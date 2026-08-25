import aiosqlite
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import END, START, StateGraph
from langchain_core.messages import HumanMessage
from core import SystemState
from graph import (
    classify_message,
    router_after_classification,
    food,
    analysis_node,
)

graph = StateGraph(SystemState)

app = None

async def init_app():
    global app
    db = await aiosqlite.connect("checkpoints.db")
    checkpointer = AsyncSqliteSaver(db)
    app = graph.compile(checkpointer=checkpointer)
    return app


graph.add_node("classify_message", classify_message)
graph.add_node("analysis_node", analysis_node)
graph.add_node("food", food)


graph.add_edge(START, "classify_message")
graph.add_conditional_edges(
    "classify_message",
    router_after_classification,
    {
        "photo": "analysis_node",
        "food": "food"
    }
)
graph.add_edge("analysis_node", END)
graph.add_edge("food", END)

async def graph_start(response_text: str, user_id: str) -> dict:
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
        "ai_response": ""

    }
    config = {"configurable": {"thread_id": user_id}}
    result = await app.ainvoke(initial_state, config=config)
    return result
