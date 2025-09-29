# src/todo_cli/db.py
from datetime import datetime
from pathlib import Path
from sqlalchemy import create_engine, Integer, String, Date, DateTime, JSON
from sqlalchemy import Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session
from sqlalchemy.types import Enum as SAEnum

# DB: %USERPROFILE%\.todo_cli\todo.db
APP_DIR = Path.home() / ".todo_cli"
APP_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = APP_DIR / "todo.db"
DB_URL = f"sqlite:///{DB_PATH.as_posix()}"

class Base(DeclarativeBase): ...
# (geri kalanı aynen)

class TaskORM(Base):
    __tablename__ = "tasks"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200))
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(SAEnum("todo", "doing", "done", name="status_enum"), default="todo")
    priority: Mapped[str] = mapped_column(SAEnum("low", "med", "high", name="priority_enum"), default="med")
    due: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

engine = create_engine(DB_URL, echo=False, future=True)

def init_db() -> None:
    Base.metadata.create_all(engine)

def get_session() -> Session:
    return Session(engine)

def to_dict(row: TaskORM) -> dict:
    return {
        "id": row.id,
        "title": row.title,
        "notes": row.notes,
        "status": row.status,
        "priority": row.priority,
        "due": row.due,
        "tags": row.tags,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }
