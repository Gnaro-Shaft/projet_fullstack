import asyncio
from unittest.mock import patch

import httpx

from services.llm import MistralAPIError, MistralClient


class FakeResponse:
    def __init__(self, status_code: int, body: dict, headers: dict | None = None) -> None:
        self.status_code = status_code
        self._body = body
        self.headers = headers or {}
        self.text = str(body)

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            request = httpx.Request("POST", "https://example.test")
            raise httpx.HTTPStatusError("request failed", request=request, response=self)

    def json(self) -> dict:
        return self._body


class FakeAsyncClient:
    responses = []

    def __init__(self, **kwargs) -> None:
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        return False

    async def post(self, *args, **kwargs):
        return self.responses.pop(0)


def test_mistral_retries_after_rate_limit() -> None:
    FakeAsyncClient.responses = [
        FakeResponse(429, {"message": "rate limit"}, {"Retry-After": "0"}),
        FakeResponse(200, {"choices": [{"message": {"content": "OK"}}], "usage": {"prompt_tokens": 10, "completion_tokens": 5}}),
    ]
    client = MistralClient(api_key="test", max_retries=1)

    with patch("services.llm.httpx.AsyncClient", FakeAsyncClient):
        response = asyncio.run(client.get_response("Bonjour"))

    assert response.text == "OK"
    assert FakeAsyncClient.responses == []


def test_mistral_reports_final_rate_limit() -> None:
    FakeAsyncClient.responses = [FakeResponse(429, {"message": "quota reached"})]
    client = MistralClient(api_key="test", max_retries=0)

    with patch("services.llm.httpx.AsyncClient", FakeAsyncClient):
        try:
            asyncio.run(client.get_response("Bonjour"))
        except MistralAPIError as error:
            assert "HTTP 429" in str(error)
            assert "quota reached" in str(error)
        else:
            raise AssertionError("MistralAPIError was not raised")
