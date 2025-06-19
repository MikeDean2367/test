import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))


import unittest
import tempfile
import shutil
from pathlib import Path
from igym.tool.jupyter_tool import JupyterSession

class TestJupyterSession(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory
        self.test_dir = tempfile.mkdtemp(dir=os.getcwd())
        self.workspace_path = Path(self.test_dir) / 'jupyter_workspace'
        self.config = {
            'workspace_path': str(self.workspace_path),
            'notebook_name': 'test_notebook.ipynb'
        }
        
    def tearDown(self):
        # Remove the directory after the test
        shutil.rmtree(self.test_dir)
    
    def test_initialization(self):
        session = JupyterSession(self.config)
        self.assertTrue(session.notebook_path.exists())
        self.assertEqual(session.notebook_name, 'test_notebook.ipynb')
        self.assertEqual(len(session.notebook.cells), 0)
        session.stop()
    
    def test_execute_command(self):
        session = JupyterSession(self.config)
        session.start()
        
        # Test simple command
        result = session.execute_command("x = 1 + 1\nx")
        self.assertIn('2', result.output)
        
        # Test command history
        self.assertEqual(len(session.command_history), 1)
        self.assertEqual(session.command_history[0], "x = 1 + 1\nx")
        
        # Test undo
        undo_result = session.undo_last_command()
        self.assertEqual(undo_result.output, "Last command undone")
        self.assertEqual(len(session.notebook.cells), 0)
        
        session.stop()
    
    def test_new_notebook(self):
        session = JupyterSession(self.config)
        session.start()
        
        new_name = "new_notebook.ipynb"
        result = session.new_notebook(new_name)
        self.assertEqual(result.output, f"New notebook created at {session.workspace_path/new_name}")
        self.assertTrue((session.workspace_path/new_name).exists())
        
        session.stop()
    
    def test_clear_notebook(self):
        session = JupyterSession(self.config)
        session.start()
        
        session.execute_command("x = 1")
        self.assertEqual(len(session.notebook.cells), 1)
        
        result = session.clear_notebook()
        self.assertEqual(result.output, "Notebook cleared")
        self.assertEqual(len(session.notebook.cells), 0)
        
        session.stop()
    
    def test_list_notebooks(self):
        session = JupyterSession(self.config)
        session.start()
        
        # Create another notebook
        session.new_notebook("another_notebook.ipynb")
        
        notebooks = session.list_notebooks()
        self.assertIn('test_notebook.ipynb', notebooks.output)
        self.assertIn('another_notebook.ipynb', notebooks.output)
        
        session.stop()
    
    def test_switch_notebook(self):
        session = JupyterSession(self.config)
        session.start()
        
        # Create and switch to another notebook
        session.execute_command("x = 1")
        session.new_notebook("another_notebook.ipynb")
        
        result = session.switch_notebook("test_notebook.ipynb")
        self.assertEqual(result.output, "Switched to notebook test_notebook.ipynb")
        self.assertEqual(len(session.notebook.cells), 1)
        
        session.stop()
    
    def test_save_load(self):
        session = JupyterSession(self.config)
        session.start()
        
        session.execute_command("x = 1")
        state = session.save()
        
        new_session = JupyterSession()
        new_session.load(state)
        
        self.assertEqual(new_session.notebook_name, 'test_notebook.ipynb')
        self.assertEqual(len(new_session.notebook.cells), 1)
        self.assertEqual(new_session.command_history, ["x = 1"])
        
        new_session.stop()

if __name__ == '__main__':
    unittest.main()