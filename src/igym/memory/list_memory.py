
from igym.memory.base import BaseMemory, MemoryItem
from typing import Dict, Optional, List, Tuple, Any, Union
from igym.memory.type import iGymMemoryItemNotFound

class ListMemory(BaseMemory):

    def __init__(self, uid: str):
        # uid = f"list-{uid}"
        super().__init__(uid)
        self.item_list: List[str] = []  # Stores UIDs in order

    def __getitem__(self, uid: Union[str, int]) -> MemoryItem:
        if isinstance(uid, int):
            uid:str = self.item_list[uid]
        if not isinstance(uid, str):
            raise TypeError(
                f"{self.__class__.__name__} index must be int or str, " 
                f"got {type(uid).__name__} (value: {uid!r})"
            )
        return self.read(identifier=uid, reader=self.uid, return_meta=True, return_none_if_error=True)
    
    def add(self, item: MemoryItem, index: Optional[int]=None, **kwargs) -> str:
        """Add item to list, optionally at specific index"""
        uid:str = super().add(item, **kwargs)
        if index is None:
            self.item_list.append(uid)
        else:
            self.item_list.insert(index, uid)
        return uid
    
    def request_link(
        self, 
        target_mem_uid: str, 
        target_item_uid: str, 
        source_item_uid: Optional[str] = None,
        index: Optional[int]=None
    ) -> int:
        uid:str = super().request_link(target_mem_uid, target_item_uid, source_item_uid)
        if index is None:
            index = len(self.item_list)
            self.item_list.append(uid)
        else:
            self.item_list.insert(index, uid)
        return index
    
    def revoke_link(self, identifier: str):
        if identifier in self.item_list:
            super().revoke_link(identifier)
            self.item_list.remove(identifier)

    def delete(
        self, 
        identifier: Union[str, int],
        recursive: bool=False,
        return_false_if_error:bool=True,
        **kwargs
    ) -> bool:
        # check the index and uid based on identifier
        if isinstance(identifier, int):
            index:int = identifier
            if len(self.item_list) <= index or index < 0:
                if return_false_if_error:
                    return False
                else:
                    raise iGymMemoryItemNotFound(item_uid=index, mem_uid=self.uid, memory=self)
            identifier:str = self.item_list[index]
        elif isinstance(identifier, str):
            if identifier in index:
                if return_false_if_error:
                    return False
                else:
                    raise iGymMemoryItemNotFound(item_uid=identifier, mem_uid=self.uid, memory=self)
            index:int = self.item_list.index(identifier)
            identifier:str = identifier
        else:
            raise TypeError(
                f"{self.__class__.__name__} index must be int or str, " 
                f"got {type(identifier).__name__} (value: {identifier!r})"
            )
        
        # delete base memory and current
        state:bool = super().delete(identifier=identifier, recursive=recursive, return_false_if_error=return_false_if_error, **kwargs)
        if state:
            self.item_list.remove(identifier)
        return state

    def retrieve(self, **kwargs) -> List[Any]:
        results:List[Any] = list()
        for uid in self.item_list:
            results.append(self.read(uid))
        return results

    def reset(self):
        super().reset()
        self.item_list.clear()

    def save(self) -> Dict[str, Any]:
        """Serialize"""
        data: Dict = super().save()  # Get BaseMemory's saved data
        data["item_list"] = self.item_list  # Add item_list to the saved data
        return data
    
    @classmethod
    def load(cls, data: Dict[str, Any]):
        """Deserialize"""
        memory = super().load(data)  # Load BaseMemory's data
        memory.item_list = data.get("item_list", [])  # Restore item_list
        return memory
    
