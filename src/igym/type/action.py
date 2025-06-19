from igym.type.base import Transaction, TransactionType
from typing import List, Any, Union
from igym.type.tool_call import ToolCallingItem
from pydantic import validator, BaseModel
from igym.type.observation import OutwardObservation
from datetime import datetime
from copy import deepcopy

class BaseAction(Transaction):
    def __init__(self, **data):
        super().__init__(transaction_type=TransactionType.ACTION, **data)

class InwardAction(BaseAction):
    info: Any

class OutwardAction(BaseAction):
    tool_calls: List[ToolCallingItem]

    @validator('tool_calls', pre=True)
    def ensure_tool_calls_is_list(cls, v):
        if v is None:
            return []
        if isinstance(v, ToolCallingItem):
            return [v]
        # if isinstance(v, list):
        #     return [item if isinstance(item, ToolCallingItem) else ToolCallingItem(**item) for item in v]
        raise ValueError("The type of field `tool_calls` must be the class `ToolCallingItem`.")

    def create_observation(self, copy:bool=False) -> OutwardObservation:
        observation = OutwardObservation(
            tool_calls=self.tool_calls if not copy else deepcopy(self.tool_calls),
            sender=self.sender,
            receivers=self.receivers,
            timestamp=datetime.utcnow,
            metadata=self.metadata,
            priority=self.metadata,
            expiration=self.expiration
        )
        return observation

class MemoryAction(BaseAction):
    pass


Action = Union[InwardAction, OutwardAction, MemoryAction]
ActionList = List[Action]

def is_action_list(actions: ActionList) -> bool:
    if isinstance(actions, list):
        for action in actions:
            if not isinstance(action, Action):
                return False
        return True
    return False
