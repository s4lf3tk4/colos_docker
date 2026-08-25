from core import SystemState, llm, classification_prompt, classification_parser, OLLAMA_BASE_URL, QWEEN_VL_MODEL
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
# from ultralytics import YOLO
# from PIL import Image
# from io import BytesIO

import base64
import requests
from PIL import Image
from io import BytesIO

import asyncio
import json
import os
import sys
from typing import List, Dict, Any, Optional

_yolo_models = {}

def classify_message(state: SystemState) -> dict:
    user_input = state["current_message"]

    # === ПРОВЕРКА ПО РАСШИРЕНИЮ (ОСНОВНОЙ СПОСОБ) ===
    if (user_input.startswith("/app/storage/") and
        any(user_input.lower().endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"])):
        print("PHOTO (определено по расширению)", flush=True)
        return {
            "message_type": "photo",
            "image_path": user_input,
            "messages": [HumanMessage(content="Классифицировано как photo (по расширению)")]
        }

    # === ДЛЯ ТЕКСТОВЫХ СООБЩЕНИЙ  — ИСПОЛЬЗУЕМ LLM ===
    classification_chain = classification_prompt | llm | classification_parser
    try:
        classification_result = classification_chain.invoke({"user_input": user_input})
        message_type = classification_result.get("message_type")
        confidence = classification_result.get("confidence", 0.0)
        # Если LLM вернул None, заменяем на "food"
        if not message_type:
            print("ОШИБКА: message_type is None, используем 'food'", flush=True)
            message_type = "food"
    except Exception as e:
        print(f"Ошибка классификации: {e}. Используем 'food' по умолчанию.", flush=True)
        message_type = "food"
        confidence = 0.0

    if message_type == "photo":
        print("PHOTO (от LLM)", flush=True)
        return {
            "message_type": message_type,
            "image_path": user_input,
            "messages": [HumanMessage(content=f"Классифицировано как {message_type}")]
        }
    else:
        print(f"Классификация вернула: {message_type}", flush=True)
        # Всегда возвращаем валидный тип (food)
        return {"message_type": "food"}


def router_after_classification(state: SystemState):
    message_type = state["message_type"]
    print(f"В router {message_type}")
    if message_type == "photo":
        return "photo"
    else:
        return "food"


async def food(state: SystemState):
    print("в func FOOD")
    messages = state.get("messages", [])
    if not messages:
        return {"messages": [HumanMessage(content="Нет сообщений для ответа.")]}

    system_msg = SystemMessage(
    content="Ты — эксперт по питанию и нутрициолог. Твоя задача — отвечать на любые вопросы о еде, калориях, БЖУ и здоровом питании. Если вопрос не касается этих тем, вежливо объясни, что ты специалист по питанию, и предложи помощь в этой области. Всегда давай полезные и точные советы, основанные на научных данных."
    )

    full_messages = [system_msg] + messages

    response = await llm_food.ainvoke(full_messages)
    answer_content = response.content

    return {
        "ai_response": [AIMessage(content=answer_content)],
        "messages": [AIMessage(content=answer_content)]
    }


def load_image_to_base64(source: str, max_size: int = 600) -> str:
    """
    Загружает изображение с ПРИНУДИТЕЛЬНЫМ сжатием
    """
    try:
        print(f"📥 Загрузка: {source[:100]}...", flush=True)

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

        print(f"📥 Исходный размер: {img.size}", flush=True)

        # ВСЕГДА сжимаем
        ratio = min(max_size / img.size[0], max_size / img.size[1])
        if ratio < 1:
            new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
            print(f"📥 Сжатие: {img.size} -> {new_size}", flush=True)
            img = img.resize(new_size, Image.Resampling.LANCZOS)

        # Конвертация в RGB
        if img.mode in ('RGBA', 'LA', 'P'):
            img = img.convert('RGB')

        # Сохранение с высоким сжатием
        buffer = BytesIO()
        img.save(buffer, format='JPEG', quality=75, optimize=True)
        image_bytes = buffer.getvalue()

        print(f"📥 Размер: {len(image_bytes) / 1024:.2f} KB", flush=True)

        return base64.b64encode(image_bytes).decode('utf-8')

    except Exception as e:
        print(f"❌ Ошибка: {e}", flush=True)
        raise ValueError(f"Не удалось загрузить изображение: {e}")
# AI analyze

def analysis_node(state: SystemState) -> dict:

    image_path = state.get("image_path")
    prompt = (
        "Ты — помощник по анализу еды. Опиши, что изображено на фотографии. "
        "Назови блюдо, перечисли основные ингредиенты, укажи примерную калорийность "
        "в килокалориях на 100 грамм или на порцию. Ответ дай в виде короткого текста, "
        "без лишней информации."
    )

    image_base64 = load_image_to_base64(image_path)
    url = f"{OLLAMA_BASE_URL}/api/chat"
    payload = {
        "model": QWEEN_VL_MODEL,
        "messages": [
            {
                "role": "user",
                "content": prompt,
                "images": [image_base64]
            }
        ],
        "stream": False,
        "options": {
            "num_ctx": 2048,  # ← Ограничить контекст
            "temperature": 0.3,  # ← Снизить креативность (0.1-0.5)
            "top_p": 0.9,
            "seed": 42  # ← Фиксированный сид для стабильности
        }
    }
    try:

        response = requests.post(url, json=payload, timeout=180)
        response.raise_for_status()
        result = response.json()
        content = result.get('message', {}).get('content', '').strip()
        if not content:
            content = "Не удалось распознать содержимое изображения."
            return {"ai_response": content}

        return {"ai_response": content,
                "messages": [AIMessage(content = content)]
        }

    except Exception as e:
        text_error = f"Ошибка при выполнения анализа: {e}"
        return {"ai_response": text_error}



def clear_state(state: SystemState) -> dict:
    print("ОЧИЩАЕМ ПОЛЯ", flush=True)
    return {
        "current_message": "",
        "message_type": "",
        "detections": [],
        "image_path": "",
        "scale": 0.0,
        "size_info": [],
        "result_calories": "",
        "ai_response": ""
    }
