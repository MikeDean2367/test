import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

import unittest
from igym.memory.base import MemorySystem, BaseMemory
from igym.memory.type import iGymMemoryDuplicateUIDError, iGymMemoryNotFound

class TestMemorySystem(unittest.TestCase):
    def setUp(self):
        # Clear any existing instances
        MemorySystem.reset()
        self.system = MemorySystem()

    def test_singleton_pattern(self):
        self.setUp()
        instance1 = MemorySystem()
        instance2 = MemorySystem()
        self.assertIs(instance1, instance2)

    def test_memory_registration(self):
        self.setUp()
        memory = BaseMemory("test_mem")
        self.system.register_memory(memory)
        self.assertEqual(self.system._memories["test_mem"], memory)

    def test_duplicate_registration(self):
        self.setUp()
        memory1 = BaseMemory("duplicate_test")
        self.system.register_memory(memory1)
        
        with self.assertRaises(iGymMemoryDuplicateUIDError):
            memory2 = BaseMemory("duplicate_test")
            self.system.register_memory(memory2)

    def test_get_memory(self):
        self.setUp()
        memory = BaseMemory("get_test")
        self.system.register_memory(memory)
        
        retrieved = self.system.get_memory("get_test")
        self.assertEqual(retrieved, memory)
        
        with self.assertRaises(iGymMemoryNotFound):
            self.system.get_memory("nonexistent")

if __name__ == '__main__':
    unittest.main()