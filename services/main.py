import os
import logging
import secrets
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field

from services.audit import AuditLogger
from services.llm import MistralAPIError, MistralClient
from services.pii import PIIAnonymizer
from services.qdrant_store import QdrantStore, QdrantStoreError
from services.rag.pipeline import RagPipeline

load_dotenv()
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))


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


@asynccontextmanager
async def lifespan(app: FastAPI):
    llm = MistralClient()
    qdrant = QdrantStore()
    pii = PIIAnonymizer()
    audit = AuditLogger()
    app.state.rag = RagPipeline(llm=llm, qdrant=qdrant, pii=pii, audit=audit)
    yield


def create_app() -> FastAPI:
    application = FastAPI(
        title="Jarvis AI API",
        version="0.1.0",
        lifespan=lifespan,
    )

    @application.get("/")
    async def root() -> dict[str, str]:
        return {"message": "Bienvenue dans le backend Jarvis AI"}

    @application.get("/ping")
    async def ping() -> dict[str, str]:
        return {"message": "pong"}

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

    return application


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("services.main:app", host="0.0.0.0", port=int(os.getenv("FASTAPI_PORT", "8000")))
