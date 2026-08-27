from typing import TypedDict, List, Sequence, Literal, Annotated
import aiosqlite
from pydantic import BaseModel, Field
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, AIMessage

from langgraph.graph.message import add_messages

import os

class SystemState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    current_message: str
    message_type: str
    image_path: str
    ai_response: str
