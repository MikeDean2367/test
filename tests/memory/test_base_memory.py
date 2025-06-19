import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))


import unittest
from igym.memory.base import BaseMemory, MemoryItem, MemorySystem
from igym.memory.type import (
    MemoryItemState,
    iGymMemoryItemNotFound,
    iGymMemoryItemDuplicateUIDError,
    iGymMemoryNotFound
)

class TestBaseMemory(unittest.TestCase):
    def setUp(self):
        MemorySystem.reset()
        self.memory = BaseMemory("test_memory")
        self.item = MemoryItem(content="test content", source="test")
        self.item_uid = self.memory.add(self.item)

    def test_add_and_read(self):
        self.setUp()
        # Test basic add and read
        content = self.memory.read(self.item_uid)
        print("mike:", content)
        self.assertEqual(content, "test content")
        
        # Test read with return_meta
        item = self.memory.read(self.item_uid, return_meta=True)
        self.assertEqual(item.content, "test content")
        self.assertEqual(item.source, "test")

    def test_modify(self):
        self.setUp()
        # Test modify
        self.memory.modify(self.item_uid, "modified content")
        self.assertEqual(
            self.memory.read(self.item_uid),
            "modified content"
        )

    def test_delete(self):
        self.setUp()
        # Test delete
        self.assertTrue(self.memory.delete(self.item_uid))
        self.assertIsNone(
            self.memory.read(self.item_uid, return_none_if_error=True)
        )

    def test_duplicate_uid(self):
        self.setUp()
        # Test adding duplicate UID
        with self.assertRaises(iGymMemoryItemDuplicateUIDError):
            self.memory.add(self.item)

    def test_nonexistent_item(self):
        self.setUp()
        # Test reading non-existent item
        with self.assertRaises(iGymMemoryItemNotFound):
            self.memory.read("nonexistent", return_none_if_error=False)

    def test_retrieve(self):
        self.setUp()
        # Add multiple items
        items = [
            MemoryItem(content=f"item{i}", source="test")
            for i in range(3)
        ]
        for item in items:
            self.memory.add(item)
        
        # Test retrieve
        contents = self.memory.retrieve()
        self.assertEqual(len(contents), 4)  # original + 3 new
        self.assertIn("test content", contents)
        self.assertIn("item0", contents)
        self.assertIn("item2", contents)

    def test_reset(self):
        self.setUp()
        # Add some items
        for i in range(3):
            self.memory.add(MemoryItem(content=f"item{i}", source="test"))
        
        # Test reset
        self.memory.reset()
        self.assertEqual(len(self.memory.items), 0)
        self.assertEqual(len(self.memory._links), 0)

class TestMemoryLinking(unittest.TestCase):
    def setUp(self):
        MemorySystem.reset()
        self.mem1 = BaseMemory("mem1")
        self.mem2 = BaseMemory("mem2")
        
        # Add item to mem1
        self.item = MemoryItem(content="shared", source="test")
        self.item_uid = self.mem1.add(self.item)
        
        # Create link in mem2
        self.mem2.request_link("mem1", self.item_uid, "linked_item")

    def test_linking(self):
        self.setUp()
        # Test reading through link
        self.assertEqual(self.mem2.read("linked_item"), "shared")
        
        # Test modifying through link
        self.assertTrue(
            self.mem2.modify("linked_item", "modified", recursive=True)
        )
        self.assertEqual(self.mem1.read(self.item_uid), "modified")

    def test_revoke_link(self):
        self.setUp()
        # Test revoking link
        self.mem2.revoke_link("linked_item")
        self.assertIsNone(
            self.mem2.read("linked_item", return_none_if_error=True)
        )

    def test_invalid_link(self):
        self.setUp()
        # Test invalid link request
        with self.assertRaises(iGymMemoryNotFound):
            self.mem2.request_link("nonexistent_mem", "nonexistent_item")

    def test_delete_with_links(self):
        self.setUp()
        # Test deleting an item with links
        # Create another memory with link
        mem3 = BaseMemory("mem3")
        mem3.request_link("mem1", self.item_uid, "another_link")
        
        # Delete from source
        self.assertTrue(self.mem1.delete(self.item_uid))
        
        # Verify links are broken
        self.assertIsNone(
            self.mem2.read("linked_item", return_none_if_error=True)
        )
        self.assertIsNone(
            mem3.read("another_link", return_none_if_error=True)
        )

class TestMemorySerialization(unittest.TestCase):
    def test_serialization(self):
        MemorySystem.reset()
        memory = BaseMemory("serial_test")
        item = MemoryItem(content="test", source="test")
        uid = memory.add(item)
        
        # Test save
        data = memory.save()
        self.assertEqual(data["uid"], "serial_test")
        self.assertIn(uid, data["items"])
        self.assertEqual(data["items"][uid]["content"], "test")
        
        # Test load
        MemorySystem.reset()
        new_memory = BaseMemory.load(data)
        self.assertEqual(new_memory.uid, "serial_test")
        self.assertEqual(new_memory.read(uid), "test")

if __name__ == '__main__':
    unittest.main()