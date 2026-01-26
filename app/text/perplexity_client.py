from typing import Any, Optional

import httpx

from app.core.config import settings

_client: Optional[httpx.AsyncClient] = None


def get_perplexity_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(timeout=settings.PERPLEXITY_TIMEOUT)
    return _client


async def close_perplexity_client():
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


async def call_perplexity_api(
        *,
        messages: list[dict[str, Any]],
        model: Optional[str] = None,
        temperature: float = 0.2
) -> str:
    if not settings.PERPLEXITY_API_KEY:
        raise ValueError("Нет API ключа PERPLEXITY_API_KEY")

    client = get_perplexity_client()

    payload = {
        "model": model or settings.PERPLEXITY_DEFAULT_MODEL,
        "messages": messages,
        "temperature": temperature,
    }

    try:
        response = await client.post(
            settings.PERPLEXITY_API_URL,
            headers={
                "Authorization": f"Bearer {settings.PERPLEXITY_API_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as e:
        raise Exception(
            f"Perplexity API вернул ошибку {e.response.status_code}: {e.response.text}"
        )
    except httpx.TimeoutException:
        raise Exception("Превышено время ожидания ответа от Perplexity API")
    except httpx.RequestError as e:
        raise Exception(f"Ошибка запроса к Perplexity API: {str(e)}")

    result = response.json()

    try:
        return result["choices"][0]["message"]["content"]
    except (KeyError, IndexError):
        raise Exception(f"Неожиданный формат ответа от Perplexity API: {result}")