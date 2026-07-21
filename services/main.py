import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, status
from pydantic import BaseModel, Field

from services.llm import MistralAPIError, MistralClient

load_dotenv()


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=10_000)


class ChatResponse(BaseModel):
    response: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.llm = MistralClient()
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

    @application.post("/chat", response_model=ChatResponse)
    async def chat(payload: ChatRequest, request: Request) -> ChatResponse:
        try:
            response = await request.app.state.llm.get_response(payload.message)
        except MistralAPIError as error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(error),
            ) from error
        return ChatResponse(response=response)

    return application


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("services.main:app", host="0.0.0.0", port=int(os.getenv("FASTAPI_PORT", "8000")))
