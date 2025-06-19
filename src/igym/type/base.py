from typing import Any, Dict, Optional, Union, List
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field, validator
import uuid

class TransactionType(str, Enum):
    ACTION = "action"
    OBSERVATION = "observation"
    CONTROL = "control"  

class Transaction(BaseModel):
    transaction_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    transaction_type: TransactionType
    sender: str
    receivers: List[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    priority: int = Field(default=5, ge=0, le=9)
    expiration: Optional[datetime] = None

    def add_receiver(self, receiver_id: str) -> None:
        """add one reciever"""
        if receiver_id not in self.receivers:
            self.receivers.append(receiver_id)

    def add_metadata(self, key: str, value: Any) -> None:
        """添加元数据"""
        self.metadata[key] = value

    def is_expired(self) -> bool:
        """检查消息是否已过期"""
        if self.expiration is None:
            return False
        return datetime.utcnow() > self.expiration
    


