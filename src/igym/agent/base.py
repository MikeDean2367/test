
from igym.type.observation import (
    InwardObservation, 
    OutwardObservation,
    Observation, 
    ObservationList
)
from igym.type.action import (
    InwardAction, 
    OutwardAction, 
    Action,
    ActionList, 
)
from typing import *
from pydantic import BaseModel, Field
from igym.backend.base import BackendConfig, BackendInput, BackendOutput
from .type import AgentConfig

"""
基于这个会派生出
tool-(free/fix) agent
tool-call agent
tool-prompt agent

这几个主要的不同就是__parse_output__和__parse_input__的不同
对于tool-prompt需要手动改的解析和输入
对于tool-free/fix，则只需要在__parse_output__那边写就行
"""

class BaseAgent:

    """
    Examples:
        >>> agent = BaseAgent(config)
        >>> agent.observe(obs1)
        >>> agent.observe(obs2)
        >>> action = agent.act()
    """

    def __init__(self, config: AgentConfig):
        self.config: AgentConfig = config
        self._init_backend(config.backend_config)
        self._init_memory(config.memory_config)

        self._observations:List[Observation] = list()

    def _init_memory(self, config):
        pass

    def _init_backend(self, config: BackendConfig):
        pass

    def observe(self, observation:Union[Observation, List[Observation]]) -> None:
        if isinstance(observation, Observation):
            self._observations.append(observation)
        elif isinstance(observation, list):
            self._observations.extend(observation)
        elif observation is None:
            pass
        else:
            raise 

    def __parse_input__(self, obs: List[Observation]) -> BackendInput:
        pass

    def __think__(self, b_in:BackendInput) -> BackendOutput:
        pass

    def __parse_output__(
        self, 
        b_out:BackendOutput
    ) -> Optional[Union[InwardAction, OutwardAction, List[Union[InwardAction, OutwardAction]]]]:
        pass

    def act(self, observation=None) -> Action:
        self.observe(observation=observation)
        b_in:BackendInput = self.__parse_input__(self._observations)
        b_out: BackendOutput = self.__think__(b_in)
        actions: Optional[Union[InwardAction, OutwardAction, List[Union[InwardAction, OutwardAction]]]] = self.__parse_output__(b_out)
        self._observations.clear()
        return actions

    def save(self) -> Dict[str, Any]:
        pass

    @classmethod
    def load(cls, data: Dict[str, Any]):
        pass
