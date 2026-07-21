import os

import httpx


class MistralAPIError(Exception):
    """Raised when Mistral cannot provide a usable response."""


class MistralClient:
    def __init__(self, api_key: str | None = None, base_url: str | None = None, model: str | None = None) -> None:
        self.api_key = api_key or os.getenv("MISTRAL_API_KEY")
        self.base_url = (base_url or os.getenv("MISTRAL_URL", "https://api.mistral.ai/v1")).rstrip("/")
        self.model = model or os.getenv("MISTRAL_MODEL", "mistral-small-latest")
        self.embedding_model = os.getenv("MISTRAL_EMBEDDING_MODEL", "mistral-embed")

    async def get_response(self, message: str, context: list[str] | None = None) -> str:
        messages = []
        if context:
            messages.append({"role": "system", "content": "Réponds à partir du contexte fourni. Si le contexte ne suffit pas, indique-le clairement.\n\nContexte :\n" + "\n\n---\n\n".join(context)})
        messages.append({"role": "user", "content": message})
        try:
            response = await self._post("/chat/completions", {"model": self.model, "messages": messages})
            content = response["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError, ValueError) as error:
            raise MistralAPIError("Mistral API returned an unexpected response.") from error
        if not isinstance(content, str) or not content.strip():
            raise MistralAPIError("Mistral API returned an empty response.")
        return content

    async def get_embeddings(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            raise MistralAPIError("At least one text is required to create embeddings.")
        try:
            response = await self._post("/embeddings", {"model": self.embedding_model, "input": texts})
            vectors = [item["embedding"] for item in response["data"]]
        except (KeyError, IndexError, TypeError, ValueError) as error:
            raise MistralAPIError("Mistral API returned unexpected embeddings.") from error
        if len(vectors) != len(texts) or any(not isinstance(vector, list) for vector in vectors):
            raise MistralAPIError("Mistral API returned invalid embeddings.")
        return vectors

    async def _post(self, endpoint: str, payload: dict) -> dict:
        if not self.api_key:
            raise MistralAPIError("MISTRAL_API_KEY is not configured.")
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(f"{self.base_url}{endpoint}", json=payload, headers={"Authorization": f"Bearer {self.api_key}"})
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as error:
            raise MistralAPIError("Mistral API request failed.") from error
