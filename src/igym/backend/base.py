from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Union, Any
import tenacity
from functools import wraps
from igym.backend.type import (
    DecodingConfig,
    BackendInput,
    BackendOutput,
    BackendConfig
)
from igym.type.tool_call import ToolCallingItem
from igym.tool.type import ToolRegistration
import time
from collections import deque


class MetaBackend(type):
    _registry = {}

    def __new__(cls, name, bases, namespace, **kwargs):
        new_class = super().__new__(cls, name, bases, namespace)
        if name not in ('BaseBackend',):
            cls._registry[name] = new_class
        return new_class
    
    @classmethod
    def from_config(cls, config: Dict):
        raise NotImplementedError("")
        backend_type:str = config['']
        return cls._registry[backend_type](**config)

def retry_on_failure(config: BackendConfig):
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            retryer = tenacity.Retrying(
                stop=tenacity.stop_after_attempt(config.max_retries),
                wait=tenacity.wait_exponential(
                    multiplier=1,
                    max=config.retry_delay * 2
                ),
                retry=tenacity.retry_if_exception_type(Exception),
                reraise=True
            )
            return retryer(f, *args, **kwargs)
        return wrapped
    return decorator

class APIKeyManager:
    """
    主要就是这三个方案
    1. 怎么判断一个key是否可用
    2. 怎么rotate
    3. rate limit

    第一次请求的时候先去看看key是否可用？

    什么时候切换key：
    - 出现异常的时候
    - 达到qps的上限
    """

    def __init__(self, config: BackendConfig, model:str):
        self.config: BackendConfig = config
        self.available_keys:List[str] = deque(config.api_keys)
        self.model: str = model
        self.key_usage:Dict[str, Dict[str, Union[int, float]]] = {key: {'count': 0, 'last_reset': time.time()} for key in config.keys}
        self.rate_limit: Optional[int] = config.rate_limit

    def get_key(self) -> str:
        while True:
            key = self.available_keys[0]
            usage = self.key_usage[key]
            
            if time.time() - usage['last_reset'] > 60:
                usage['count'] = 0
                usage['last_reset'] = time.time()
                
            if usage['count'] < self.rate_limit:
                usage['count'] += 1
                return key
            else:
                self.available_keys.rotate(-1)
                time.sleep(0.1)  # 避免忙等待

class BaseBackend(MetaBackend):
    """
    思考一下这里应该怎么写，
    本地的tool_call -> ToolCallingItem -> message
    将registration转换成输入的格式
    """
    def __init__(self, config:BackendConfig):
        self.config: BackendConfig = config

    # 可以参考一下MLBench里面的query部分
    # 超时处理，建议使用tenacity，
    def query(self, inputs: BackendInput) -> BackendOutput:
        raise NotImplementedError()

    @classmethod
    def from_response(self, response: Any) -> BackendOutput:
        # 将query的输出打包成BackendOutput
        raise NotImplementedError()

    @classmethod
    def bkd_tool2tool_call(self, tool_calls: List[Any]) -> List[ToolCallingItem]:
        # 如果使用function calling，则调用这个会把调用的工具转换成ToolCallingItem的形式
        raise NotImplementedError()

    @classmethod
    def tool_call2bkd_tool(self, tool_calls:List[ToolCallingItem]) -> List[Dict]:
        # 如果使用function calling，调用这个会把ToolCallingItem的执行结果转换成backend输入的格式
        raise NotImplementedError()
    
    @classmethod
    def tool_registry2bkd_input(
        self, 
        tool_registry:Union[List[ToolRegistration], ToolRegistration]
    ) -> Union[Dict, str]:
        # 把function的注册信息转换成工具需要的
        raise NotImplementedError()

    