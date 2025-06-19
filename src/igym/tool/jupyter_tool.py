
from .base import BaseSession, ToolRegistry
from .docker_session import DockerSession

import os
import uuid
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
from nbformat import v4 as nbformat
from nbformat import reads, writes
from nbconvert.preprocessors import ExecutePreprocessor

class JupyterSession(BaseSession):
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the Jupyter session with optional configuration
        
        Args:
            config: Dictionary containing:
                   - workspace_path: Path to store notebook files (default: './jupyter_workspace')
                   - notebook_name: Name of the notebook file (default: random uuid)
        """
        super().__init__(config)
        self.workspace_path = Path(
            self.config.get('workspace_path', './jupyter_workspace')
        )
        self.notebook_name = self.config.get(
            'notebook_name', 
            f"notebook_{uuid.uuid4().hex[:8]}.ipynb"
        )
        self.notebook_path = self.workspace_path / self.notebook_name
        self.notebook = None
        self.command_history = []
        self.current_cell_index = 0
        
        # Create workspace if it doesn't exist
        self.workspace_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize new notebook if one doesn't exist
        if not self.notebook_path.exists():
            self._create_new_notebook()
        else:
            self._load_notebook()
    
    def _create_new_notebook(self):
        """Create a new Jupyter notebook"""
        self.notebook = nbformat.new_notebook()
        self._save_notebook()
        self.command_history = []
        self.current_cell_index = 0
    
    def _load_notebook(self):
        """Load an existing Jupyter notebook"""
        with open(self.notebook_path, 'r', encoding='utf-8') as f:
            self.notebook = reads(f.read(), as_version=4)
        self.current_cell_index = len(self.notebook.cells)
    
    def _save_notebook(self):
        """Save the current notebook to file"""
        with open(self.notebook_path, 'w', encoding='utf-8') as f:
            f.write(writes(self.notebook))
    
    @ToolRegistry().register(
        parameters={
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Shell command to execute",
                    
                }
            },
            "required": ["code"]
        },
        name='jupyter_execute', 
        timeout=30,
        require_session=True
    )
    def execute_command(self, code: str) -> str:
        """
        Execute Python code in the Jupyter notebook
        
        Args:
            code: Python code to execute
            
        Returns:
            Execution results or error message
        """
        if not self.is_active():
            return "Session is not active"
        
        try:
            # Add cell to notebook
            new_cell = nbformat.new_code_cell(source=code)
            self.notebook.cells.append(new_cell)
            self.current_cell_index = len(self.notebook.cells) - 1
            
            # Execute the cell
            ep = ExecutePreprocessor(timeout=60, kernel_name='python3')
            ep.preprocess(self.notebook, {'metadata': {'path': str(self.workspace_path)}})
            
            # Save notebook and record command
            self._save_notebook()
            self.command_history.append(code)
            
            # Get execution results
            output = []
            for cell in self.notebook.cells:
                if 'outputs' in cell:
                    for out in cell.outputs:
                        if 'text' in out:
                            output.append(out['text'])
                        elif 'data' in out and 'text/plain' in out['data']:
                            output.append(out['data']['text/plain'])
            
            return '\n'.join(output[-5:])  # Return last 5 outputs
        
        except Exception as e:
            return f"Error executing code: {str(e)}"
    
    @ToolRegistry().register(
        name='jupyter_undo', 
        timeout=10,
        require_session=True,
        parameters={}
    )
    def undo_last_command(self) -> str:
        """
        Undo the last executed command by removing the last cell
        
        Returns:
            Status message
        """
        if not self.notebook.cells:
            return "No commands to undo"
        
        self.notebook.cells.pop()
        self.current_cell_index = max(0, len(self.notebook.cells) - 1)
        self._save_notebook()
        return "Last command undone"
    
    @ToolRegistry().register(
        name='jupyter_new', 
        timeout=10,
        require_session=True,
        parameters={}
    )
    def new_notebook(self, notebook_name: Optional[str] = None) -> str:
        """
        Create a new notebook
        
        Args:
            notebook_name: Optional name for the new notebook
            
        Returns:
            Status message
        """
        if notebook_name:
            self.notebook_name = notebook_name if notebook_name.endswith('.ipynb') else f"{notebook_name}.ipynb"
            self.notebook_path = self.workspace_path / self.notebook_name
        
        self._create_new_notebook()
        return f"New notebook created at {self.notebook_path}"
    
    @ToolRegistry().register(
        name='jupyter_clear', 
        timeout=10,
        require_session=True,
        parameters={}
    )
    def clear_notebook(self) -> str:
        """
        Clear all cells from the current notebook
        
        Returns:
            Status message
        """
        self.notebook.cells = []
        self.current_cell_index = 0
        self._save_notebook()
        return "Notebook cleared"
    
    @ToolRegistry().register(
        name='jupyter_list', 
        timeout=10,
        require_session=True,
        parameters={}
    )
    def list_notebooks(self) -> List[str]:
        """
        List all notebooks in the workspace
        
        Returns:
            List of notebook filenames
        """
        return [f.name for f in self.workspace_path.glob('*.ipynb')]
    
    @ToolRegistry().register(
        name='jupyter_switch', 
        timeout=10,
        require_session=True,
        parameters={}
    )
    def switch_notebook(self, notebook_name: str) -> str:
        """
        Switch to a different notebook in the workspace
        
        Args:
            notebook_name: Name of the notebook to switch to
            
        Returns:
            Status message
        """
        if not notebook_name.endswith('.ipynb'):
            notebook_name += '.ipynb'
            
        new_path = self.workspace_path / notebook_name
        if not new_path.exists():
            return f"Notebook {notebook_name} not found"
        
        self.notebook_name = notebook_name
        self.notebook_path = new_path
        self._load_notebook()
        return f"Switched to notebook {notebook_name}"
    
    @ToolRegistry().register(
        name='jupyter_history', 
        timeout=10,
        require_session=True,
        parameters={}
    )
    def get_command_history(self) -> List[str]:
        """
        Get the history of executed commands
        
        Returns:
            List of previously executed commands
        """
        return self.command_history
    
    def save(self) -> Dict[str, Any]:
        """Save session state for persistence"""
        state = super().save()
        state.update({
            'workspace_path': str(self.workspace_path),
            'notebook_name': self.notebook_name,
            'command_history': self.command_history,
            'current_cell_index': self.current_cell_index
        })
        return state
    
    @classmethod
    def load(cls, state: Dict[str, Any]) -> 'JupyterSession':
        session = super().load(state)
        session.workspace_path = Path(state['workspace_path'])
        session.notebook_name = state['notebook_name']
        session.notebook_path = session.workspace_path / session.notebook_name
        session.command_history = state.get('command_history', [])
        session.current_cell_index = state.get('current_cell_index', 0)
        session._load_notebook()
        return session

    
    # def load(self, state: Dict[str, Any]) -> None:
    #     """Load session state from persistence"""
    #     super().load(state)
    #     self.workspace_path = Path(state['workspace_path'])
    #     self.notebook_name = state['notebook_name']
    #     self.notebook_path = self.workspace_path / self.notebook_name
    #     self.command_history = state.get('command_history', [])
    #     self.current_cell_index = state.get('current_cell_index', 0)
    #     self._load_notebook()


