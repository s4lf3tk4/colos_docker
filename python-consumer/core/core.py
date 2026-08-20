from typing import TypedDict, List, Sequence, Literal, Annotated
import aiosqlite
from pydantic import BaseModel, Field
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, AIMessage

from langchain_ollama import ChatOllama

from langgraph.graph.message import add_messages

import os

from .settings import OLLAMA_BASE_URL

class SystemState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    current_message: str
    message_type: str
    detections: List[dict]
    image_path: str
    scale: float
    size_info: List[str]
    result_calories: str
    ai_response: str


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
    base_url=OLLAMA_BASE_URL,
    num_predict=2000
)
llm_food = ChatOllama(
    model="llama3.2:3b",
    base_url=OLLAMA_BASE_URL,
    num_predict=2000
)
