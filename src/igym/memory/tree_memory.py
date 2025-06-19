from igym.memory.base import BaseMemory, MemoryItem
from typing import Dict, Optional, List, Tuple, Any, Union
from igym.memory.type import iGymMemoryItemNotFound
from pydantic import Field
from collections import deque 
from copy import deepcopy

"""
TODO:
    1. 过时的咋办
    2. 想要修改孩子节点咋办
"""

class TreeMemoryItem(MemoryItem):
    depth: Optional[int] = 0
    parent_uid: Optional[str] = None
    children_uids: List[str] = Field(default_factory=list)

    def remove_child(self, child:Optional['TreeMemoryItem']=None, child_uid: Optional[str]=None):
        if child:
            if child.uid in self.children_uids:
                self.children_uids.remove(child.uid)
        elif child_uid:
            if child_uid in self.children_uids:
                self.children_uids.remove(child_uid)
    
    def add_child(self, child:'TreeMemoryItem', recursive_depth:bool=False, all_items:Optional[Dict[str, 'TreeMemoryItem']]=None):
        # TODO: 这里需要检查一下
        """if `recursive_depth` is true, we will travel his child and change the depth"""
        child.parent_uid = self.uid
        child.depth = self.depth + 1
        if child.uid not in self.children_uids:
            self.children_uids.append(child.uid)
        if recursive_depth:
            assert all_items
            for child_child_uid in child.children_uids:
                child_child: TreeMemoryItem = all_items[child_child_uid]
                child.add_child(child_child)

    def become_root(self, recursive_depth:bool=False, all_items:Optional[Dict[str, 'TreeMemoryItem']]=None) -> str:
        self.parent_uid = None
        self.depth = 0
        if recursive_depth:
            assert all_items
            for child_uid in self.children_uids:
                child:'TreeMemoryItem' = all_items[child_uid]
                self.add_child(child, recursive_depth=recursive_depth, all_items=all_items)
        return self.uid

    @property
    def is_root(self) -> bool:
        return self.parent_uid is None

    @property
    def is_leaf(self) -> bool:
        return len(self.children_uids) == 0

class TreeMemory(BaseMemory):
    # 后续可以加入环的检测来防止其变成图

    def __init__(self, uid:str):
        # uid = f"tree-{uid}"
        super().__init__(uid)
        self.root_uids: List[str] = list()
    
    # 新加入节点，可以设置父亲节点
    def add(
        self, 
        item: Union[MemoryItem, TreeMemoryItem],
        parent_uid: Optional[str]=None,
        **kwargs
    ) -> str:
        if not isinstance(item, TreeMemoryItem):
            # Convert MemoryItem to TreeMemoryItem if needed
            tree_item = TreeMemoryItem(**item.dict())
        else:
            tree_item = item
        
        tree_item.parent_uid = parent_uid
        uid:str = super().add(tree_item, **kwargs)

        if parent_uid is None:
            tree_item.depth = 0
            self.root_uids.append(uid)
            for child_uid in tree_item.children_uids:
                child: TreeMemoryItem = self.items[child_uid]
                tree_item.add_child(child=child, recursive_depth=True, all_items=self.items)
        else:
            if parent_uid not in self.items:
                raise iGymMemoryItemNotFound(item_uid=parent_uid, mem_uid=self.uid, memory=self)
            parent:TreeMemoryItem = self.items[parent_uid]
            assert isinstance(parent, TreeMemoryItem)
            parent.add_child(tree_item, recursive_depth=True, all_items=self.items)
            # parent.children_uids.append(uid)
            # tree_item.depth = parent.depth + 1
        
        return uid
    
    def traverse(
        self,
        uid: str,
        order: str = "pre",
        func: Optional[callable] = None,
        return_meta: bool=False
    ) -> Union[List[Any], List[TreeMemoryItem], List[List[TreeMemoryItem]], List[List[Any]]]:
        __SUPPORT_ORDER__ = ["pre", "post", "layer"]
        order = order.lower()
        assert order in __SUPPORT_ORDER__, \
            f"The order `{order}` is invalid. We only support the {', '.join(['`' + _ + '`' for _ in __SUPPORT_ORDER__])}."
        
        results: List[Any] = list()

        def recursive_traverse(current_uid:str, order: str):
            if current_uid not in self.items:
                return
            
            current: TreeMemoryItem = self.items[current_uid]

            if func:
                func(current=current, parent=None if current.parent_uid is None else self.items[current.parent_uid])

            if order == 'pre':
                results.append(current.content if not return_meta else current)

            for uid in current.children_uids:
                recursive_traverse(uid, order=order)
            
            if order == 'post':
                results.append(current.content if not return_meta else current)
        
        def layer_traverse(current_uid:str):
            """Return Union[
                List[List[TreeMemoryItem]],
                List[List[Any]]
            ]"""
            if current_uid not in self.items:
                return
            
            queue = deque([current_uid])

            while queue:
                level_size:int = len(queue)
                current_level:List = list()
                
                for _ in range(level_size):
                    current_uid = queue.popleft()
                    current: TreeMemoryItem = self.items[current_uid]
                    current_level.append(current.content if not return_meta else current)
                    queue.extend(current.children_uids)
                    if func:
                        func(current=current, parent=None if current.parent_uid is None else self.items[current.parent_uid])
                results.append(current_level)

        if order == 'layer':
            layer_traverse(current_uid=uid)
        else:
            recursive_traverse(current_uid=uid, order=order)
        return results

    def delete(
        self,
        identifier: str,
        with_children: bool=False,
        return_false_if_error:bool=False,
        **kwargs,
    ) -> bool:
        """Delete item from tree, optionally with children"""
        # Check if the identifier exists
        if identifier not in self.items:
            if return_false_if_error:
                return False
            else:
                raise iGymMemoryItemNotFound(item_uid=identifier, mem_uid=self.uid, memory=self)

        item: TreeMemoryItem = self.items[identifier]
        parent: TreeMemoryItem = None if item.parent_uid is None else self.items[item.parent_uid]
        if with_children:
            # Delete the children
            pre_state = True
            children_uids: List[str] = deepcopy(item.children_uids)
            for child_uid in children_uids:
                state:bool = self.delete(child_uid, with_children=True, return_false_if_error=return_false_if_error, **kwargs)
                
                pre_state = state and pre_state
            if pre_state:
                pre_state = pre_state and super().delete(identifier=identifier, return_false_if_error=return_false_if_error, **kwargs)
                if pre_state:
                    if parent:
                        parent.remove_child(child_uid=item.uid)
                    else:
                        self.root_uids.remove(identifier)
            return pre_state
        else:
            # make the children's parent to their grandparent
            # 如果待删除的是根节点，则所有的儿子节点都变成根节点，然后修改depth
            # 如果不是，则修改父亲节点，然后修改depth
            child_uids: List[str] = deepcopy(item.children_uids)
            success:bool = super().delete(identifier=identifier, return_false_if_error=return_false_if_error, **kwargs)
            if not success:
                return success
            if parent:
                parent.remove_child(child_uid=identifier)
            else:
                if identifier in self.root_uids:
                    self.root_uids.remove(identifier)
            for child_uid in child_uids:
                child:TreeMemoryItem = self.items[child_uid]
                if parent:
                    parent.add_child(child, recursive_depth=True, all_items=self.items)
                else:
                    # make the child node the parent
                    self.root_uids.append(child_uid)
                    child.become_root(recursive_depth=True, all_items=self.items)
            child_uids.clear()
            return success

    def save(self) -> Dict[str, Any]:
        """Serialize"""
        data: Dict = super().save()  # Get BaseMemory's saved data
        data["root_uids"] = self.root_uids
        return data

    @classmethod
    def load(cls, data: Dict[str, Any]):
        """Deserialize"""
        memory = super().load(data, item_class=TreeMemoryItem)  # Load BaseMemory's data
        memory.root_uids = data.get("root_uids", [])  # Restore root_uids
        return memory

    def get_children(
        self, 
        uid:str, 
        return_meta:bool=False
    ) -> Optional[Union[List[Any], List[TreeMemoryItem]]]:
        if uid not in self.items:
            return
        parent:TreeMemoryItem = self.items[uid]
        results:List = list()
        for child_uid in parent.children_uids:
            children:TreeMemoryItem = self.items[child_uid]
            results.append(children if return_meta else children.content)
        return results

    def get_parent(
        self,
        uid:str,
        return_meta:bool=False
    ) -> Optional[Union[Any, TreeMemoryItem]]:
        if uid not in self.items:
            return
        item:TreeMemoryItem = self.items[uid]
        if item.parent_uid:
            return self.items[item.parent_uid] if return_meta else self.items[item.parent_uid].content
        return None
