import asyncio
import logging
import re
import urllib.parse
from typing import Any

import aiohttp

from core import (
    LLM_MAX_TOKENS,
    LLM_RETRIES,
    LLM_TIMEOUT,
    QWEN_PICT_MODEL,
    QWEN_PICT_URL,
    QWEN_TEXT_MODEL,
    QWEN_TEXT_URL,
    SystemState,
)
from core.images import ALLOWED_HOSTS, recall_image, store_last_image, to_data_url

log = logging.getLogger(__name__)

FOOD_PROMPT = (
    "Ты — эксперт по питанию и нутрициолог. Отвечай на вопросы о еде кратко и по делу, "
    "без лишней информации. Если к вопросу приложено фото блюда — опирайся на него."
)
PHOTO_PROMPT = (
    "Ты — помощник по анализу еды. Опиши, что изображено на фотографии: назови блюдо, "
    "перечисли основные ингредиенты, укажи примерную калорийность на 100 г или на порцию. "
    "Ответ дай коротким текстом, без лишней информации."
)
PHOTO_QUESTION = "Что это за блюдо и какова его примерная калорийность?"

USER_ERROR = "Сервис анализа временно недоступен. Попробуйте повторить запрос позже."
IMAGE_TROUBLE = "Не удалось загрузить изображение. Пришлите фото ещё раз."

_URL_RE = re.compile(r"^https?://\S+$", re.IGNORECASE)
_IMAGE_EXT_RE = re.compile(r"\.(jpe?g|png|bmp|webp|gif|heic|heif)$", re.IGNORECASE)

_session: aiohttp.ClientSession | None = None


class LLMError(RuntimeError):
    """Модель недоступна или ответила некорректно."""


def get_session() -> aiohttp.ClientSession:
    global _session
    if _session is None or _session.closed:
        _session = aiohttp.ClientSession()
    return _session


async def close_llm_session() -> None:
    global _session
    if _session is not None and not _session.closed:
        await _session.close()
    _session = None


def is_image_url(message: str) -> bool:
    candidate = (message or "").strip()
    if not _URL_RE.match(candidate):
        return False
    parsed = urllib.parse.urlparse(candidate)
    host = (parsed.hostname or "").lower()
    if any(host == allowed or host.endswith("." + allowed) for allowed in ALLOWED_HOSTS):
        return True
    return bool(_IMAGE_EXT_RE.search(parsed.path))


async def call_llm(url: str, model: str, prompt: str, content: Any) -> str:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": content},
        ],
        "max_tokens": LLM_MAX_TOKENS,
        "temperature": 0.1,
        "top_p": 0.8,
    }
    attempts = LLM_RETRIES + 1
    last_error = "неизвестная ошибка"

    for attempt in range(1, attempts + 1):
        try:
            timeout = aiohttp.ClientTimeout(total=LLM_TIMEOUT)
            async with get_session().post(url, json=payload, timeout=timeout) as response:
                if response.status != 200:
                    body = (await response.text())[:300]
                    last_error = f"HTTP {response.status}: {body}"
                    if 400 <= response.status < 500:
                        raise LLMError(last_error)   # повторять бессмысленно
                    log.warning("модель ответила %s (попытка %d/%d)",
                                response.status, attempt, attempts)
                else:
                    data = await response.json(content_type=None)
                    try:
                        answer = data["choices"][0]["message"]["content"]
                    except (KeyError, IndexError, TypeError) as exc:
                        last_error = f"некорректный ответ модели: {exc}"
                        log.warning(last_error)
                    else:
                        answer = str(answer or "").strip()
                        if answer:
                            return answer
                        last_error = "модель вернула пустой ответ"
        except LLMError:
            raise
        except asyncio.TimeoutError:
            last_error = f"таймаут {LLM_TIMEOUT:.0f} с"
            log.warning("таймаут модели (попытка %d/%d)", attempt, attempts)
        except aiohttp.ClientError as exc:
            last_error = f"сеть: {exc}"
            log.warning("сетевая ошибка модели (попытка %d/%d): %s", attempt, attempts, exc)

        if attempt < attempts:
            await asyncio.sleep(0.5 * attempt)

    raise LLMError(last_error)


async def _recall(user_id: str) -> bytes | None:
    """Redis упал — не роняем запрос, просто отвечаем без картинки."""
    try:
        return await recall_image(user_id)
    except Exception as exc:
        log.warning("Redis недоступен, работаю без картинки: %s", exc)
        return None


async def classify_message(state: SystemState) -> dict:
    text = (state.get("current_message") or "").strip()
    user_id = state.get("user_id") or ""

    if not is_image_url(text):
        return {"message_type": "food"}

    try:
        await store_last_image(user_id, text)
    except Exception as exc:
        log.warning("не удалось принять фото uid=%s: %s", user_id, exc)
        return {"message_type": "error", "ai_response": IMAGE_TROUBLE}

    return {"message_type": "photo"}


def route_after_classification(state: SystemState) -> str:
    message_type = state.get("message_type") or "food"
    if message_type == "photo":
        return "photo"
    if message_type == "error":
        return "error"
    return "food"


async def food(state: SystemState) -> dict:
    """Есть картинка в Redis — отвечаем по ней; нет — отвечаем как нутрициолог."""
    text = (state.get("current_message") or "").strip()
    jpeg = await _recall(state.get("user_id") or "")

    if jpeg:
        content = [
            {"type": "image_url", "image_url": {"url": to_data_url(jpeg)}},
            {"type": "text", "text": text or "Что изображено на фото? Оцени калорийность."},
        ]
    else:
        content = text or "Что можно съесть на завтрак?"

    try:
        answer = await call_llm(QWEN_TEXT_URL, QWEN_TEXT_MODEL, FOOD_PROMPT, content)
    except LLMError as exc:
        log.error("food: %s", exc)
        return {"ai_response": USER_ERROR}

    return {"ai_response": answer}


async def analysis_node(state: SystemState) -> dict:
    jpeg = await _recall(state.get("user_id") or "")
    if not jpeg:
        return {"ai_response": IMAGE_TROUBLE}

    content = [
        {"type": "image_url", "image_url": {"url": to_data_url(jpeg)}},
        {"type": "text", "text": PHOTO_QUESTION},
    ]

    try:
        answer = await call_llm(QWEN_PICT_URL, QWEN_PICT_MODEL, PHOTO_PROMPT, content)
    except LLMError as exc:
        log.error("analysis_node: %s", exc)
        return {"ai_response": USER_ERROR}

    return {"ai_response": answer}
