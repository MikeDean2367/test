
from typing import Any, Dict
from .base import BaseSession

class PythonSession(BaseSession):

    def __init__(self, config: Dict[str, Any] | None = None):
        super().__init__(config)
