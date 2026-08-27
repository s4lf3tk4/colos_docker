from core import SystemState, QWEN_PICT_URL, QWEN_PICT_MODEL, QWEN_TEXT_MODEL, QWEN_TEXT_URL
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
# from ultralytics import YOLO
# from PIL import Image
# from io import BytesIO

import base64
import requests
from PIL import Image
from io import BytesIO

import aiohttp
import asyncio
# import json
# import os
# import sys
from typing import List, Dict, Any, Optional

def classify_message(state: SystemState) -> dict:
    """Классификация сообщения по расширению:
        food (анализ текста);
        photo(ссылка на картинку -> анализ картинки ИИ)"""
    try:
        user_input = state["current_message"]

        if (user_input.startswith("/app/storage/") and
            any(user_input.lower().endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"])):
            return {
                "message_type": "photo",
                "image_path": user_input,
            }
        else:
            return {
                "message_type": "food",
            }


    except Exception as e:
        print(f"Ошибка классификации: {e}. Используем 'food' по умолчанию.", flush=True)
        message_type = "food"
        return {
            "message_type": "food",
        }


def router_after_classification(state: SystemState):
    message_type = state["message_type"]
    print(f"В router {message_type}")
    if message_type == "photo":
        return "photo"
    else:
        return "food"


async def food(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Обрабатывает текстовые запросы о питании через Qwen.

    Args:
        state: содержит "messages" — список результатов анализов и других сообщений - вопросов

    Returns:
        {"ai_response": [{"role": "assistant", "content": str}],
         "messages": [{"role": "assistant", "content": str}]}
    """
    print("В функции FOOD")
    prompt = (
        "Ты — эксперт по питанию и нутрициолог. Твоя задача — отвечать на любые вопросы о еде, "
        "калориях, БЖУ и здоровом питании. Если вопрос не касается этих тем, вежливо объясни, "
        "что ты специалист по питанию, и предложи помощь в этой области. Всегда давай полезные "
        "и точные советы, основанные на научных данных. Отвечай на русском языке."
    )
    messages = state.get("messages", [])
    if not messages:
        error_msg = "Нет сообщений для ответа."
        return {
            "ai_response": error_msg,
        }

    full_messages = [
        {"role": "system", "content": prompt},
        *messages
    ]

    payload = {
        "model": QWEN_TEXT_MODEL,
        "messages": full_messages,
        "temperature": 0.3,
        "max_tokens": 2048,
        "top_p": 0.9,
        "stream": False,
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                QWEN_TEXT_URL,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=120)
            ) as response:

                if response.status != 200:
                    error_text = await response.text()
                    print(f"❌ Ошибка Qwen: {response.status} - {error_text}")
                    error_msg = f"Ошибка модели: {response.status}"
                    return {
                        "ai_response": error_msg
                    }

                result = await response.json()
                answer_content = result["choices"][0]["message"]["content"]

                print(f"✅ Ответ от Qwen получен (длина: {len(answer_content)} символов)")

                return {
                    "ai_response": answer_content,
                    "messages": [AIMessage(content = answer_content)]
                }

    except asyncio.TimeoutError:
        print("Таймаут при запросе к Qwen")
        error_msg = "Превышено время ожидания ответа от модели."
        return {
            "ai_response":error_msg
        }
    except aiohttp.ClientError as e:
        print(f"Ошибка сети при запросе к Qwen: {e}")
        error_msg = "Ошибка соединения с сервисом ИИ. Попробуйте позже."
        return {
            "ai_response":error_msg
        }
    except Exception as e:
        print(f"Неизвестная ошибка в food(): {e}")
        error_msg = f"Ошибка: {str(e)}"
        return {
            "ai_response": error_msg,
        }

# async def food(state: SystemState):
#     print("в func FOOD")
#     messages = state.get("messages", [])
#     if not messages:
#         return {"messages": [HumanMessage(content="Нет сообщений для ответа.")]}

#     system_msg = SystemMessage(
#     content="Ты — эксперт по питанию и нутрициолог. Твоя задача — отвечать на любые вопросы о еде, калориях, БЖУ и здоровом питании. Если вопрос не касается этих тем, вежливо объясни, что ты специалист по питанию, и предложи помощь в этой области. Всегда давай полезные и точные советы, основанные на научных данных."
#     )

#     full_messages = [system_msg] + messages

#     response = await llm.ainvoke(full_messages)
#     answer_content = response.content

#     return {
#         "ai_response": [AIMessage(content=answer_content)],
#         "messages": [AIMessage(content=answer_content)]
#     }


def load_image_to_base64(source: str, max_size: int = 600) -> str:
    """
    Загружает изображение с ПРИНУДИТЕЛЬНЫМ сжатием
    """
    try:

        if source.startswith(("http://", "https://")):
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'https://vk.com/'
            }
            response = requests.get(source, headers=headers, timeout=30)
            response.raise_for_status()
            img = Image.open(BytesIO(response.content))
        else:
            img = Image.open(source)


        ratio = min(max_size / img.size[0], max_size / img.size[1])
        if ratio < 1:
            new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
            img = img.resize(new_size, Image.Resampling.LANCZOS)

        # Конвертация в RGB
        if img.mode in ('RGBA', 'LA', 'P'):
            img = img.convert('RGB')

        # Сохранение с высоким сжатием
        buffer = BytesIO()
        img.save(buffer, format='JPEG', quality=75, optimize=True)
        image_bytes = buffer.getvalue()

        return base64.b64encode(image_bytes).decode('utf-8')

    except Exception as e:
        print(f"❌ Ошибка: {e}", flush=True)
        raise ValueError(f"Не удалось загрузить изображение: {e}")
# AI analyze
async def analysis_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Обрабатывает запросы с изображениями через Qwen3-VL.

    Args:
        state: содержит "image_path" и "current_message"

    Returns:
        {"ai_response": [{"role": "assistant", "content": str}],
         "messages": [{"role": "assistant", "content": str}]}
    """

    print("В функции PHOTO")

    prompt = (
        "Ты — помощник по анализу еды. Опиши, что изображено на фотографии. "
        "Назови блюдо, перечисли основные ингредиенты, укажи примерную калорийность "
        "в килокалориях на 100 грамм или на порцию. Ответ дай в виде короткого текста, "
        "без лишней информации."
    )
    image_path = state.get("image_path", "")


    if not image_path:
        error_msg = "Путь к изображению не указан."
        return {
            "ai_response": error_msg,
        }

    image_base64 = load_image_to_base64(image_path)

    payload = {
        "model": QWEN_PICT_MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}
                    },
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
            }
        ],
        "temperature": 0.5,
        "max_tokens": 2024,
        "top_p": 0.9,
        "seed": 42
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                QWEN_PICT_URL,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=120)
            ) as response:

                if response.status != 200:
                    error_text = await response.text()
                    print(f"❌ Ошибка Qwen3-VL: {response.status} - {error_text}")
                    error_msg = f"Ошибка модели: {response.status}"
                    return {
                        "ai_response": [{"role": "assistant", "content": error_msg}],
                        "messages": [{"role": "assistant", "content": error_msg}]
                    }

                result = await response.json()
                answer_content = result["choices"][0]["message"]["content"]

                print(f"✅ Ответ от Qwen3-VL получен (длина: {len(answer_content)} символов)")

                return {
                    "ai_response": answer_content,
                    "messages": [AIMessage(content = answer_content)]
                }

    except Exception as e:
        print(f"Ошибка в photo(): {e}")
        error_msg = f"Ошибка при обработке изображения: {str(e)}"
        return {
            "ai_response": [{"role": "assistant", "content": error_msg}],
            "messages": [{"role": "assistant", "content": error_msg}]
        }

# def analysis_node(state: SystemState) -> dict:
#     try:
#         image_path = state.get("image_path")
#         prompt = (
#             "Ты — помощник по анализу еды. Опиши, что изображено на фотографии. "
#             "Назови блюдо, перечисли основные ингредиенты, укажи примерную калорийность "
#             "в килокалориях на 100 грамм или на порцию. Ответ дай в виде короткого текста, "
#             "без лишней информации."
#         )

#         image_base64 = load_image_to_base64(image_path)
#         url = f"{OLLAMA_BASE_URL}/api/chat"
#         payload = {
#             "model": QWEEN_VL_MODEL,
#             "messages": [
#                 {
#                     "role": "user",
#                     "content": prompt,
#                     "images": [image_base64]
#                 }
#             ],
#             "stream": False,
#             "options": {
#                 "num_ctx": 2048,  # Ограничить контекст
#                 "temperature": 0.5,  # креативность (0.1-0.5)
#                 "top_p": 0.9, # nucleus sampling
#                 "seed": 42  # Фиксированный сид для стабильности
#             }
#         }
#     except Exception as e:
#         text_error = f"Ошибка при подготовке анализа: {e}"
#         print(f"Ошибка при подготовке анализа: {e}")
#         return {"ai_response": text_error}
#     try:

#         response = requests.post(url, json=payload, timeout=180)
#         response.raise_for_status()
#         result = response.json()
#         content = result.get('message', {}).get('content', '').strip()
#         if not content:
#             content = "Не удалось распознать содержимое изображения."
#             return {"ai_response": content}

#         return {"ai_response": content,
#                 "messages": [AIMessage(content = content)]
#         }

#     except Exception as e:
#         text_error = f"Ошибка при выполнения анализа: {e}"
#         print(f"Ошибка при выполнения анализа: {e}")
#         return {"ai_response": text_error}
