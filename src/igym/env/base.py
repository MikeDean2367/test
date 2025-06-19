"""
动作空间
"""
import time
import pickle
import importlib
from pathlib import Path
from typing import Dict, Any, List, Optional, Type, Callable
from datetime import datetime
from .type import (
    EnvConfig, 
    SessionConfig,

    EnvStatus, 
    OutwardActionRecord, 

    iGymEnvException, 
    iGymEnvStateException,
    iGymEnvExecutionException, 
    iGymEnvInitializationException,
)
from igym.tool.type import (
    ToolExecutionResult,
    ToolExecutionStatus
)
from igym.tool.base import (
    # MetaSession,
    BaseSession, 
    ToolRegistry, 
    ToolRegistration,
)
from igym.type.tool_call import (
    ToolCallingItem
)
from abc import ABC, abstractmethod
import warnings
from igym.type.action import OutwardAction
from igym.type.observation import OutwardObservation

"""
一个是通过参数设置，还有一种就是直接在这里面进行配置？
这里唯一的问题就是class的初始化了，就是不知道类从哪里导入吧感觉

BaseEnv的作用主要就是注册，然后调用，当然也可以使用
tool的话就两类，一类是session based，一类是非session based
这里可以写一下action space
"""

class IEnv(ABC):

    @abstractmethod
    def init(self, *args, **kwargs):
        raise NotImplementedError()

    @abstractmethod
    def step(self, *args, **kwargs):
        raise NotImplementedError()

    @abstractmethod
    def get_observation(self, *args, **kwargs):
        raise NotImplementedError()

    @abstractmethod
    def reset(self, *args, **kwargs):
        raise NotImplementedError()

    @abstractmethod
    def close(self, *args, **kwargs):
        raise NotImplementedError()
    
    @abstractmethod
    def start(self, *args, **kwargs):
        raise NotImplementedError()

class BaseEnv(IEnv):

    def __init__(self, config: Optional[Dict[str, Any]]=None):
        self.status:EnvStatus = EnvStatus.INIT
        self._sessions: Dict[str, BaseSession] = {}
        self._tools: Dict[str, Callable] = {}
        self._action_history: List[OutwardActionRecord] = []
        self._config: EnvConfig = EnvConfig.parse_obj(config or {})
        self.init()

    def init(self):
        self.status:EnvStatus = EnvStatus.INIT
        try:
            self.init_sessions()
            self.init_tools()
        except Exception as e:
            raise iGymEnvInitializationException(
                env_name=self.__class__.__name__,
                reason=str(e)
            ) from e
        self.status = EnvStatus.RUNNING

    def init_sessions(self):
        for session_name, session_config in self._config.sessions.items():
            try:
                session_class_name:str = session_config.class_name
                session_class:object = BaseSession.get_cls(session_class_name)
                session_instance = session_class(**session_config.config)
                self._sessions[session_name] = session_instance

                # Register session tools
                self._register_session_tools(
                    session_name=session_name, 
                    session_instance=session_instance, 
                    tools=session_config.tools
                )
            except Exception as e:
                raise iGymEnvInitializationException(
                    env_name=self.__class__.__name__,
                    reason=f"Failed to initialize session `{session_name}`: {str(e)}"
                ) from e
            
    def _register_session_tools(self, session_name:str, session_instance:BaseSession, tools: List[str]):
        """Register tools from a session instance. Avoid cases where some tools are not registered"""
        if not tools:
            warnings.warn(
                f"The instance `{session_name}` of class `{session_instance.__class__.__name__}`"
                f"has no registered tools."
            )
        else:
            for tool_name in tools:
                if not hasattr(session_instance, tool_name):
                    raise iGymEnvInitializationException(
                        env_name=self.__class__.__name__,
                        reason=f"Tool `{tool_name}` not found in session `{session_name}` (class `{session_name.__class__.__name__}`)"
                    )
                attr = getattr(session_instance, tool_name)
                if not (callable(attr) and hasattr(attr, 'tool_registration')):
                    raise iGymEnvInitializationException(
                        env_name=self.__class__.__name__,
                        reason=f"Attribute '{tool_name}' in session '{session_name}' is not a registered tool"
                    )
                self._tools[f"{session_name}.{tool_name}"] = attr

    def init_tools(self):
        # Standalone tools (no session)
        for tool_name in self._config.tools:
            tool_reg: ToolRegistration = ToolRegistry().get_tool(
                name=tool_name
            )
            if tool_reg is None:
                raise iGymEnvExecutionException(
                    env_name=self.__class__.__name__,
                    reason=f"Tool `{tool_name}` not found in registry"
                )
            self._tools[tool_name] = tool_reg.func

        # Load information
        ToolRegistry().set_info(self._config.tools_info)

    def reset(self, *args, **kwargs):
        self.status = EnvStatus.INIT
        for name, sessions in self._sessions.items():
            sessions.reset()
        self.status = EnvStatus.RUNNING

    def start(self, *args, **kwargs):
        self.status = EnvStatus.INIT
        for name, sessions in self._sessions.items():
            sessions.start()
        self.status = EnvStatus.RUNNING
    
    def close(self, *args, **kwargs):
        for name, sessions in self._sessions.items():
            del sessions
        self.status = EnvStatus.CLOSED

    def _step(
        self, 
        tool_name:str, 
        parameters: Dict[str, Any],
    ) -> ToolExecutionResult:
        if tool_name not in self._tools:
            raise iGymEnvExecutionException(
                env_name=self.__class__.__name__,
                tool_name=tool_name,
                error=f"Tool `{tool_name}` is not registered."
            )

        tool_func: Callable = self._tools[tool_name]
        tool_reg: ToolRegistration = tool_func.tool_registration

        try:
            self.status = EnvStatus.RUNNING
            if tool_reg.require_session:
                session_name:str = parameters.pop('session', None)
                if session_name is None:
                    raise iGymEnvExecutionException(
                        env_name=self.__class__.__name__,
                        tool_name=tool_name,
                        error=f"The field `session` required for session-based tools"
                    )
                if session_name not in self._sessions:
                    raise iGymEnvExecutionException(
                        env_name=self.__class__.__name__,
                        tool_name=tool_name,
                        error=f"Session '{session_name}' not found"
                    )
                session:BaseSession = self._sessions[session_name]
                result:ToolExecutionResult = tool_func(session=session, **parameters)
            else:
                result:ToolExecutionResult = tool_func(**parameters)
            self.status = EnvStatus.READY
            return result
        except Exception as e:
            raise iGymEnvExecutionException(
                env_name=self.__class__.__name__,
                tool_name=tool_name,
                error=str(e)
            ) from e

    def step(self, action: OutwardAction) -> OutwardObservation:
        observation: OutwardObservation = action.create_observation(copy=False)
        tool_calls:List[ToolCallingItem] = action.tool_calls
        for i in range(len(tool_calls)):
            tool_call = tool_calls[i]
            action_record = OutwardActionRecord(
                tool_name=tool_call.name,
                parameters=tool_call.params,
                result=None,
            )
            result: ToolExecutionResult = self._step(
                tool_name=tool_call.name, parameters=tool_call.params
            )
            action_record.e_timestamp = datetime.now
            action_record.status = result.status
            self._action_history.append(action_record)
            observation.tool_calls[i].content = result
        return observation

    def get_observation(self, *args, **kwargs):
        return super().get_observation(*args, **kwargs)

