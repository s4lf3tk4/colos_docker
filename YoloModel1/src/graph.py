import asyncio
import re
from pathlib import Path
from typing import Annotated, Sequence, TypedDict, List, Literal

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
import requests

from langgraph.checkpoint.memory import InMemorySaver

import aiosqlite
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

import sys

class SystemState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    current_message: str
    message_type: str
    detections: List[dict]
    image_path: str
    scale: float

class Classification(BaseModel):
    message_type: Literal["photo", "food"] = Field(
        description = "Тип сообщения: photo - ссылка на фото;  dialog - простой диалог"
    )
    confidence: float = Field(
        description = "Уверенность в классификации",
        ge = 0.0, le = 1.0
    )

classification_parser = JsonOutputParser(pydantic_object = Classification)
classification_prompt = PromptTemplate(template = """Определи тип сообщения пользователя:
    PHOTO - ссылка на фото.
    FOOD - сообщение от пользователя, связанное с питанием, кллориями или БЖУ.

    Сообщение: {user_input}

    {format_instructions}

    Верни ТОЛЬКО JSON!
""",
    input_variables = ["user_input"],
    partial_variables={"format_instructions": classification_parser.get_format_instructions()}
)

llm = ChatOllama(
    model="llama3.2:3b",
    base_url="http://localhost:11434",
    num_predict=2000
)

graph = StateGraph(SystemState)

@graph.add_node
def classify_message(state: SystemState) -> dict:
    user_input = state["current_message"]
    classification_chain = classification_prompt | llm | classification_parser
    try:
        classification_result = classification_chain.invoke({"user_input": user_input})
        message_type = classification_result.get("message_type", "food")
        confidence = classification_result.get("confidence", 0.0)
    except Exception as e:
        message_type = "food"
        confidence = 0.0

    print(f"Тип сообщения: {message_type}, уверенность: {confidence}")
    if message_type == "photo":
        return {
            "message_type": message_type,
            "image_path": state["current_message"],
            "messages": [HumanMessage(content=f"Классифицировано как {message_type}")]
        }
    return {
        "message_type": message_type
    }
def router_after_classification(state: SystemState):
    message_type = state["message_type"]
    if message_type == "photo":
        return "analysis_node"
    elif message_type == "food":
        return "food"



@graph.add_node
async def food(state: SystemState):
    messages = state.get("messages", [])
    if not messages:
        return {"messages": [HumanMessage(content="Нет сообщений для ответа.")]}

    system_msg = SystemMessage(content="Ты - специалист по питанию, настоящий нутрициолог, будь дружелюбным помощником")
    full_messages = [system_msg] + messages

    response = await llm.ainvoke(full_messages)

    answer_content = response.content
    return {
        "messages": [AIMessage(content=answer_content)]
    }

@graph.add_node
async def useless(state: SystemState):
    return {
        "messages": [AIMessage(content = "Я специалист по питанию, задавайте вопросы по существу!")]
    }

# YOLO

from ultralytics import YOLO
from PIL import Image
from io import BytesIO
import requests
from langchain_core.messages import HumanMessage

_yolo_models = {}

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
        model = get_yolo_model("model_forks.pt")
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

@graph.add_node
async def analysis_node(state: SystemState) -> dict:

    image_path = state.get("image_path")
    if not image_path:
        return {"messages": [HumanMessage(content="❌ Нет пути к изображению.")]}

    scale = await scale_node(image_path)
    if scale is None:
        return {"messages": [HumanMessage(content="❌ Масштаб не задан.")]}

    try:
        model = get_yolo_model("food_analysis.pt")
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
            real_size = real_length * real_width * real_width/2
            line = f"{class_name}: {real_size:.1f} см^3"
            print(line)
            msg_lines.append(line)

        if not detections:
            print("Объектов не обнаружено.")
            msg_lines.append("Объектов не обнаружено.")

        return {
            "messages": [HumanMessage(content="\n".join(msg_lines))],
            "detections": detections
        }

    except Exception as e:
        return {
            "messages": [HumanMessage(content=f"❌ Ошибка анализа: {e}")]
        }


@graph.add_node
async def analyze_calories(state: SystemState) -> dict:
    # Извлекаем список классов из детекций
    detections = state.get("detections", [])
    if not detections:
        return {"messages": [HumanMessage(content="Нет объектов для расчёта калорий.")]}

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


graph.add_edge(START, "classify_message")
graph.add_conditional_edges(
    "classify_message",
    router_after_classification,
    {
        "analysis_node": "analysis_node",
        "food": "food"
    }
)
graph.add_edge("analysis_node", "analyze_calories")
graph.add_edge("analyze_calories", END)
graph.add_edge("food", END)

app = None

async def init_app():
    global app
    db = await aiosqlite.connect("checkpoints.db")
    checkpointer = AsyncSqliteSaver(db)
    app = graph.compile(checkpointer=checkpointer)
    return app

async def graph_start(response_text: str, user_id: str) -> dict:
    if app is None:
        raise RuntimeError("App not initialized. Call init_app() first.")

    initial_state = {
        "messages": [HumanMessage(content=response_text)],
        "current_message": response_text,
        "message_type": "",
        "detections": [],
        "image_path": ""
    }
    config = {"configurable": {"thread_id": user_id}}
    result = await app.ainvoke(initial_state, config=config)
    return result   # возвращаем словарь

import os
import json
import aio_pika
from aio_pika import Message, DeliveryMode

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", 5672))
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "user")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "password")

def convert_to_serializable(obj):
    import numpy as np
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
    await init_app()
    connection = await aio_pika.connect_robust(
        host=RABBITMQ_HOST,
        port=RABBITMQ_PORT,
        login=RABBITMQ_USER,
        password=RABBITMQ_PASS
    )
    async with connection:
        channel = await connection.channel()

        # Объявляем очереди (durable)
        await channel.declare_queue("request_queue", durable=True)
        await channel.declare_queue("response_queue", durable=True)

        queue = await channel.declare_queue("request_queue", durable=True)

        async with queue.iterator() as queue_iter:
            print(" [*] Ожидание сообщений... Нажмите CTRL+C для выхода")
            async for message in queue_iter:
                async with message.process(requeue=False):
                    # Декодируем тело
                    body = message.body.decode()
                    try:
                        data = json.loads(body)
                    except json.JSONDecodeError:
                        print(" [!] Получено невалидное JSON-сообщение, пропускаем")
                        continue

                    request = data.get("request_text")
                    correlation_id = data.get("correlation_id")
                    user_id = data.get("user_id")
                    if not request or not correlation_id or not user_id:
                        print(" [!] Сообщение без 'request_text' или 'correlation_id' или 'user_id'")
                        continue

                    print(f" [x] Получена задача: {request} (corr_id={correlation_id})")

                    result = await graph_start(request, user_id)

                    # Извлекаем последнее сообщение (текстовый ответ)
                    last_message = result["messages"][-1] if result.get("messages") else None
                    output_text = last_message.content if last_message else ""

                    response = {
                        "correlation_id": correlation_id,
                        "status": "ok",
                        "result": {"message": output_text}
                    }



                    response_body = json.dumps(response, default=convert_to_serializable).encode()
                    await channel.default_exchange.publish(
                        Message(
                            body=response_body,
                            delivery_mode=DeliveryMode.PERSISTENT,
                            correlation_id=correlation_id
                        ),
                        routing_key="response_queue"
                    )
                    print(f" [x] Ответ отправлен для corr_id={correlation_id}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Остановка потребителя.")
        sys.exit(0)
