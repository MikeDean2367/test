from typing import *
from pydantic import BaseModel, Field
from igym.backend.base import BackendConfig, BackendInput, BackendOutput
from igym.type.exception import iGymException

class AgentConfig(BaseModel):
    name: str
    memory_config: Dict
    backend_config: BackendConfig
    tool_config: List[str]
    receivers: Optional[Union[List[str], str]] = None

class iGymAgentException(iGymException):
    pass

