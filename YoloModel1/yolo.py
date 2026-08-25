import asyncio
import re
from pathlib import Path
from typing import Annotated, Sequence, TypedDict, List, Literal
import json

import numpy as np

import sys
from aio_pika import Message, DeliveryMode

import requests
from bs4 import BeautifulSoup
from ddgs import DDGS
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, AIMessage
from langchain_core.tools import tool
from langchain_ollama import ChatOllama
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import create_react_agent, ToolNode
from pydantic import BaseModel, Field
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate

import torch

import threading

# import os
import base64
# import aiosqlite
# from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
# import aio_pika

class SystemState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    current_message: str
    message_type: str
    detections: List[dict]
    image_path: str
    scale: float
    size_info: List[str]
    result_calories: str
    ai_response: Annotated[Sequence[str], add_messages]
    final_output: str


class Classification(BaseModel):
    message_type: Literal["photo", "food"] = Field(
        description = "Тип сообщения: photo - ссылка на фото; food - вопрос по питанию или истории диалога"
    )
    confidence: float = Field(
        description = "Уверенность в классификации",
        ge = 0.0, le = 1.0
    )

classification_parser = JsonOutputParser(pydantic_object = Classification)
classification_prompt = PromptTemplate(template = """Определи тип сообщения пользователя:
    PHOTO - ссылка на фото (например: /app/storage/test2.png)
    FOOD - вопрос или сообщение, связанный только с питанием, едой или историей сообщений
    Сообщение: {user_input}

    {format_instructions}

    Верни ТОЛЬКО JSON!
""",
    input_variables = ["user_input"],
    partial_variables={"format_instructions": classification_parser.get_format_instructions()}
)

llm = ChatOllama(
    model="mistral",
    base_url="http://localhost:11434",
    num_predict=2000
)
llm_food = ChatOllama(
    model="llama3.2:3b",
    base_url="http://localhost:11434",
    num_predict=2000
)

_yolo_models = {}

def classify_message(state: SystemState) -> dict:
    user_input = state["current_message"]

    # === ПРОВЕРКА ПО РАСШИРЕНИЮ (ОСНОВНОЙ СПОСОБ) ===
    if (user_input.startswith("/app/storage/") and
        any(user_input.lower().endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"])):
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
        # Всегда возвращаем валидный тип (food)
        return {"message_type": "food"}


def router_after_classification(state: SystemState):
    message_type = state["message_type"]
    if message_type == "photo":
        return "photo"
    elif message_type == "food":
        return "food"
    else:
        return "photo"

async def food(state: SystemState):
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
        "ai_response": [answer_content],
        "messages": [AIMessage(content=answer_content)]
    }



async def final_node(state: SystemState):
    raw_messages = state.get("ai_response", [])
    texts = []
    for msg in raw_messages:
        if hasattr(msg, 'content'):      # для BaseMessage (HumanMessage, AIMessage)
            texts.append(msg.content)
        elif isinstance(msg, str):
            texts.append(msg)
        else:
            texts.append(str(msg))       # fallback
    full_text = "\n".join(texts)
    print(f"=== ИТОГОВЫЙ ОТВЕТ ===\n{full_text}")
    return {"final_output": full_text}


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
        "ai_response": []
    }


import time
from pynvml import *

nvmlInit()
handle = nvmlDeviceGetHandleByIndex(0)
# def get_gpu_memory_fast():
#     info = nvmlDeviceGetMemoryInfo(handle)
#     return info.used // 1024**2

# Получаем URL Ollama из окружения
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
QWEN_VL_MODEL = os.getenv("QWEN_VL_MODEL", "qwen3-vl:4b-q4ks ")


def encode_image_to_base64(image_path: str) -> str:
    """Читает изображение и кодирует в base64."""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def qween_vl(state: SystemState) -> dict:
    print("\nВ qween\n")
    # Замеряем базовое значение после прогрева
    base_vram = get_gpu_memory_fast()

    # Мониторинг пика
    peak_vram = base_vram
    stop_monitor = False

    def monitor():
        nonlocal peak_vram
        while not stop_monitor:
            current = get_gpu_memory_fast()
            if current > peak_vram:
                peak_vram = current
            time.sleep(0.01)

    monitor_thread = threading.Thread(target=monitor)
    monitor_thread.start()
    anser = ""

    image_path = state.get("image_path")
    prompt = (
        "Ты — помощник по анализу еды. Опиши, что изображено на фотографии. "
        "Назови блюдо, перечисли основные ингредиенты, укажи примерную калорийность "
        "в килокалориях на 100 грамм или на порцию. Ответ дай в виде короткого текста, "
        "без лишней информации."

    )

    image_base64 = encode_image_to_base64(image_path)
    url = f"{OLLAMA_BASE_URL}/api/chat"
    payload = {
        "model": QWEN_VL_MODEL,
        "messages": [
            {
                "role": "user",
                "content": prompt,
                "images": [image_base64]
            }
        ],
        "stream": False
    }
    try:

        start_time = time.perf_counter()
        response = requests.post(url, json=payload, timeout=180)
        end_time = time.perf_counter()
        elapsed = end_time - start_time
        print(f"\nВремя выполнения qween:8b: {elapsed:.2f} сек\n")
        response.raise_for_status()
        result = response.json()
        print(f"RAW RESULT: {result}", flush=True)
        content = result.get('message', {}).get('content', '').strip()
        if not content:
            content = "⚠️ Не удалось распознать содержимое изображения."
        print(f"QWEEN: {result.get('message', {}).get('content', 'Не удалось получить ответ.')}\n", flush=True)
        anser += "\n" + f"QWEEN: {result.get('message', {}).get('content', 'Не удалось получить ответ.')}\n"
        current_message = state.get("ai_response")
        new_message = current_message + [anser]

        stop_monitor = True
        monitor_thread.join()

        print(f"Базовое VRAM: {base_vram} МБ")
        print(f"Пик VRAM: {peak_vram} МБ")
        print(f"Оверхед: {peak_vram - base_vram:.0f} МБ", flush=True)

        return {"ai_response": new_message}

    except Exception as e:
        stop_monitor = True
        monitor_thread.join()

        print(f"Базовое VRAM: {base_vram} МБ")
        print(f"Пик VRAM: {peak_vram} МБ")
        print(f"Оверхед: {peak_vram - base_vram:.0f} МБ", flush=True)

        return {"ai_response": new_message}

        return {"ai_response": new_message}

# def qween_vl(state: SystemState) -> str:
#     print("\nВ qween\n")
#     before = get_gpu_memory_fast()
#     print(f"\nbefore: {before}\n")
#     anser = ""
#     """
#     Отправляет изображение в Ollama (модель Qwen VL) и возвращает ответ.
#     """
#     image_path = state.get("image_path")
#     prompt = (
#         "Ты — помощник по анализу еды. Опиши, что изображено на фотографии. "
#         "Назови блюдо, перечисли основные ингредиенты, укажи примерную калорийность "
#         "в килокалориях на 100 грамм или на порцию. Ответ дай в виде короткого текста, "
#         "без лишней информации."
#     )

#     # Кодируем изображение
#     image_base64 = encode_image_to_base64(image_path)
#     print("\n image_base64 = encode_image_to_base64(image_path)\n")


#     # Формируем запрос к Ollama API (чат)
#     url = f"{OLLAMA_BASE_URL}/api/chat"
#     print(f"\n url: {url} \n")
#     payload = {
#         "model": QWEN_VL_MODEL,
#         "messages": [
#             {
#                 "role": "user",
#                 "content": prompt,
#                 "images": [image_base64]
#             }
#         ],
#         "stream": False
#     }
#     print("\n В АНАЛИЗ\n")
#     try:

#         start_time = time.perf_counter()
#         response = requests.post(url, json=payload, timeout=60)
#         end_time = time.perf_counter()
#         elapsed = end_time - start_time

#         print(f"\nВремя выполнения qween:8b: {elapsed:.2f} сек\n")

#         response.raise_for_status()
#         result = response.json()
#         print(f"QWEEN: {result.get("message", {}).get("content", "Не удалось получить ответ.")}\n")
#         anser += "\n" + f"QWEEN: {result.get("message", {}).get("content", "Не удалось получить ответ.")}\n"
#         current_message = state.get("ai_response")
#         new_message = current_message + [anser]
#         #after = get_gpu_memory_fast()
#         #print(f"VRAM использовано: {after - before:.1f} МБ")
#         #return {"ai_response": new_message}
#     except Exception as e:
#         anser +=f"Ошибка при запросе к Qwen VL: {e}"
#         current_message = state.get("ai_response")
#         new_message = current_message + [anser]
#         #return {"ai_response": new_message}
#     after = get_gpu_memory_fast()
#     print(f"VRAM использовано: {after - before:.1f} МБ")



# YOLO

from ultralytics import YOLO
from PIL import Image
from io import BytesIO
import requests
from langchain_core.messages import HumanMessage

def get_gpu_memory_fast():
    """Текущее использование VRAM в МБ"""
    if torch.cuda.is_available():
        return torch.cuda.memory_allocated() / 1024**2
    return 0

def get_peak_vram():
    """Пиковое использование VRAM в МБ"""
    if torch.cuda.is_available():
        return torch.cuda.max_memory_allocated() / 1024**2
    return 0

def get_yolo_model(path):
    model = YOLO(path)
    # ЯВНО перекидываем на GPU
    if torch.cuda.is_available():
        model = model.to('cuda')
        print(f"✅ Модель загружена на GPU: {torch.cuda.get_device_name(0)}")
    else:
        print("⚠️ CUDA недоступна, работаем на CPU")
    return model

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
        torch.cuda.reset_peak_memory_stats()
        model = get_yolo_model("model_calibration.pt")

        peak_after_load = torch.cuda.max_memory_allocated() / 1024**2  # В МБ
        print(f"ПИК VRAM после загрузки: {peak_after_load:.0f} МБ ({peak_after_load/1024:.2f} ГБ)")

        # 4️⃣ Инференс — память не растет
        img = load_image(image_path)
        results = model(img)

        fork_pixels = None
        for r in results:
            boxes = r.boxes
            if boxes is not None:
                for box in boxes:
                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    cls = int(box.cls[0])
                    print(f"  класс: {model.names[cls]}, уверенность: {box.conf[0].item()}")
                    if model.names[cls] == "fork":
                        fork_pixels = calculate_pixels(x1, y1, x2, y2)
                if fork_pixels is not None:
                    break

        if fork_pixels is None:
            return None

        REAL_FORK_LENGTH_CM = 11.0
        scale = fork_pixels / REAL_FORK_LENGTH_CM
        print(f"\n\nМасштаб: {scale:.2f} px/см (вилка {fork_pixels:.0f} px)\n\n", flush=True)


        peak_total = torch.cuda.max_memory_allocated() / 1024**2
        print(f"ПИК VRAM общий: {peak_total:.0f} МБ ({peak_total/1024:.2f} ГБ)")

        # Текущее использование
        current_vram = get_gpu_memory_fast()
        print(f"ТЕКУЩАЯ VRAM: {current_vram:.0f} МБ")
        return scale

    except Exception as e:
        print(f"scale_node ошибка: {e}")
        return None
# ========== УЗЕЛ АНАЛИЗА ==========

EXCLUDED_CLASSES = {"fork", "spoon", "knife", "dining table", "cup", "bowl"}

async def yolo_analysis(state: SystemState) -> dict:
    torch.cuda.reset_peak_memory_stats()
    anser = ""
    print("=" * 60 + "\n")
    anser += "=" * 60 + "\n"
    anser += "==YOLO== \n"
    image_path = state.get("image_path")
    print(f"image_path = {image_path}")
    if not image_path:
        anser += "❌ Нет пути к изображению."
        current = state.get("ai_response", [])
        new_response = current + [anser]
        return {"ai_response": new_response}   # здесь detections не обновляются, но это ошибка – лучше вернуть пустой список

    start_time = time.perf_counter()
    scale = await scale_node(image_path)
    if scale is None:
        anser += "❌ Масштаб не задан."
        current = state.get("ai_response", [])
        new_response = current + [anser]
        # Важно: возвращаем состояние с пустыми detections, чтобы следующий узел понял, что объектов нет
        return {
            "ai_response": new_response,
            "detections": [],
            "scale": 0.0,
            "size_info": []
        }

    try:
        torch.cuda.reset_peak_memory_stats()
        model = get_yolo_model("model_food.pt")

        # Пик после загрузки модели
        peak_after_load = torch.cuda.max_memory_allocated() / 1024**2
        print(f"ПИК VRAM после загрузки: {peak_after_load:.0f} МБ ({peak_after_load/1024:.2f} ГБ)")

        img = load_image(image_path)
        results = model(img, verbose=False)

        # Общий пик (включая инференс)
        peak_total = torch.cuda.max_memory_allocated() / 1024**2
        print(f"ПИК VRAM общий: {peak_total:.0f} МБ ({peak_total/1024:.2f} ГБ)")

        # Текущее потребление (для сравнения)
        current_vram = get_gpu_memory_fast()
        print(f"ТЕКУЩАЯ VRAM: {current_vram:.0f} МБ")

    # try:

    #     model = get_yolo_model("model_food.pt")
    #     img = load_image(image_path)
    #     results = model(img, verbose=False)
    #     peak_vram = get_gpu_memory_fast()
    #     print(f"PEAK_BASE:{peak_vram}")

        detections = []
        size_info = []
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
        end_time = time.perf_counter()
        elapsed = end_time - start_time
        print(f"Время выполнения yolo+scale: {elapsed:.2f} сек", flush = True)
        print(f"Результаты анализа (масштаб: {scale:.2f} px/см):\n", flush=True)
        anser += f"Результаты анализа (масштаб: {scale:.2f} px/см):\n"
        for det in detections:
            class_name = det["class"]
            x1, y1, x2, y2 = det["bbox"]
            width_px = abs(x2 - x1)
            height_px = abs(y2 - y1)
            real_length = max(width_px, height_px) / scale
            real_width = min(width_px, height_px) / scale
            real_size = real_length * real_width * real_width / 4
            line = f"• {class_name}: {real_size:.1f} см^3\n"
            size_info.append(line)
            anser += line

        if not detections:
            print("Объектов не обнаружено.", flush=True)
            anser += "Объектов не обнаружено."

        # ✅ Возвращаем все обновлённые поля
        current = state.get("ai_response", [])
        new_response = current + [anser]
        print(f"ИИ:{anser}")
        return {
            "ai_response": new_response,
            "detections": detections,
            "scale": scale,
            "size_info": size_info
        }
    except Exception as e:
        print(f"Ошибка в yolo_analysis: {e}", flush=True)
        current = state.get("ai_response", [])
        new_response = current + [anser + f"\nОшибка: {e}"]
        return {
            "ai_response": new_response,
            "detections": [],
            "scale": 0.0,
            "size_info": []
        }

async def yolo_analysis_search(state: SystemState) -> dict:
    anser = ""
    # Извлекаем список классов из детекций

    detections = state.get("detections", [])
    if not detections:
        last_message = state["messages"][-1]
        # Извлекаем содержимое последнего сообщения
        last_text = last_message.content if hasattr(last_message, 'content') else str(last_message)
        new_message = last_text + "\nНет объектов для расчёта калорий."
        anser +="\nНет объектов для расчёта калорий."
        return {"ai_response": [anser]}

    product_names = list(set(d["class"] for d in detections))

    calorie_info = []
    start_time = time.perf_counter()

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
        calorie_info.append(f"{product}: {calorie_value}")

    end_time = time.perf_counter()
    elapsed = end_time - start_time
    print(f"Время выполнения search: {elapsed:.2f} сек", flush = True)



    result_message = "Расчёт калорийности:\n" + "\n".join(calorie_info)
    anser +="Расчёт калорийности:\n" + "\n".join(calorie_info) + "\n"
    print("\n"+ "=" * 60 + "\n")
    anser += "\n"+ "=" * 60 + "\n"
    return {"ai_response": [anser]}

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



graph = StateGraph(SystemState)

app = None

async def init_app():
    global app
    app = graph.compile()
    return app

graph.add_node("classify_message", classify_message)
graph.add_node("food", food)
graph.add_node("qween_vl", qween_vl)
graph.add_node("clear_state", clear_state)
graph.add_node("final_node", final_node)
graph.add_node("yolo_analysis", yolo_analysis)
# graph.add_node("yolo_analysis_search", yolo_analysis_search)


graph.add_edge(START, "classify_message")
graph.add_conditional_edges(
    "classify_message",
    router_after_classification,
    {
        "photo": "yolo_analysis",
        "food": "food"
    }
)
#graph.add_edge("qween_vl", "yolo_analysis")
graph.add_edge("yolo_analysis", END)
# graph.add_edge("yolo_analysis_search", "final_node")
graph.add_edge("food", "clear_state")
graph.add_edge("final_node", "clear_state")
graph.add_edge("qween_vl", END)

async def graph_start(response_text: str) -> dict:
    global app
    if app is None:
        await init_app()
    initial_state = {
        "messages": [HumanMessage(content=response_text)],
        "current_message": response_text,
        "message_type": "",
        "detections" : [],
        "image_path":"",
        "scale": "",
        "size_info":[],
        "result_calories": "",
        "ai_response": []

    }
    result = await app.ainvoke(initial_state)
    return result

import os
import aio_pika


def convert_to_serializable(obj):
    if isinstance(obj, (np.integer, np.int64)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float32, np.float64)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif hasattr(obj, 'content'):
        return obj.content
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

async def main():

    files = [
        "test.png", "test1.png", "test2.png", "test3.png", "test4.png",
        "test5.png", "test6.png", "test7.png", "test8.png", "test9.png"
    ]

    for idx, request in enumerate(files, start=1):
        print(f"\n{'='*50}\n")
        print(f"Обработка {idx}/{len(files)}: {request}\n")

        try:
            result = await graph_start(request)
            print(f"\n{'='*50}\n")
        except Exception as e:
            print(f"❌ Ошибка при обработке {request}: {e}")
            continue


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Остановка потребителя.")
        sys.exit(0)
