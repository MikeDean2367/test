import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

import unittest
from datetime import datetime, timedelta
import time
from igym.memory.base import MemoryItem
from igym.memory.type import (
    MemoryItemState,
    MemoryItemReadProtocol,
    MemoryItemModifyProtocol,
    iGymMemoryUnappendableError
)

class TestMemoryItem(unittest.TestCase):
    def setUp(self):
        self.default_item = MemoryItem(
            content="test content", 
            source="test_source"
        )
        self.timestamp = datetime.now()
        self.timed_item = MemoryItem(
            content="timed content",
            source="test_source",
            timestamp=self.timestamp
        )

    def test_initialization(self):
        self.assertIsInstance(self.default_item.uid, str)
        self.assertEqual(self.default_item.content, "test content")
        self.assertEqual(self.default_item.source, "test_source")
        self.assertEqual(self.default_item.state, MemoryItemState.NORMAL)
        self.assertEqual(self.default_item.read_count, 0)
        self.assertEqual(len(self.default_item.history), 1)  # Initial creation

    def test_duration_expiration(self):
        item = MemoryItem(
            content="test",
            source="test",
            duration="1s"
        )
        self.assertFalse(item.is_expired())
        time.sleep(1)
        self.assertTrue(item.is_expired())

    def test_end_time_expiration(self):
        future = datetime.now() + timedelta(seconds=1)
        item = MemoryItem(
            content="test",
            source="test",
            end_time=future
        )
        self.assertFalse(item.is_expired())
        time.sleep(1.1)
        self.assertTrue(item.is_expired())

    def test_expiration_conflict(self):
        now = datetime.now()
        item = MemoryItem(
            content="test",
            source="test",
            timestamp=now,
            duration="2h",
            end_time=now + timedelta(hours=1)
        )
        # Should use end_time (more restrictive)
        print(now)
        print("mike", item.get_expiration_time())
        self.assertEqual(
            item.get_expiration_time(),
            now + timedelta(hours=1)
        )

    def test_read_protocols(self):
        # Test KEEP protocol
        item = MemoryItem(
            content="test",
            source="test",
            r_protocol=MemoryItemReadProtocol.KEEP
        )
        self.assertEqual(item.read(), "test")
        self.assertEqual(item.state, MemoryItemState.NORMAL)
        
        # Test BURN_AFTER_READ protocol
        item = MemoryItem(
            content="test",
            source="test",
            r_protocol=MemoryItemReadProtocol.BURN_AFTER_READ
        )
        self.assertEqual(item.read(), "test")
        self.assertEqual(item.state, MemoryItemState.EXPIRED)

    def test_modify_protocols(self):
        # Test OVERWRITE protocol
        item = MemoryItem(
            content="original",
            source="test",
            m_protocol=MemoryItemModifyProtocol.OVERWRITE
        )
        item.modify("new")
        self.assertEqual(item.content, "new")
        
        # Test APPEND protocol with list
        item = MemoryItem(
            content=[],
            source="test",
            m_protocol=MemoryItemModifyProtocol.APPEND
        )
        item.modify(1)
        self.assertEqual(item.content, [1])
        item.modify(2)
        self.assertEqual(item.content, [1, 2])
        
        # Test APPEND protocol with non-list
        item = MemoryItem(
            content="string",
            source="test",
            m_protocol=MemoryItemModifyProtocol.APPEND
        )
        with self.assertRaises(iGymMemoryUnappendableError):
            item.modify("append")

    def test_history_tracking(self):
        item = MemoryItem(content="test", source="test")
        item.read(reader="user1")
        item.modify("new content", modifier="user2")
        self.assertEqual(len(item.history), 3)  # init + read + modify
        self.assertEqual(item.history[1]["action"], "read")
        self.assertEqual(item.history[2]["action"], "modify")

    def test_duration_validation(self):
        with self.assertRaises(ValueError):
            MemoryItem(
                content="test",
                source="test",
                duration="invalid"
            )

    def test_end_time_validation(self):
        with self.assertRaises(ValueError):
            MemoryItem(
                content="test",
                source="test",
                end_time="invalid format"
            )

if __name__ == '__main__':
    unittest.main()