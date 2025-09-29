from datetime import datetime, date
from typing import Optional, Literal
from pydantic import BaseModel, Field

Priority = Literal["low", "med", "high"]
Status = Literal["todo", "doing", "done"]

class TaskIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    notes: Optional[str] = None
    due: Optional[date] = None
    priority: Priority = "med"
    tags: list[str] = Field(default_factory=list)

class Task(TaskIn):
    id: int
    status: Status = "todo"
    created_at: datetime
    updated_at: datetime
