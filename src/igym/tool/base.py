from typing import Optional, Dict, Any, Callable, Type, Union, List
from functools import wraps
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
import inspect
from abc import ABC, abstractmethod
from .type import (
    SessionStatus,
    SessionState,

    ToolExecutionStatus, 
    ToolExecutionResult, 
    ToolRegistration,
    ToolType, 
    ToolMetadata,

    iGymToolException, 
    iGymToolTimeoutException, 
    iGymToolExecutionException,
    iGymToolRegistrationException
)
from datetime import datetime

def tool(
    description: str,
    tool_type: ToolType = ToolType.SESSION_FREE,
    name: Optional[str]=None,
    timeout: Optional[float] = None,
    require_session: bool = False
):
    """
    Decorator to register a function as a tool.
    
    Args:
        name: Name of the tool
        description: Description of the tool's functionality
        tool_type: Type of the tool (SESSION_BASED or SESSION_FREE)
        timeout: Timeout in seconds for the tool execution
        require_session: Whether the tool requires a session as first argument
    """
    def decorator(func: Callable):
        # Validate the function signature
        sig = inspect.signature(func)
        params = list(sig.parameters.values())
        
        if require_session and (len(params) == 0 or params[0].name != 'session'):
            raise iGymToolRegistrationException(
                tool_name=name,
                reason="First parameter must be named 'session' for session-based tools"
            )
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            result = None
            status = ToolExecutionStatus.COMPLETED
            error = None
            
            try:
                if timeout is not None:
                    with ThreadPoolExecutor(max_workers=1) as executor:
                        future = executor.submit(func, *args, **kwargs)
                        result = future.result(timeout=timeout)
                else:
                    result = func(*args, **kwargs)
            except FutureTimeoutError:
                status = ToolExecutionStatus.TIMEOUT
                error = f"Tool {name} timed out after {timeout} seconds"
                # raise iGymToolTimeoutException(tool_name=name, timeout=timeout)
            except Exception as e:
                status = ToolExecutionStatus.ERROR
                error = str(e)
                # raise iGymToolExecutionException(tool_name=name, error=str(e))
            finally:
                execution_time = time.time() - start_time
                if status == ToolExecutionStatus.COMPLETED and result is not None and isinstance(result, ToolExecutionResult):
                    return result
                return ToolExecutionResult(
                    status=status,
                    output=result,
                    error=error,
                    execution_time=execution_time
                )
        
        wrapper.tool_metadata = ToolMetadata(
            name=name if name else func.__name__,
            description=description,
            tool_type=tool_type,
            timeout=timeout,
            require_session=require_session
        )
        
        return wrapper
    return decorator

class MetaSession(type):

    _registry = {}

    def __new__(cls, name, bases, namespace, **kwargs):
        new_class = super().__new__(cls, name, bases, namespace)
        if name not in ('BaseSession',):  # 避免注册基类
            cls._registry[name] = new_class
        return new_class

class BaseSession(metaclass=MetaSession):

    @classmethod
    def get_cls(cls, name:str) -> object:
        if name in cls._registry:
            return cls._registry[name]
        return None

    def __init__(self, config:Optional[Dict[str, Any]]=None):
        """
        Initialize the session with optional configuration
        
        Args:
            config: Session-specific configuration
        """
        self.config = config or {}
        self._state = SessionState(status=SessionStatus.INIT)
    
    def start(self) -> None:
        """Start the session"""
        self._state.status = SessionStatus.RUNNING
        self._state.updated_at = datetime.now()

    def stop(self) -> None:
        """Stop the session"""
        self._state.status = SessionStatus.STOPPED
        self._state.updated_at = datetime.now()

    def reset(self) -> None:
        """Reset the session to initial state"""
        self._state = SessionState(status=SessionStatus.INIT)

    def get_state(self) -> SessionState:
        """Get current session state"""
        return self._state
    
    def is_active(self) -> bool:
        """Check if session is active"""
        return self._state.status == SessionStatus.RUNNING
    
    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

    def get_state(self) -> SessionState:
        """Get current session state"""
        return self._state
    
    def save(self) -> Dict[str, Any]:
        """Save session state for persistence"""
        return {
            "state": self._state.dict(),
            "config": self.config
        }

    @classmethod
    def load(cls, data: Dict[str, Any]) -> 'BaseSession':
        """Load session state from persistence"""
        session = cls(data.get("config"))
        session._state = SessionState.parse_obj(data.get("state"))
        return session

class ToolRegistry:
    """Global tool registry with unified registration"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._tools: Dict[str, ToolRegistration] = {}
            cls._instance._class_tools: Dict[str, ToolRegistration] = {}
            # cls._instance._classes: Dict[str, object] = {}
            cls._instance._class_tools_short_map: Dict[str, str] = {}       # tool_name: class.tool_name
            cls._instance._info: Dict[str, Any] = {}
        return cls._instance
    
    def set_info(self, info:Dict[str, Any]):
        self._info = info

    def get(self, name:str) -> Any:
        return self._info.get(name, None)

    def __getitem__(self, name:str) -> Optional[ToolRegistration]:
        return self.get_tool(name)
            
    def register(
        self,
        func: Optional[Callable] = None,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
        parameters: Optional[Dict] = None,
        tool_type: ToolType = ToolType.SESSION_FREE,
        timeout: Optional[float] = None,
        require_session: bool = False,
    ) -> Union[Callable, ToolRegistration]:
        """
        Unified tool registration decorator
        
        Can be used as:
        1. @register
        2. @register(name="tool_name", description="...")
        3. register(func, name="tool_name")
        """
        def decorator(f: Callable) -> Callable:
            # Determine tool name
            tool_name = name or f.__name__
            
            # Handle class methods - use class_name.method_name
            owner_class = None
            # print(f.__qualname__)
            if inspect.ismethod(f) or '.' in f.__qualname__:
                # owner_class = f.__objclass__.__name__
                owner_class:str = f.__qualname__.split('.')[0]
                if tool_name in self._class_tools_short_map:
                    raise iGymToolRegistrationException(
                        tool_name=tool_name,
                        reason=f"The session tool name `{tool_name}` is conflicted with `{self._class_tools_short_map[tool_name]}`"
                    )
                # self._classes[f.__objclass__.__name__] = f.__objclass__
                self._class_tools_short_map[tool_name] = f"{owner_class}.{tool_name}"
                tool_name = f"{owner_class}.{tool_name}"
            assert (owner_class and require_session) or (owner_class is None and not require_session)
            
            # Check for duplicates
            if tool_name in self._tools:
                raise iGymToolRegistrationException(
                    tool_name=tool_name,
                    reason="Tool with this name already registered"
                )
            
            # Validate function signature
            sig = inspect.signature(f)
            params = list(sig.parameters.values())
            
            # For session-based tools, check session parameter
            if require_session:
                if not params or params[0].name not in ['session', 'self']:
                    raise iGymToolRegistrationException(
                        tool_name=tool_name,
                        reason="First parameter must be named 'session' for session-based tools"
                    )
            
                # For class methods, skip 'self' parameter
                # if params and params[0].name == 'self':
                # params = params[1:]
            
            # Create registration info
            registration = ToolRegistration(
                name=tool_name,
                description=description or f.__doc__ or "No description provided",
                parameters=parameters,
                tool_type=tool_type,
                timeout=timeout,
                require_session=require_session,
                func=f,
                owner_class=owner_class
            )
            
            # Store the registration
            if owner_class:
                self._class_tools[tool_name] = registration
            else:
                self._tools[tool_name] = registration
            
            # Add info access to the function
            f.tool_registration = registration
            
            @wraps(f)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                result = None
                status = ToolExecutionStatus.COMPLETED
                error = None
                
                try:
                    if registration.timeout is not None:
                        with ThreadPoolExecutor(max_workers=1) as executor:
                            future = executor.submit(f, *args, **kwargs)
                            result = future.result(timeout=registration.timeout)
                    else:
                        result = f(*args, **kwargs)
                except FutureTimeoutError:
                    status = ToolExecutionStatus.TIMEOUT
                    error = f"Tool {tool_name} timed out after {registration.timeout} seconds"
                    raise iGymToolTimeoutException(tool_name=tool_name, timeout=registration.timeout)
                except Exception as e:
                    status = ToolExecutionStatus.ERROR
                    error = str(e)
                    raise iGymToolExecutionException(tool_name=tool_name, error=str(e))
                finally:
                    execution_time = time.time() - start_time
                    if status == ToolExecutionStatus.COMPLETED and result is not None and isinstance(result, ToolExecutionResult):
                        return result
                    return ToolExecutionResult(
                        status=status,
                        output=result,
                        error=error,
                        execution_time=execution_time
                    )
            
            return wrapper
        
        # Handle different invocation styles
        if func is None:
            return decorator
        elif callable(func):
            return decorator(func)
        else:
            raise iGymToolRegistrationException(
                tool_name="unknown",
                reason="Invalid registration parameters"
            )
    
    def get_tool(self, name: str) -> Optional[ToolRegistration]:
        """Get a tool registration by name"""
        if name in self._tools:
            return self._tools[name]
        if name in self._class_tools_short_map:
            name = self._class_tools_short_map[name]
        if name in self._class_tools:
            return self._class_tools[name]
        return None
    
    def get_class(self, name:str) -> Optional[object]:
        if name in self._classes:
            return self._classes[name]
        return None
    
    def list_tools(self) -> Dict[str, ToolRegistration]:
        """List all registered tools"""
        return self._tools.copy() | self._class_tools.copy()
    
    def get_tools_by_class(self, class_name: str) -> Dict[str, ToolRegistration]:
        """Get all tools owned by a specific class"""
        return {
            name: reg 
            for name, reg in self._class_tools.items() 
            if reg.owner_class == class_name
        }

