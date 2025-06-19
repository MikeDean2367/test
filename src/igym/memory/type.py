from pydantic import BaseModel
from typing import *
from enum import Enum, auto
from igym.type.exception import (
    iGymException
)

def isinstance_(object_:object, type_:Union[str, type]):
    if isinstance(type_, str):
        return object_.__class__.__name__ == type_
    else:
        return isinstance(object_, type_)

class MemoryItemModifyProtocol(Enum):
    OVERWRITE = auto()
    APPEND = auto()

class MemoryItemReadProtocol(Enum):
    BURN_AFTER_READ = auto()
    KEEP = auto()

class MemoryItemState(Enum):
    EXPIRED = auto()
    WRITING = auto()
    NORMAL = auto()


class iGymMemoryDuplicateUIDError(iGymException):
    
    def __init__(self, uid:str):
        self.uid = uid
        full_message = f"Memory UID `{self.uid}` already exists. Please use a different UID"
        super().__init__(full_message)


class iGymMemoryUnappendableError(iGymException):

    def __init__(self, content:Any, uid:str):
        self.content = content
        self.uid = uid
        full_message: str = f"Failed to modify `{uid}` content: {type(content)} does not support append operation. Please update modify protocol for UID {uid}."
        super().__init__(full_message)


class iGymMemoryItemDuplicateUIDError(iGymException):

    def __init__(self, uid:str):
        pass


class iGymMemoryNotFound(iGymException):

    def __init__(self, uid:str):
        pass

class iGymMemoryItemNotFound(iGymException):

    def __init__(self, item_uid:str, mem_uid:str, memory: Optional[object]=None):
        if isinstance_(memory, 'ListMemory'):
            raise NotImplementedError()
        elif isinstance_(memory, 'DictMemory'):
            raise NotImplementedError()
        elif isinstance_(memory, 'TreeMemory'):
            full_message: str = f"{item_uid}, {mem_uid}"
        elif isinstance_(memory, 'GraphMemory'):
            raise NotImplementedError()
        elif isinstance_(memory, 'BaseMemory'):
            raise NotImplementedError()
        else:
            raise NotImplementedError()
        super().__init__(full_message)
