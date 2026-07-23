import os
import json
import logging
import secrets
import time
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from services.audit import AuditLogger
from services.llm import MistralAPIError, MistralClient
from services.pii import PIIAnonymizer
from services.qdrant_store import QdrantStore, QdrantStoreError
from services.rag.pipeline import RagPipeline
from services.reranker import rerank_results

load_dotenv()
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("trustrag")


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=10_000)


class ChatResponse(BaseModel):
    response: str
    sources: list[dict] = Field(default_factory=list)


class Document(BaseModel):
    text: str = Field(min_length=1, max_length=50_000)
    metadata: dict = Field(default_factory=dict)


class DocumentsRequest(BaseModel):
    documents: list[Document] = Field(min_length=1, max_length=100)


class DocumentsResponse(BaseModel):
    indexed: int


class DeleteDocumentResponse(BaseModel):
    document_id: str
    source: str
    deleted: bool


class DeleteConversationResponse(BaseModel):
    request_id: str
    deleted: bool


@asynccontextmanager
async def lifespan(app: FastAPI):
    llm = MistralClient()
    qdrant = QdrantStore()
    pii = PIIAnonymizer()
    audit = AuditLogger()
    app.state.rag = RagPipeline(llm=llm, qdrant=qdrant, pii=pii, audit=audit)
    app.state.start_time = time.monotonic()
    yield


def create_app() -> FastAPI:
    application = FastAPI(
        title="Jarvis AI API",
        version="0.2.0",
        lifespan=lifespan,
    )

    @application.middleware("http")
    async def metrics_middleware(request: Request, call_next):
        start = time.monotonic()
        response = await call_next(request)
        elapsed = time.monotonic() - start
        logger.info(
            "metrics path=%s method=%s status=%d elapsed_ms=%.0f",
            request.url.path,
            request.method,
            response.status_code,
            elapsed * 1000,
        )
        response.headers["X-Response-Time-Ms"] = str(round(elapsed * 1000))
        return response

    @application.get("/")
    async def root() -> dict[str, str]:
        return {"message": "Bienvenue dans le backend Jarvis AI"}

    @application.get("/metrics")
    async def metrics(request: Request) -> dict:
        chat_count = request.app.state.rag.audit.chat_count()

        collection_info = {}
        try:
            col = request.app.state.rag.qdrant.client.get_collection(
                request.app.state.rag.qdrant.collection_name
            )
            collection_info = {
                "points_count": col.points_count,
                "indexed_documents": col.points_count,
                "vectors_config": str(col.config.params.vectors.size) if col.config.params.vectors else "unknown",
            }
        except Exception as e:
            collection_info = {"error": str(e)}

        return {
            "version": "0.2.0",
            "uptime_seconds": time.monotonic() - request.app.state.start_time,
            "chat_requests_total": chat_count,
            "collection": collection_info,
            "endpoints": {
                "chat": "/chat",
                "chat_stream": "/chat/stream",
                "health": "/health",
                "metrics": "/metrics",
                "qdrant_health": "/qdrant/health",
                "delete_conversation": "/conversations/{request_id}",
            },
        }

    @application.get("/ping")
    async def ping() -> dict[str, str]:
        return {"message": "pong"}

    @application.get("/health")
    async def health(request: Request) -> dict:
        checks = {}
        all_ok = True

        try:
            await run_in_threadpool(request.app.state.rag.qdrant.healthcheck)
            checks["qdrant"] = "ok"
        except QdrantStoreError as e:
            checks["qdrant"] = str(e)
            all_ok = False

        try:
            vectors = await request.app.state.rag.llm.get_embeddings(["test"])
            if vectors and len(vectors[0]) > 0:
                checks["embeddings"] = "ok"
            else:
                checks["embeddings"] = "empty response"
                all_ok = False
        except MistralAPIError as e:
            checks["embeddings"] = str(e)
            all_ok = False

        try:
            response = await request.app.state.rag.llm.get_response("Réponds 'ok'")
            checks["llm"] = "ok" if "ok" in response.lower() else "unexpected"
        except MistralAPIError as e:
            checks["llm"] = str(e)
            all_ok = False

        status_code = status.HTTP_200_OK if all_ok else status.HTTP_503_SERVICE_UNAVAILABLE
        raise HTTPException(status_code=status_code, detail=json.dumps(checks))

    @application.get("/qdrant/health")
    async def qdrant_health(request: Request) -> dict[str, str]:
        try:
            await run_in_threadpool(request.app.state.rag.qdrant.healthcheck)
        except QdrantStoreError as error:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error
        return {"message": "qdrant connected"}

    @application.post("/documents", response_model=DocumentsResponse, status_code=status.HTTP_201_CREATED)
    async def index_documents(payload: DocumentsRequest, request: Request) -> DocumentsResponse:
        documents = [document.model_dump() for document in payload.documents]
        try:
            vectors = await request.app.state.rag.llm.get_embeddings([document["text"] for document in documents])
            indexed = await run_in_threadpool(request.app.state.rag.qdrant.upsert, documents, vectors)
        except (MistralAPIError, QdrantStoreError) as error:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error
        return DocumentsResponse(indexed=indexed)

    @application.delete("/documents/{document_id}", response_model=DeleteDocumentResponse)
    async def delete_document(
        document_id: str,
        request: Request,
        source: str = "service-public-vdd",
    ) -> DeleteDocumentResponse:
        admin_key = os.getenv("ADMIN_API_KEY")
        provided_key = request.headers.get("X-Admin-Key", "")
        if not admin_key or not secrets.compare_digest(provided_key, admin_key):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Administrative key required.",
            )
        try:
            await run_in_threadpool(request.app.state.rag.qdrant.delete_document, document_id, source)
        except QdrantStoreError as error:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error
        return DeleteDocumentResponse(document_id=document_id, source=source, deleted=True)

    @application.delete("/conversations/{request_id}", response_model=DeleteConversationResponse)
    async def delete_conversation(request_id: str, request: Request) -> DeleteConversationResponse:
        admin_key = os.getenv("ADMIN_API_KEY")
        provided_key = request.headers.get("X-Admin-Key", "")
        if not admin_key or not secrets.compare_digest(provided_key, admin_key):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Administrative key required.",
            )
        deleted = request.app.state.rag.audit.delete_entry(request_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No conversation found with request_id '{request_id}'.",
            )
        return DeleteConversationResponse(request_id=request_id, deleted=True)

    @application.post("/chat", response_model=ChatResponse)
    async def chat(payload: ChatRequest, request: Request) -> ChatResponse:
        try:
            result = await request.app.state.rag.execute(payload.message)
        except (MistralAPIError, QdrantStoreError) as error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(error),
            ) from error
        return ChatResponse(response=result.response, sources=result.sources)

    @application.post("/chat/stream")
    async def chat_stream(payload: ChatRequest, request: Request):
        try:
            anonymized = request.app.state.rag.pii.anonymize(payload.message).text
            vector = (await request.app.state.rag.llm.get_embeddings([anonymized]))[0]
            candidates = await run_in_threadpool(request.app.state.rag.qdrant.search, vector, 12)

            context_chunks = rerank_results(payload.message, candidates, top_k=8, deduplicate=False)
            source_chunks = rerank_results(payload.message, context_chunks, top_k=8, deduplicate=True)

            if not context_chunks:
                no_result = "Je ne trouve pas cette information dans les documents disponibles."
                async def noop():
                    yield f"data: {json.dumps({'done': True, 'sources': [], 'response': no_result})}\n\n"
                return StreamingResponse(noop(), media_type="text/event-stream")

            llm_context = RagPipeline._format_context(context_chunks)

            async def generate():
                full = ""
                async for token in request.app.state.rag.llm.get_response_stream(anonymized, llm_context):
                    full += token
                    yield f"data: {json.dumps({'token': token})}\n\n"
                safe = request.app.state.rag.pii.anonymize(full).text
                public_sources = [{k: v for k, v in s.items() if k != "text"} for s in source_chunks]
                request.app.state.rag.audit.record_chat(anonymized, safe, public_sources)
                yield f"data: {json.dumps({'done': True, 'sources': public_sources})}\n\n"

            return StreamingResponse(generate(), media_type="text/event-stream")

        except (MistralAPIError, QdrantStoreError) as error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(error),
            ) from error

    return application


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("services.main:app", host="0.0.0.0", port=int(os.getenv("FASTAPI_PORT", "8000")))
