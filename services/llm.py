import asyncio
import os
import random
from dataclasses import dataclass

import httpx


class MistralAPIError(Exception):
    """Raised when Mistral cannot provide a usable response."""


@dataclass
class LlmResponse:
    text: str
    input_tokens: int = 0
    output_tokens: int = 0


class MistralClient:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        max_retries: int | None = None,
    ) -> None:
        self.api_key = api_key or os.getenv("MISTRAL_API_KEY")
        self.base_url = (base_url or os.getenv("MISTRAL_URL", "https://api.mistral.ai/v1")).rstrip("/")
        self.model = model or os.getenv("MISTRAL_MODEL", "mistral-small-latest")
        self.embedding_model = os.getenv("MISTRAL_EMBEDDING_MODEL", "mistral-embed")
        self.max_retries = max_retries if max_retries is not None else int(os.getenv("MISTRAL_MAX_RETRIES", "5"))

    async def get_response(self, message: str, context: list[str] | None = None) -> LlmResponse:
        messages = []
        if context:
            system_prompt = (
                "Tu es un assistant spécialisé dans les démarches administratives françaises. "
                "Réponds uniquement à partir du contexte fourni. "
                "N'invente jamais de chiffre, de date, de délai, de condition, de lien ou de procédure. "
                "Si une information n'est pas présente ou ne peut pas être déduite clairement du contexte, "
                "dis-le explicitement et invite l'utilisateur à consulter la source officielle. "
                "Ne présente pas une supposition comme un fait. "
                "Rédige une réponse claire, concise et compréhensible, sans mentionner tes limites techniques."
                "\n"
                "Règles strictes :\n"
                "- Cite les sources avec leur titre et URL à la fin de ta réponse.\n"
                "- Ne cite JAMAIS une référence, un numéro de document, ou un lien"
                " qui n'est pas explicitement présent dans le contexte.\n"
                "- Utilise EXACTEMENT les mots, chiffres et descriptions du contexte."
                " Ne les remplace par aucun synonyme."
                " Exemple : si le contexte dit 'service en ligne',"
                " écris 'service en ligne', pas 'téléservice' ou 'simulateur'.\n"
                "- Si une information est absente du contexte, dis-le."
                " N'invente rien."
                "\n\nContexte :\n"
                + "\n\n---\n\n".join(context)
            )
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": message})
        try:
            response = await self._post("/chat/completions", {"model": self.model, "messages": messages})
            content = response["choices"][0]["message"]["content"]
            usage = response.get("usage", {})
        except (KeyError, IndexError, TypeError, ValueError) as error:
            raise MistralAPIError("Mistral API returned an unexpected response.") from error
        if not isinstance(content, str) or not content.strip():
            raise MistralAPIError("Mistral API returned an empty response.")
        return LlmResponse(
            text=content,
            input_tokens=usage.get("prompt_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0),
        )

    async def get_response_stream(self, message: str, context: list[str] | None = None):
        messages = []
        if context:
            system_prompt = (
                "Tu es un assistant spécialisé dans les démarches administratives françaises. "
                "Réponds uniquement à partir du contexte fourni. "
                "N'invente jamais de chiffre, de date, de délai, de condition, de lien ou de procédure. "
                "Si une information n'est pas présente ou ne peut pas être déduite clairement du contexte, "
                "dis-le explicitement et invite l'utilisateur à consulter la source officielle. "
                "Ne présente pas une supposition comme un fait. "
                "Rédige une réponse claire, concise et compréhensible, sans mentionner tes limites techniques."
                "\n"
                "Règles strictes :\n"
                "- Cite les sources avec leur titre et URL à la fin de ta réponse.\n"
                "- Ne cite JAMAIS une référence, un numéro de document, ou un lien"
                " qui n'est pas explicitement présent dans le contexte.\n"
                "- Utilise EXACTEMENT les mots, chiffres et descriptions du contexte."
                " Ne les remplace par aucun synonyme.\n"
                "- Si une information est absente du contexte, dis-le."
                " N'invente rien."
                "\n\nContexte :\n"
                + "\n\n---\n\n".join(context)
            )
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": message})
        if not self.api_key:
            raise MistralAPIError("MISTRAL_API_KEY is not configured.")
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                json={"model": self.model, "messages": messages, "stream": True},
                headers={"Authorization": f"Bearer {self.api_key}"},
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data.strip() == "[DONE]":
                            break
                        try:
                            import json
                            chunk = json.loads(data)
                            delta = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                            if delta:
                                yield delta
                        except json.JSONDecodeError:
                            continue

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

        retryable_statuses = {429, 500, 502, 503, 504}
        for attempt in range(self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        f"{self.base_url}{endpoint}",
                        json=payload,
                        headers={"Authorization": f"Bearer {self.api_key}"},
                    )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as error:
                status_code = error.response.status_code
                if status_code not in retryable_statuses or attempt == self.max_retries:
                    raise MistralAPIError(
                        f"Mistral API returned HTTP {status_code}: {self._error_message(error.response)}"
                    ) from error

                # Retry-After est prioritaire ; sinon on applique un backoff exponentiel.
                wait_seconds = self._retry_after(error.response, attempt)
                await asyncio.sleep(wait_seconds)
            except httpx.HTTPError as error:
                raise MistralAPIError("Mistral API request failed.") from error

        raise MistralAPIError("Mistral API request failed after retries.")

    @staticmethod
    def _retry_after(response: httpx.Response, attempt: int) -> float:
        """Calcule une attente courte et croissante entre deux tentatives."""
        retry_after = response.headers.get("Retry-After")
        try:
            return max(0.0, float(retry_after)) if retry_after else min(60.0, 2**attempt + random.random())
        except ValueError:
            return min(60.0, 2**attempt + random.random())

    @staticmethod
    def _error_message(response: httpx.Response) -> str:
        """Extrait le message JSON de Mistral sans masquer le statut HTTP."""
        try:
            body = response.json()
            return str(body.get("message") or body.get("error") or "request failed")
        except (ValueError, TypeError):
            return response.text[:200] or "request failed"
