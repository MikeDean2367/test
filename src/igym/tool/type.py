from enum import Enum, auto
from typing import Optional, Dict, Any, List, Union, Callable
from pydantic import BaseModel, Field, validator
from datetime import datetime
from igym.type.exception import iGymException

class ToolExecutionStatus(str, Enum):
    RUNNING = "Running"
    ERROR = "Error"
    COMPLETED = "Completed"
    TIMEOUT = "Timeout"
    
class ToolType(str, Enum):
    SESSION_BASED = "session_based"
    SESSION_FREE = "session_free"
    
class ToolMetadata(BaseModel):
    name: str
    description: str
    tool_type: ToolType
    timeout: Optional[float] = None
    require_session: bool = False

class ToolExecutionResult(BaseModel):
    status: ToolExecutionStatus
    output: Optional[Any] = None
    error: Optional[str] = None
    execution_time: Optional[float] = None
    timestamp: datetime = Field(default_factory=datetime.now)

class ToolRegistration(BaseModel):
    """Complete tool registration information"""
    name: str
    description: str
    parameters: Dict = Field(default_factory=dict)
    tool_type: ToolType
    timeout: Optional[float] = None
    require_session: bool = False
    func: Callable
    owner_class: Optional[str] = None  # For class methods
    version:str = 'v1'

class SessionStatus(str, Enum):
    INIT = "initialized"
    RUNNING = "running"
    STOPPED = "stopped"

class SessionState(BaseModel):
    """Base model for session state"""
    status: SessionStatus
    created_at: datetime = Field(
        default_factory=datetime.now,
        frozen=True,
        description="Timestamp of initial creation"
    )
    updated_at: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp of last update"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary session metadata"
    )

    # @validator("*", pre=True)
    # def _auto_update_timestamp(cls, value, values, field):
    #     """Auto-update updated_at on field changes"""
    #     if field.name != "updated_at" and not field.name.startswith("_"):
    #         values["updated_at"] = datetime.now()
    #     return value

class iGymToolException(iGymException):
    """Base exception for tool-related errors"""
    def __init__(self, message: str, tool_name: Optional[str] = None):
        self.tool_name = tool_name
        self.message = message
        super().__init__(f"{f'[{tool_name}] ' if tool_name else ''}{message}")

class iGymToolTimeoutException(iGymToolException):
    """Exception raised when a tool execution times out"""
    def __init__(self, tool_name: str, timeout: float):
        super().__init__(
            tool_name=tool_name,
            message=f"Tool timed out after {timeout} seconds"
        )
        self.timeout = timeout

class iGymToolExecutionException(iGymToolException):
    """Exception raised when a tool execution fails"""
    def __init__(self, tool_name: str, error: str):
        super().__init__(
            tool_name=tool_name,
            message=f"Tool execution failed: {error}"
        )
        self.original_error = error

class iGymToolRegistrationException(iGymToolException):
    """Exception raised when tool registration fails"""
    def __init__(self, tool_name: str, reason: str):
        super().__init__(
            tool_name=tool_name,
            message=f"Tool registration failed: {reason}"
        )

