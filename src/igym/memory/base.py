from datetime import datetime, timedelta
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Union, Tuple
from uuid import uuid4
from pydantic import BaseModel, Field, field_validator, ConfigDict, field_serializer
from collections import defaultdict
from abc import ABC, abstractmethod
import warnings

from igym.memory.type import (
    MemoryItemState,
    MemoryItemReadProtocol,
    MemoryItemModifyProtocol,
    iGymMemoryDuplicateUIDError,
    iGymMemoryUnappendableError,
    iGymMemoryItemDuplicateUIDError,
    iGymMemoryNotFound,
    iGymMemoryItemNotFound
)
from igym.util.base import parse_duration

class MemoryItem(BaseModel):
    uid: str = Field(default_factory=lambda: str(uuid4()))
    content: Any
    source: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now())
    m_protocol: MemoryItemModifyProtocol = MemoryItemModifyProtocol.OVERWRITE
    r_protocol: MemoryItemReadProtocol = MemoryItemReadProtocol.KEEP
    bind_func: Optional[str] = None
    bind_args: Dict[str, Any] = Field(default_factory=dict)
    others: Dict[str, Any] = Field(default_factory=dict)
    state: MemoryItemState = MemoryItemState.NORMAL

    duration: Optional[str] = None  # e.g. "1d20h30m15s"
    end_time: Optional[datetime] = None  # e.g. "2090/04/12 00:00"

    # Metadata
    read_count: int = 0
    last_access_time: Optional[datetime] = None
    last_modify_time: Optional[datetime] = None
    last_reader: Optional[str] = None
    last_modifier: Optional[str] = None
    history: List[Dict[str, Any]] = Field(default_factory=list)

    # Pydantic
    model_config = ConfigDict(
        arbitrary_types_allowed=True,  # 允许任意类型
        json_encoders={
            datetime: lambda v: v.isoformat(),
            Enum: lambda v: v.name,
            timedelta: lambda v: str(v),
        }
    )

    # class Config:
    #     arbitrary_types_allowed = True
    #     json_encoders = {
    #         datetime: lambda v: v.isoformat(),
    #         Enum: lambda v: v.name,
    #         timedelta: lambda v: str(v)
    #     }

    @field_validator('duration')
    @classmethod
    def validate_duration(cls, v):
        if v is None:
            return None
        try:
            parse_duration(v)
            return v
        except ValueError as e:
            raise ValueError(f"Invalid duration format: {v}. Expected format like '1d2h30m15s'")
    
    @field_validator('end_time', mode='before')
    @classmethod
    def parse_end_time(cls, v):
        if v is None:
            return None
        if isinstance(v, str):
            try:
                return datetime.strptime(v, "%Y/%m/%d %H:%M")
            except ValueError:
                try:
                    return datetime.fromisoformat(v)
                except ValueError:
                    raise ValueError("end_time must be in format 'YYYY/MM/DD HH:MM' or ISO format")
        return v
    
    def _validate_expiration(self):
        """Validate expiration settings and choose the most restrictive one"""
        if self.duration is not None and self.end_time is not None:
            warnings.warn(
                "Both duration and end_time are set. Using the most restrictive expiration.",
                UserWarning
            )
            
            duration_delta = parse_duration(self.duration)
            calculated_end = (self.timestamp or datetime.now()) + duration_delta
            
            # Use whichever comes first
            if calculated_end < self.end_time:
                self.end_time = None
            else:
                self.duration = None
    
    def model_post_init(self, __context) -> None:
        self._validate_expiration()
        self.update_history("init")

    def get_expiration_time(self) -> Optional[datetime]:
        """Calculate the expiration time based on duration or end_time"""
        if self.duration:
            duration_delta = parse_duration(self.duration)
            return (self.timestamp or datetime.now()) + duration_delta
        return self.end_time

    def is_expired(self) -> bool:
        """Check if the item has expired"""
        expiration_time = self.get_expiration_time()
        if expiration_time is None:
            return False
        return datetime.now() > expiration_time

    def update_history(
        self, 
        action:str, 
        accessed_via: Optional[Tuple[str, str]]=None, 
        **kwargs
    ):
        """update item history with an action"""
        entry = {
            "timestamp": datetime.now(),
            "action": action,
            "state": self.state,
            "content": self.content,
            **kwargs
        }
        if accessed_via:
            entry["accessed_via"] = f"{accessed_via[0]}->{accessed_via[1]}"
        self.history.append(entry) 

    def read(
        self, 
        return_meta:bool=False, 
        reader:Optional[str]=None, 
        accessed_via: Optional[Tuple[str, str]]=None
    ) -> Union[MemoryItemState, str, Any]:
        """Read the item content with protocol handling"""
        # check if the current item is valid
        if self.state != MemoryItemState.NORMAL:
            return self.state
        if self.is_expired():
            self.state = MemoryItemState.EXPIRED
            return self.state

        self.read_count += 1
        self.last_access_time = datetime.now()
        self.last_reader = reader

        if self.r_protocol == MemoryItemReadProtocol.BURN_AFTER_READ:
            self.state = MemoryItemState.EXPIRED
        
        self.update_history("read", accessed_via, reader=reader)
        if return_meta:
            return self
        else:
            return self.content
    
    def modify(
        self,
        new_content: Any,
        modifier: Optional[str]=None,
        protocol: Optional[MemoryItemModifyProtocol]=None,
        accessed_via: Optional[Tuple[str, str]]=None
    ) -> Union[bool, MemoryItemState]:
        """Modify the item content with protocol handling"""
        # check if the current item is valid
        if self.state != MemoryItemState.NORMAL:
            return self.state
        if self.is_expired():
            self.state = MemoryItemState.EXPIRED
            return self.state
    
        protocol: MemoryItemModifyProtocol = protocol or self.m_protocol

        if protocol == MemoryItemModifyProtocol.APPEND:
            if not hasattr(self.content, 'append'):
                raise iGymMemoryUnappendableError(self.content, self.uid)
            self.content.append(new_content)
        elif protocol == MemoryItemModifyProtocol.OVERWRITE:
            self.content = new_content
        else:
            raise NotImplementedError(f"Invalid MemoryItemModifyProtocol: `{protocol}`.")
        
        self.last_modify_time = datetime.now()
        self.last_modifier = modifier
        self.update_history("modify", accessed_via, modifier=modifier, new_content=new_content)
        return True
    
    def is_accessible(self) -> bool:
        """Check if item is accessible (not expired or being written)"""
        return self.state == MemoryItemState.NORMAL and not self.is_expired()

class MemorySystem:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._memories = dict()
        return cls._instance
    
    def register_memory(self, memory):
        if memory.uid in self._memories:
            if memory == self.get_memory(memory.uid):
                return
            raise iGymMemoryDuplicateUIDError(memory.uid)
        self._memories[memory.uid] = memory

    def unregister_memory(self, memory):
        if memory.uid in self._memories:
            self._memories.pop(memory.uid)
        
    def get_memory(self, uid):
        if uid not in self._memories:
            raise iGymMemoryNotFound(uid)
        return self._memories.get(uid)
    
    @classmethod
    def reset(cls):
        if cls._instance:
            cls._instance._memories.clear()
            del cls._instance
            cls._instance = None

class IMemory(ABC):

    @abstractmethod
    def add(self, *args, **kwargs):
        raise NotImplementedError()
    
    @abstractmethod
    def read(self, *args, **kwargs):
        raise NotImplementedError()
    
    @abstractmethod
    def modify(self, *args, **kwargs):
        raise NotImplementedError()
    
    @abstractmethod
    def delete(self, *args, **kwargs):
        raise NotImplementedError()
    
    @abstractmethod
    def delete(self, *args, **kwargs):
        raise NotImplementedError()
    
    @abstractmethod
    def retrieve(self, *args, **kwargs):
        raise NotImplementedError()
    
    @abstractmethod
    def reset(self, *args, **kwargs):
        raise NotImplementedError()

class BaseMemory(IMemory):

    def __init__(self, uid:str):
        self.uid:str = uid
        self.items: Dict[str, MemoryItem] = dict()
        self._links: Dict[str, Tuple[str, str]] = dict()    # {local_key: (target_memory_uid, target_key)}
        self._reverse_links: Dict[str, List[Tuple[str, str]]] = defaultdict(list)  # {target_memory_uid: [(local_key, target_key)]}
        MemorySystem().register_memory(self)

    def __contains__(self, uid: str):
        return uid in self.items or uid in self._links
    
    def __getitem__(self, uid:str) -> MemoryItem:
        return self.read(
            identifier=uid, 
            reader=self.uid,
            return_none_if_error=True, 
            return_meta=True
        )

    def __len__(self) -> int:
        return len(self.items) + len(self._links)
    
    def _resolve_link(
        self,
        identifier: Union[str, Any]
    ) -> Tuple[Optional['BaseMemory'], Optional[Union[str, Any]], Optional[Tuple[str, str]]]:
        """Resolve a link if the identifier refers to one"""
        # Check if is a direct link key
        if identifier in self._links:
            # If current memory hold the link
            # we need find the owner memory, and then return 
            # the owner memory, the uid of owner memory, (current memory uid, current item uid)
            # self[identifier] <=> target_memory[target_item_uid]
            target_memory_uid, target_item_uid = self._links[identifier]
            target_memory: 'BaseMemory' = MemorySystem().get_memory(target_memory_uid)
            return target_memory, target_item_uid, (self.uid, identifier)

        return None, None, None

    def add(self, item: MemoryItem, **kwargs) -> str:
        """Add a new item to memory"""
        if item.uid in self.items:
            raise iGymMemoryItemDuplicateUIDError(item.uid)
        
        item.state = MemoryItemState.WRITING
        self.items[item.uid] = item
        item.state = MemoryItemState.NORMAL
        item.update_history("added")
        return item.uid
    
    # 向其他人请求
    def request_link(
        self, 
        target_mem_uid: str, 
        target_item_uid:str, 
        source_item_uid:Optional[str]=None
    ) -> str:
        """Request a link to another memory's item
        
        Args:TODO
            target_mem_uid (str):
            target_item_uid (str):
            source_item_uid (Optional[str]):

        Returns:
            source item uid (str)   

        Raise:
            iGymMemoryNotFound
            iGymMemoryItemNotFound
        """
        if target_mem_uid == self.uid:
            return
        # source_uid will be equal to target_uid if source_uid is not set
        if source_item_uid is None:
            source_item_uid = target_item_uid
        # check the source_uid is not in self.items
        if source_item_uid in self.items:
            raise iGymMemoryItemDuplicateUIDError(source_item_uid)
        # find the owner item
        target_memory: 'BaseMemory' = MemorySystem().get_memory(target_mem_uid)
        while True:
            if target_item_uid in target_memory.items:
                break
            elif target_item_uid in target_memory._links:
                target_memory, target_item_uid, _ = target_memory._resolve_link(identifier=target_item_uid)
            else:
                raise iGymMemoryItemNotFound(item_uid=target_item_uid, mem_uid=target_mem_uid)
        # update
        self._links[source_item_uid] = (target_mem_uid, target_item_uid)
        if self.uid not in target_memory._reverse_links:
            target_memory._reverse_links[self.uid] = list()
        target_memory._reverse_links[self.uid].append((source_item_uid, target_item_uid))

    # 主动删除对别人的申请
    # 首先删除自己的
    # 然后删除授权者那边对自己的记录
    def revoke_link(
        self,
        identifier: str
    ):
        if identifier in self._links:
            target_mem_uid, target_item_uid = self._links[identifier]
            del self._links[identifier]

            target_memory: 'BaseMemory' = MemorySystem().get_memory(target_mem_uid)
            if target_memory:
                target_memory._reverse_links[self.uid] = [
                    (su, tu) for su, tu in target_memory._reverse_links[self.uid]
                    if su != identifier
                ]
    
    # 如果这个对应的是link，则直接删除link，而不删除指向的值
    # 如果这个对应的是非link，则除了删除自己，还要删除所有授权的人
    def delete(
        self, 
        identifier: str, 
        recursive: bool=False,
        return_false_if_error:bool=True, 
        **kwargs
    ) -> bool:
        """delete an item, handling links appropriately
        
        Args:
            identifier (str):
            recursive (bool): if the value corresponding to identifier is link, we will delete the owner when recursive set to True
        """
        # First check if this is a linked item
        if recursive:
            target_memory, target_item_uid, _ = self._resolve_link(identifier)
            if target_memory is not None:
                return target_memory.delete(target_item_uid, recursive, return_false_if_error, **kwargs)
        else:
            if identifier in self._links:
                self.revoke_link(identifier=identifier)
                return True
        
        # Handle local item deletion
        if identifier in self.items:
            # Remove all links pointing to this item
            for mem_uid in list(self._reverse_links.keys()):
                memory: 'BaseMemory' = MemorySystem().get_memory(mem_uid)
                if memory:
                    keys_to_remove = [
                        k for k, v in memory._links.items() 
                        if v == (self.uid, identifier)
                    ]
                    for k in keys_to_remove:
                        del memory._links[k]

            # Then delete the actual item
            item = self.items[identifier]
            item.state = MemoryItemState.EXPIRED
            item.update_history("deleted")
            del self.items[identifier]
            return True
        
        if return_false_if_error:
            return False
        else:
            raise iGymMemoryItemNotFound(item_uid=identifier, mem_uid=self.uid)

    def read(
        self, 
        identifier: Union[str, Any], 
        reader: Optional[str]=None, 
        return_meta:bool=False,
        return_none_if_error:bool=True,
        **kwargs
    ) -> Optional[Union[Any, MemoryItemState, MemoryItem]]:
        """Read an items'content, following links if necessary
        
        Args:
            identifier (str): 
            reader (Optional[str]): 
            return_meta (bool):
            return_none_if_error (bool): 
        
        Returns:
            Optional[Union[Any, MemoryItemState, MemoryItem]]:
                - if `return_meta` is True: 
                    return MemoryItem
                - if `return_meta` is False: 
                    return Any
                - if `return_none_if_error` is True: 
                    return None if the identifier is not existed or the current state is unreadable.
                - if `return_none_if_error` is False:
                    raise Error if the identifier is not existed
                    return MemoryItemState if the current state is unreadale.

        Raises:
            iGymMemoryItemNotFound: if the identifier is not existed.
        
        Examples:TODO
            >>> self
            results
            >>> self.read(123)
            results
        """
        target_memory, target_item_uid, accessed_via = self._resolve_link(identifier)
        if target_memory is not None:
            return target_memory.read(
                identifier=target_item_uid,
                reader=reader,
                accessed_via=accessed_via,
                **kwargs
            )
        
        if isinstance(identifier, str) and identifier in self.items:
            # the identifier is existed.
            item:MemoryItem = self.items[identifier]
            if not item.is_accessible():
                if return_none_if_error:
                    return None
                return item.state

            return item.read(return_meta=return_meta, reader=reader, **kwargs)
        
        # the identifier is not existed
        if return_none_if_error:
            return None
        else:
            raise iGymMemoryItemNotFound(item_uid=identifier, mem_uid=self.uid)

    def modify(
        self,
        identifier: str,
        new_content: Any,
        recursive: bool=False,
        modifier: Optional[str]=None,
        return_false_if_error:bool=True,
        **kwargs,
    ) -> bool:
        """Modify an item's content
        
        Args:
            identifier (str):
            new_content (Any):
            recursive (bool):
            modifier (Optional[str]):
        
        Returns:
            pass
            
        Raises:
            iGymMemoryItemNotFound
        """
        if modifier is None:
            modifier = self.uid
        if recursive:
            target_memory, target_item_uid, accessed_via = self._resolve_link(identifier=identifier)
            if target_memory:
                return target_memory.modify(target_item_uid, new_content, recursive, self.uid, return_false_if_error, **kwargs)

        if identifier in self._links:
            return False
        if identifier in self.items:
            item: MemoryItem = self.items[identifier]
            if not item.is_accessible():
                if return_false_if_error:
                    return False
                return item.state
            
            item.modify(new_content, modifier, **kwargs)
            return True
        if return_false_if_error:
            return False
        raise iGymMemoryItemNotFound(item_uid=identifier, mem_uid=self.uid)
            
    def retrieve(
        self, 
        **kwargs
    ) -> List[Any]:
        """Retrieve items based on criteria. Here we return all items"""
        results: List[Any] = list()
        for uid in self.items:
            # results.append(self.items[uid].content)
            results.append(self.read(uid))
        for uid in self._links:
            results.append(self.read(uid))
        return results
    
    def reset(self):
        for uid in list(self.items.keys()):
            self.delete(uid, recursive=True, return_false_if_error=True)
        for uid in list(self._links.keys()):
            self.revoke_link(uid)
        assert len(self.items) == 0 and len(self._links) == 0

    def save(self) -> Dict[str, Any]:
        """Serialize memory to a dictionary"""
        return {
            "uid": self.uid,
            "items": {k: v.dict() for k, v in self.items.items()},
            "links": self._links,
            "type": self.__class__.__name__
        }
    
    @classmethod
    def load(cls, data: Dict[str, Any], item_class:Optional[type]=MemoryItem):
        """Deserialize memory from a dictionary"""
        memory = cls(data.get("uid"))

        for k, item_data in data.get("items", {}).items():
            memory.items[k] = item_class(**item_data)
        
        memory._links = data.get("links", {})
        return memory
    
    def update(self, identifier:str):
        pass
