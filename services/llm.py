import os

import httpx


class MistralAPIError(Exception):
    """Raised when Mistral cannot provide a usable chat completion."""


class MistralClient:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
    ) -> None:
        self.api_key = api_key or os.getenv("MISTRAL_API_KEY")
        self.base_url = (base_url or os.getenv("MISTRAL_URL", "https://api.mistral.ai/v1")).rstrip("/")
        self.model = model or os.getenv("MISTRAL_MODEL", "mistral-small-latest")

    async def get_response(self, message: str) -> str:
        if not self.api_key:
            raise MistralAPIError("MISTRAL_API_KEY is not configured.")

        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": message}],
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers=headers,
                )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
        except httpx.HTTPError as error:
            raise MistralAPIError("Mistral API request failed.") from error
        except (KeyError, IndexError, TypeError, ValueError) as error:
            raise MistralAPIError("Mistral API returned an unexpected response.") from error

        if not isinstance(content, str) or not content.strip():
            raise MistralAPIError("Mistral API returned an empty response.")
        return content
