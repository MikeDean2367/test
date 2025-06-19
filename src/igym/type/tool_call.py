from typing import Any, Dict, Optional, Union, List
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field, validator
import uuid


class ToolCallingItem(BaseModel):
    id: str
    name: str
    params: Dict[str, Any]
    role: str = "tool"
    content: Optional[str] = None

