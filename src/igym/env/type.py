from enum import Enum, auto
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from igym.tool.type import ToolExecutionResult, ToolExecutionStatus
from igym.type.exception import iGymException

class EnvStatus(str, Enum):
    INIT = "init"
    RUNNING = "running"
    ERROR = "error"
    CLOSED = "closed"
    READY = "ready"

class OutwardActionRecord(BaseModel):
    tool_name: str
    parameters: Dict[str, Any]
    result: Any
    s_timestamp: datetime = Field(default_factory=datetime.now)
    e_timestamp: datetime = Field(default_factory=datetime.now)
    status: ToolExecutionStatus = ToolExecutionStatus.RUNNING

class SessionConfig(BaseModel):
    class_name: str
    config: Dict[str, Any] = Field(default_factory=dict)
    tools: List[str] = Field(default_factory=list)

class EnvConfig(BaseModel):
    sessions: Dict[str, SessionConfig] = Field(default_factory=dict)
    tools: List[str] = Field(default_factory=list)
    tools_info: Dict[str, str] = Field(default_factory=dict)
    first_reciever: List[str] = Field(default_factory=list)

class iGymEnvException(iGymException):
    """Base exception for environment-related errors"""
    def __init__(self, message: str, env_name: Optional[str] = None):
        self.env_name = env_name
        self.message = message
        super().__init__(f"{f'[{env_name}] ' if env_name else ''}{message}")

class iGymEnvInitializationException(iGymEnvException):
    """Exception raised when environment initialization fails"""
    def __init__(self, env_name: str, reason: str):
        super().__init__(
            env_name=env_name,
            message=f"Environment initialization failed: {reason}"
        )
        self.reason = reason

class iGymEnvExecutionException(iGymEnvException):
    """Exception raised when environment execution fails"""
    def __init__(self, env_name: str, tool_name: str, error: str):
        super().__init__(
            env_name=env_name,
            message=f"Tool '{tool_name}' execution failed: {error}"
        )
        self.tool_name = tool_name
        self.original_error = error

class iGymEnvStateException(iGymEnvException):
    """Exception raised when environment state operations fail"""
    def __init__(self, env_name: str, operation: str, error: str):
        super().__init__(
            env_name=env_name,
            message=f"State {operation} failed: {error}"
        )
        self.operation = operation

