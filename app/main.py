import json
import logging
import os
import secrets
import time
from collections import defaultdict
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.audit import AuditLogger
from app.llm import MistralAPIError, MistralClient
from app.pii import PIIAnonymizer
from app.qdrant_store import QdrantStore, QdrantStoreError
from app.rag.pipeline import RagPipeline
from app.reranker import rerank_results

load_dotenv()
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("trustrag")


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=10_000)


class ChatResponse(BaseModel):
    request_id: str
    response: str
    sources: list[dict] = Field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0


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


class FeedbackRequest(BaseModel):
    request_id: str = Field(min_length=1)
    score: str = Field(pattern=r"^(positive|negative)$")


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

    rate_limit_store: dict[str, list[float]] = defaultdict(list)
    RATE_LIMIT = int(os.getenv("RATE_LIMIT_PER_MINUTE", "30"))

    @application.middleware("http")
    async def rate_limit_middleware(request: Request, call_next):
        if request.url.path in ("/metrics", "/health", "/ping", "/qdrant/health"):
            return await call_next(request)
        client_ip = request.client.host if request.client else "unknown"
        now = time.monotonic()
        window = rate_limit_store[client_ip]
        window[:] = [t for t in window if now - t < 60.0]
        if len(window) >= RATE_LIMIT:
            raise HTTPException(status_code=429, detail="Rate limit exceeded. Try again later.")
        window.append(now)
        return await call_next(request)

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

        audit = request.app.state.rag.audit
        recent = audit.recent_entries(limit=100)
        error_count = sum(1 for e in recent if e.get("error"))
        total = len(recent)
        rt_values = [e["response_time_ms"] for e in recent if e.get("response_time_ms")]
        tokens_in = sum(e.get("input_tokens", 0) for e in recent)
        tokens_out = sum(e.get("output_tokens", 0) for e in recent)
        feedbacks = [e for e in audit._read_entries() if e.get("event") == "feedback"]
        positive_fb = sum(1 for e in feedbacks if e.get("score") == "positive")
        negative_fb = sum(1 for e in feedbacks if e.get("score") == "negative")

        return {
            "version": "0.2.0",
            "uptime_seconds": time.monotonic() - request.app.state.start_time,
            "chat_requests_total": chat_count,
            "collection": collection_info,
            "latency": {
                "min_ms": min(rt_values) if rt_values else 0,
                "avg_ms": round(sum(rt_values) / len(rt_values), 1) if rt_values else 0,
                "max_ms": max(rt_values) if rt_values else 0,
                "p50_ms": sorted(rt_values)[len(rt_values) // 2] if rt_values else 0,
                "p95_ms": sorted(rt_values)[int(len(rt_values) * 0.95)] if rt_values else 0,
                "p99_ms": sorted(rt_values)[int(len(rt_values) * 0.99)] if rt_values else 0,
            },
            "errors": {
                "count": error_count,
                "rate": round(error_count / total, 3) if total else 0,
            },
            "tokens": {
                "total_input": tokens_in,
                "total_output": tokens_out,
                "total": tokens_in + tokens_out,
            },
            "feedback": {
                "positive": positive_fb,
                "negative": negative_fb,
            },
            "endpoints": {
                "chat": "/chat",
                "chat_stream": "/chat/stream",
                "feedback": "/feedback",
                "health": "/health",
                "metrics": "/metrics",
                "qdrant_health": "/qdrant/health",
                "audit_recent": "/audit/recent",
                "delete_conversation": "/conversations/{request_id}",
            },
        }

    @application.get("/ping")
    async def ping() -> dict[str, str]:
        return {"message": "pong"}

    @application.get("/health")
    async def health(request: Request) -> dict:
        checks = {}

        try:
            await run_in_threadpool(request.app.state.rag.qdrant.healthcheck)
            checks["qdrant"] = "ok"
        except QdrantStoreError as e:
            checks["qdrant"] = str(e)

        try:
            vectors = await request.app.state.rag.llm.get_embeddings(["test"])
            if vectors and len(vectors[0]) > 0:
                checks["embeddings"] = "ok"
            else:
                checks["embeddings"] = "empty response"
        except MistralAPIError as e:
            checks["embeddings"] = str(e)

        try:
            llm_resp = await request.app.state.rag.llm.get_response("Réponds 'ok'")
            checks["llm"] = "ok" if "ok" in llm_resp.text.lower() else "unexpected"
        except MistralAPIError as e:
            checks["llm"] = str(e)

        return checks

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

    @application.get("/audit/recent")
    async def audit_recent(request: Request, limit: int = 20) -> list[dict]:
        admin_key = os.getenv("ADMIN_API_KEY")
        provided_key = request.headers.get("X-Admin-Key", "")
        if not admin_key or not secrets.compare_digest(provided_key, admin_key):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrative key required.")
        return request.app.state.rag.audit.recent_entries(limit=min(limit, 100))

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

    @application.get("/eval/history")
    async def eval_history(request: Request) -> list[dict]:
        path = Path(os.getenv("EVAL_HISTORY_PATH", "data/eval_history.json"))
        if not path.exists():
            return []
        return json.loads(path.read_text(encoding="utf-8"))

    @application.post("/feedback")
    async def feedback(payload: FeedbackRequest, request: Request) -> dict:
        success = request.app.state.rag.audit.record_feedback(payload.request_id, payload.score)
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request ID not found.")
        return {"status": "ok"}

    @application.post("/chat", response_model=ChatResponse)
    async def chat(payload: ChatRequest, request: Request) -> ChatResponse:
        client_ip = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")
        start = time.monotonic()
        try:
            result = await request.app.state.rag.execute(payload.message)
        except (MistralAPIError, QdrantStoreError) as error:
            elapsed = time.monotonic() - start
            request.app.state.rag.audit.record_chat(
                "anonymized", "", [],
                client_ip=client_ip,
                user_agent=user_agent,
                response_time_ms=round(elapsed * 1000),
                error=str(error),
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(error),
            ) from error
        elapsed = time.monotonic() - start
        event = request.app.state.rag.audit.record_chat(
            result.anonymized_question, result.response, result.sources,
            client_ip=client_ip,
            user_agent=user_agent,
            response_time_ms=round(elapsed * 1000),
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
        )
        return ChatResponse(
            request_id=event["request_id"],
            response=result.response, sources=result.sources,
            input_tokens=result.input_tokens, output_tokens=result.output_tokens,
        )

    @application.post("/chat/stream")
    async def chat_stream(payload: ChatRequest, request: Request):
        client_ip = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")
        start = time.monotonic()
        try:
            anonymized = request.app.state.rag.pii.anonymize(payload.message).text
            vector = (await request.app.state.rag.llm.get_embeddings([anonymized]))[0]
            candidates = await run_in_threadpool(request.app.state.rag.qdrant.search, vector, 12)

            context_chunks = rerank_results(payload.message, candidates, top_k=8, deduplicate=False)
            source_chunks = rerank_results(payload.message, context_chunks, top_k=8, deduplicate=True)

            top = max(context_chunks, key=lambda c: c.get("rerank_score", 0)) if context_chunks else None
            if (
                not context_chunks
                or top is None
                or top.get("rerank_score", 0) < 0.4
                or top.get("title_keyword_score", 0) < 0.3
            ):
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
                _NO_SOURCE_PATTERNS = ["ne peux pas répondre", "ne trouve pas", "ne concerne pas"]
                if any(p in safe.lower() for p in _NO_SOURCE_PATTERNS):
                    public_sources = []
                else:
                    public_sources = [{k: v for k, v in s.items() if k != "text"} for s in source_chunks]
                elapsed = time.monotonic() - start
                usage = getattr(request.app.state.rag.llm, "_last_usage", {})
                request.app.state.rag.audit.record_chat(
                    anonymized, safe, public_sources,
                    client_ip=client_ip,
                    user_agent=user_agent,
                    response_time_ms=round(elapsed * 1000),
                    input_tokens=usage.get("prompt_tokens", 0),
                    output_tokens=usage.get("completion_tokens", 0),
                )
                yield f"data: {json.dumps({'done': True, 'sources': public_sources})}\n\n"

            return StreamingResponse(generate(), media_type="text/event-stream")

        except (MistralAPIError, QdrantStoreError) as error:
            elapsed = time.monotonic() - start
            request.app.state.rag.audit.record_chat(
                "anonymized", "", [],
                client_ip=client_ip,
                user_agent=user_agent,
                response_time_ms=round(elapsed * 1000),
                error=str(error),
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(error),
            ) from error

    return application


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=int(os.getenv("FASTAPI_PORT", "8000")))
