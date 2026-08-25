import copy
from typing import TypedDict


class KBGraphState(TypedDict, total=False):
    task_id: str  # for realtime tracking of task status

GRAPH_DEFAULT_STATE: KBGraphState = {
    "task_id": "",
}

def create_default_state(**overrides) -> KBGraphState:
    state = copy.deepcopy(GRAPH_DEFAULT_STATE)
    state.update(overrides)
    return state

def get_default_state() -> KBGraphState:
    return copy.deepcopy(GRAPH_DEFAULT_STATE)