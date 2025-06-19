import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

import unittest
from datetime import datetime
from igym.memory.tree_memory import TreeMemory, TreeMemoryItem
from igym.memory.type import iGymMemoryItemNotFound
from igym.memory.base import MemorySystem

class TestTreeMemoryItem(unittest.TestCase):
    def setUp(self):
        MemorySystem.reset()
        self.root = TreeMemoryItem(
            content="root content",
            source="test",
            depth=0
        )
        self.child1 = TreeMemoryItem(
            content="child1 content",
            source="test",
            depth=1,
            parent_uid="root_uid"
        )
        self.child2 = TreeMemoryItem(
            content="child2 content",
            source="test",
            depth=1,
            parent_uid="root_uid"
        )

    def test_add_remove_child(self):
        self.setUp()
        # Test adding children
        self.root.add_child(self.child1)
        self.assertEqual(len(self.root.children_uids), 1)
        self.assertEqual(self.child1.parent_uid, self.root.uid)
        
        # Test removing child by object
        self.root.remove_child(child=self.child1)
        self.assertEqual(len(self.root.children_uids), 0)
        
        # Test removing child by uid
        self.root.add_child(self.child1)
        self.root.remove_child(child_uid=self.child1.uid)
        self.assertEqual(len(self.root.children_uids), 0)

    def test_recursive_add_child(self):
        self.setUp()
        # Create a mock items dictionary
        items = {
            self.child1.uid: self.child1,
            self.child2.uid: self.child2
        }
        
        # Add child with recursive depth
        self.root.add_child(self.child1, recursive_depth=True, all_items=items)
        self.assertEqual(self.child1.depth, 1)
        
        # Add grandchild
        grandchild = TreeMemoryItem(
            content="grandchild content",
            source="test",
            parent_uid=self.child1.uid
        )
        items[grandchild.uid] = grandchild
        self.child1.add_child(grandchild)
        
        # Test recursive depth update
        self.root.add_child(self.child1, recursive_depth=True, all_items=items)
        self.assertEqual(grandchild.depth, 2)

    def test_become_root(self):
        self.setUp()
        items = {
            self.child1.uid: self.child1,
            self.child2.uid: self.child2
        }
        
        # Set up hierarchy
        self.root.add_child(self.child1)
        self.root.add_child(self.child2)
        
        # Make child1 a root
        self.child1.become_root(recursive_depth=True, all_items=items)
        
        self.assertIsNone(self.child1.parent_uid)
        self.assertEqual(self.child1.depth, 0)
        self.assertEqual(self.child2.depth, 1)

    def test_properties(self):
        self.setUp()
        # Test is_root
        self.assertTrue(self.root.is_root)
        self.assertFalse(self.child1.is_root)
        
        # Test is_leaf
        self.assertTrue(self.child1.is_leaf)
        self.root.add_child(self.child1)
        self.assertFalse(self.root.is_leaf)

class TestTreeMemory(unittest.TestCase):
    def setUp(self):
        MemorySystem.reset()
        self.tree = TreeMemory("test_tree")
        
        # Create items
        self.root = TreeMemoryItem(content="root", source="test", uid="root")
        self.child1 = TreeMemoryItem(content="child1", source="test", uid="c1")
        self.child2 = TreeMemoryItem(content="child2", source="test", uid="c2")
        self.grandchild = TreeMemoryItem(content="grandchild", source="test", uid="gc")

    def test_add_items(self):
        self.setUp()
        # Add root
        root_uid = self.tree.add(self.root)
        self.assertEqual(len(self.tree.root_uids), 1)
        
        # Add child to root
        child_uid = self.tree.add(self.child1, parent_uid=root_uid)
        root_item = self.tree.items[root_uid]
        self.assertEqual(len(root_item.children_uids), 1)
        self.assertEqual(self.tree.items[child_uid].parent_uid, root_uid)
        
        # Test adding with invalid parent
        with self.assertRaises(iGymMemoryItemNotFound):
            self.tree.add(self.child2, parent_uid="invalid_uid")

    def test_traverse(self):
        self.setUp()
        # Build tree structure
        root_uid = self.tree.add(self.root)
        child1_uid = self.tree.add(self.child1, parent_uid=root_uid)
        child2_uid = self.tree.add(self.child2, parent_uid=root_uid)
        grandchild_uid = self.tree.add(self.grandchild, parent_uid=child1_uid)
        
        # Test pre-order traversal
        pre_order = self.tree.traverse(root_uid, order="pre")
        self.assertEqual(len(pre_order), 4)
        self.assertEqual(pre_order[0], "root")
        
        # Test post-order traversal
        post_order = self.tree.traverse(root_uid, order="post")
        self.assertEqual(len(post_order), 4)
        self.assertEqual(post_order[-1], "root")
        
        # Test layer-order traversal
        layer_order = self.tree.traverse(root_uid, order="layer")
        self.assertEqual(len(layer_order), 3)  # 3 levels
        self.assertEqual(layer_order[0][0], "root")
        self.assertEqual(len(layer_order[1]), 2)  # 2 children

    def test_read(self):
        self.setUp()
        root_uid = self.tree.add(self.root)
        child1_uid = self.tree.add(self.child1, parent_uid=root_uid)
        child2_uid = self.tree.add(self.child2, parent_uid=root_uid)
        grandchild_uid = self.tree.add(self.grandchild, parent_uid=child1_uid)

        self.assertIsNotNone(self.tree['c1'])
        self.assertEqual(self.tree['c1'].content, self.tree.read('c1'))
        self.assertIsInstance(self.tree['c1'], TreeMemoryItem)

    def test_delete(self):
        """
        Start:
                   root
           child1       child2
        grandchild

        Then:
                  root
        grandchild     child2

        Final:

        """
        self.setUp()
        # Build tree structure
        root_uid = self.tree.add(self.root)
        child1_uid = self.tree.add(self.child1, parent_uid=root_uid)
        child2_uid = self.tree.add(self.child2, parent_uid=root_uid)
        grandchild_uid = self.tree.add(self.grandchild, parent_uid=child1_uid)

        # Test delete without children
        self.assertTrue(self.tree.delete(child1_uid))
        self.assertNotIn(child1_uid, self.tree.items)
        self.assertIn(grandchild_uid, self.tree.items)  # Grandchild should still exist
        self.assertEqual(self.tree.items[grandchild_uid].parent_uid, root_uid)

        # Test delete with children
        state = self.tree.delete(root_uid, with_children=True)
        self.assertTrue(state)
        self.assertNotIn(root_uid, self.tree.items)
        self.assertNotIn(child2_uid, self.tree.items)
        self.assertNotIn(grandchild_uid, self.tree.items)
        
        # Test delete non-existent item
        self.assertFalse(self.tree.delete("invalid_uid", return_false_if_error=True))

    def test_serialization(self):
        self.setUp()
        # Build tree
        root_uid = self.tree.add(self.root)
        child_uid = self.tree.add(self.child1, parent_uid=root_uid)
        
        # Save and load
        data = self.tree.save()
        print(data)
        MemorySystem.reset()
        new_tree = TreeMemory.load(data)
        
        # Verify structure
        print(new_tree.root_uids)
        self.assertEqual(len(new_tree.root_uids), 1)
        self.assertEqual(len(new_tree.items), 2)
        self.assertEqual(new_tree.items[root_uid].children_uids, [child_uid])

if __name__ == '__main__':
    unittest.main()