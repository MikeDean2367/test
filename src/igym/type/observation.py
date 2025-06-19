from igym.type.base import Transaction, TransactionType
from igym.type.tool_call import ToolCallingItem
from typing import Any, List, Union
from pydantic import validator, root_validator

class BaseObservation(Transaction):
    def __init__(self, **data):
        super().__init__(transaction_type=TransactionType.OBSERVATION, **data)

class InwardObservation(BaseObservation):
    content: str
    meta_result: Any

class OutwardObservation(BaseObservation):
    """这里需要处理一个情况：万一我们的action那边传出了多个tool_calls，这里的tool_calls应该是会被打包在一起的
    所以我们应该要把这些返回去的时候都统一放到一起，就是要等待在一起，这里我们应该怎么设计呢，需要有一个聚合机制"""
    tool_calls: List[ToolCallingItem]
    # contents: List[str]
    # meta_results: List[Any]

    # @validator('content')
    # def sync_content_to_tool_call(cls, v, values):
    #     """当content改变时，同步更新tool_call.content"""
    #     if 'tool_call' in values and values['tool_call']:
    #         values['tool_call'].content = v
    #     return v
    
"""
思考一下这里的数据流向：
- agent单次可以吐出多个action
- 
"""

Observation = Union[InwardObservation, OutwardObservation]
ObservationList = List[Observation]

def is_observation_list(observations: ObservationList) -> bool:
    if isinstance(observations, list):
        for observation in observations:
            if not isinstance(observation, Observation):
                return False
        return True
    return False
