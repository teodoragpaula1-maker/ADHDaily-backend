from pydantic import BaseModel
from typing import Optional
from datetime import date
from enum import Enum   

class TaskSize(str, Enum):
    tiny = "tiny"
    medium = "medium"
    big = "big"


class Task(BaseModel):
    id: int
    title: str
    size: TaskSize
    category: Optional[str] = None
    importance: Optional[int] = None
    due_date: Optional[date] = None
    status: str = "pending"


class TaskCreate(BaseModel):
    title: str
    size: TaskSize              
    category: Optional[str] = None
    importance: Optional[int] = None
    due_date: Optional[date] = None
