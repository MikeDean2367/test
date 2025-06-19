
from igym.memory.base import BaseMemory, MemoryItem
from typing import Dict, Optional, List, Tuple, Any
from igym.memory.type import iGymMemoryItemDuplicateUIDError

class DictMemory(BaseMemory):

    def __init__(self, uid: str):
        # uid = f"dict-{uid}"
        super().__init__(uid)

    def add(self, item: MemoryItem, key: Optional[str]=None, **kwargs) -> str:
        """Add item to dict with optional key. We enforce that the item.uid equals the provided key (if specified)."""
        if key is not None:
            item.uid = key
        uid = super().add(item, **kwargs)
        return uid

