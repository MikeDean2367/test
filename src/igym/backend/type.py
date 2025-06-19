
from enum import Enum
from pydantic import BaseModel, Field, validator
from typing import List, Dict, Any, Optional, Union
from abc import ABC
import warnings
import tenacity
from functools import wraps

class DecodingConfig(BaseModel):
    temperature: float = Field(0.7, ge=0, le=2)
    top_p: float = Field(1.0, ge=0, le=1)
    max_tokens: Optional[int] = Field(None, gt=0)
    frequency_penalty: float = Field(None, ge=-2, le=2)
    presence_penalty: float = Field(None, ge=-2, le=2)
    max_completion_tokens: int = Field(None, gt=0)
    extra_params: Dict[str, Any] = Field(default_factory=dict)

class BackendInput(BaseModel):
    model: str
    messages: List[Dict[str, Any]]
    decode_config: Optional[DecodingConfig] = None
    tools: Optional[List[Dict[str, Any]]] = None
    extra_params: Dict[str, Any] = {}
    stream: bool = False

class BackendOutput(BaseModel):
    id: str
    messages: Any
    role: str
    finish_reason: str
    completion_tokens: int
    prompt_tokens: int
    total_tokens: int

class BackendConfig(BaseModel):
    """Enhanced base config with validation"""
    timeout: int = Field(30, gt=0)
    max_retries: int = Field(3, ge=0)
    retry_delay: float = Field(1.0, gt=0)
    base_url: Optional[Union[str, List[str]]] = None
    api_keys: Optional[Union[str, List[str]]] = None
    qps: Optional[Union[int, List[int]]] = None
    rate_limit: Optional[Union[int, List[int]]] = None
    decode_config: Optional[DecodingConfig] = None
    
    @validator('timeout')
    def validate_timeout(cls, v):
        if v > 300:
            warnings.warn("Timeout exceeds 300s, consider optimizing your backend")
        return v


"""
一个
"""

