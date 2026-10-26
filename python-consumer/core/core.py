from typing import Literal, NotRequired, TypedDict


class SystemState(TypedDict):
    current_message: str
    user_id: str
    message_type: NotRequired[Literal["food", "photo", "error"]]
    ai_response: NotRequired[str]
