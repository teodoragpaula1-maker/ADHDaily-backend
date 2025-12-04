from pydantic import BaseModel
from typing import Optional
from datetime import date

class Task(BaseModel):
    id: int
    title: str
    size: str
    category: Optional[str] = None
    importance: Optional[int] = None
    due_date: Optional[date] = None
    status: str = "pending"
