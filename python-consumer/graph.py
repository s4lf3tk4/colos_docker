from core import SystemState, llm, llm_food, classification_prompt, classification_parser
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from ultralytics import YOLO
from PIL import Image
from io import BytesIO

import requests
from bs4 import BeautifulSoup
from ddgs import DDGS

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


# def classify_message(state: SystemState) -> dict:
#     user_input = state["current_message"]
#     classification_chain = classification_prompt | llm | classification_parser
#     try:
#         classification_result = classification_chain.invoke({"user_input": user_input})
#         message_type = classification_result.get("message_type")
#         if not message_type:
#             print("ОШИБКА В КЛАССИФИКАЦИИ")
#         confidence = classification_result.get("confidence", 0.0)
#     except Exception as e:
#         print(f"Ошибка классификации: {e}. Используем 'food' по умолчанию.")
#         message_type = "food"
#         confidence = 0.0

#     if message_type == "photo":
#         print("PHOTO")
#         return {
#             "message_type": message_type,
#             "image_path": state["current_message"],
#             "messages": [HumanMessage(content=f"Классифицировано как {message_type}")]
#         }
#     return {
#         "message_type": message_type
#     }


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


# YOLO

from ultralytics import YOLO
from PIL import Image
from io import BytesIO
import requests
from langchain_core.messages import HumanMessage

def get_yolo_model(model_path: str = "best.pt"):
    if model_path not in _yolo_models:
        _yolo_models[model_path] = YOLO(model_path)
    return _yolo_models[model_path]

def load_image(source: str):
    if source.startswith(("http://", "https://")):
        response = requests.get(source, timeout=10)
        response.raise_for_status()
        return Image.open(BytesIO(response.content))
    else:
        return Image.open(source)

def calculate_pixels(x1, y1, x2, y2):
    width = abs(x2 - x1)
    height = abs(y2 - y1)
    return max(width, height)

# ========== УЗЕЛ КАЛИБРОВКИ ==========
async def scale_node(image_path):
    try:
        model = get_yolo_model("models/model_calibrations.pt")
        img = load_image(image_path)
        results = model(img)

        fork_pixels = None
        for r in results:
            boxes = r.boxes
            if boxes is not None:
                for box in boxes:
                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    cls = int(box.cls[0])
                    if model.names[cls] == "fork":
                        fork_pixels = calculate_pixels(x1, y1, x2, y2)
                if fork_pixels is not None:
                    break

        if fork_pixels is None:
            return None

        REAL_FORK_LENGTH_CM = 11.0
        scale = fork_pixels / REAL_FORK_LENGTH_CM
        print(f"\n\nМасштаб: {scale:.2f} px/см (вилка {fork_pixels:.0f} px)\n\n")

        return scale

    except Exception as e:
        return None
# ========== УЗЕЛ АНАЛИЗА ==========

EXCLUDED_CLASSES = {"fork", "spoon", "knife", "dining table", "cup", "bowl"}

async def analysis_node(state: SystemState) -> dict:
    print("В func analysis")
    image_path = state.get("image_path")
    print(f"image_path = {image_path}")
    if not image_path:
        return {"messages": [HumanMessage(content="❌ Нет пути к изображению.")]}

    scale = await scale_node(image_path)
    if scale is None:
        return {"messages": [AIMessage(content="❌ Масштаб не задан.")]}

    try:
        model = get_yolo_model("models/model_food.pt")
        img = load_image(image_path)
        results = model(img, verbose=False)

        detections = []
        for r in results:
            boxes = r.boxes
            if boxes is not None:
                for box in boxes:
                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    conf = float(box.conf[0])
                    cls = int(box.cls[0])
                    class_name = model.names[cls]
                    if class_name.lower() in EXCLUDED_CLASSES:
                        continue
                    detections.append({
                        "class": class_name,
                        "confidence": conf,
                        "bbox": [x1, y1, x2, y2]
                    })

        print(f"Результаты анализа (масштаб: {scale:.2f} px/см):")
        msg_lines = []
        for det in detections:
            class_name = det["class"]
            x1, y1, x2, y2 = det["bbox"]
            width_px = abs(x2 - x1)
            height_px = abs(y2 - y1)
            real_length = max(width_px, height_px) / scale
            real_width = min(width_px, height_px) / scale
            real_size = real_length * real_width * real_width/4
            line = f"• {class_name}: {real_size:.1f} см^3"
            msg_lines.append(line)

        if not detections:
            print("Объектов не обнаружено.")
            msg_lines.append("Объектов не обнаружено.")

        return {
            "messages": [HumanMessage(content="\n".join(msg_lines))],
            "detections": detections,
            "size_info": msg_lines
        }

    except Exception as e:
        return {
            "messages": [HumanMessage(content=f"❌ Ошибка анализа: {e}")]
        }

async def analyze_calories(state: SystemState) -> dict:
    # Извлекаем список классов из детекций
    detections = state.get("detections", [])
    if not detections:
        last_message = state["messages"][-1]
        # Извлекаем содержимое последнего сообщения
        last_text = last_message.content if hasattr(last_message, 'content') else str(last_message)
        new_message = last_text + "\nНет объектов для расчёта калорий."
        return {"messages": [AIMessage(content=new_message)]}

    # Собираем уникальные названия продуктов
    product_names = list(set(d["class"] for d in detections))

    calorie_info = []
    for product in product_names:
        search_result = web_search(f"калорийность {product} на 100 грамм")
        prompt = f"""
        Ты - нутрициолог. На основе следующей информации определи примерное количество калорий на 100 грамм продукта '{product}'.

        Информация из поиска:
        {search_result}

        Если информации недостаточно, используй свои знания. Ответь только числом (ккал на 100 г), без пояснений.
        """
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        calorie_value = response.content.strip()
        calorie_info.append(f"{product}: {calorie_value} ккал/100г")

    result_message = "Расчёт калорийности:\n" + "\n".join(calorie_info)

    return {
        "messages": [AIMessage(content=result_message)],
        "result_calories": result_message
    }

def web_search(query: str) -> str:
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=5))
            if not results:
                return "Ничего не найдено."

            for idx, result in enumerate(results):
                url = result.get('href')
                if not url:
                    continue
                try:
                    resp = requests.get(url, timeout=10)
                    soup = BeautifulSoup(resp.text, 'html.parser')

                    # Извлекаем все параграфы
                    paragraphs = soup.find_all('p')
                    if paragraphs:
                        full_text = ' '.join(p.get_text(strip=True) for p in paragraphs)
                    else:
                        full_text = soup.body.get_text(separator='\n', strip=True) if soup.body else ""

                    max_chars = 5000
                    if len(full_text) > max_chars:
                        full_text = full_text[:max_chars]

                    if full_text.strip():
                        return f"Источник: {url}\n\n{full_text}"

                except Exception as e:
                    print(f"Не удалось загрузить {url}: {e}")
                    continue

            if results:
                first = results[0]
                return f"{first.get('title', 'Без заголовка')}: {first.get('body', 'Нет описания')}"
            else:
                return "Не удалось получить содержимое ни с одного сайта."

    except Exception as e:
        return f"Ошибка поиска: {e}"


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
