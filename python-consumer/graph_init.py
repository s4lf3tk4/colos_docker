from langgraph.graph import END, START, StateGraph

from core import SystemState
from graph import analysis_node, classify_message, food, route_after_classification


def build_graph():
    builder = StateGraph(SystemState)
    builder.add_node("classify_message", classify_message)
    builder.add_node("analysis_node", analysis_node)
    builder.add_node("food", food)

    builder.add_edge(START, "classify_message")
    builder.add_conditional_edges(
        "classify_message",
        route_after_classification,
        {"photo": "analysis_node", "food": "food", "error": END},
    )
    builder.add_edge("analysis_node", END)
    builder.add_edge("food", END)
    return builder.compile()


app = build_graph()


async def graph_start(message_text: str, user_id: str) -> dict:
    """Один запрос — один вызов. Никакой персистентности: память картинки в Redis."""
    return await app.ainvoke(
        {"current_message": message_text, "user_id": str(user_id)}
    )
