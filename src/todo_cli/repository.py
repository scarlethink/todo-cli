from __future__ import annotations
from typing import Optional
from datetime import date
from sqlalchemy import select, or_
from todo_cli.db import TaskORM, get_session, to_dict
from todo_cli.models import Task, TaskIn



class TaskRepo:
    def add(self, data: TaskIn) -> Task:
        with get_session() as s, s.begin():
            row = TaskORM(
                title=data.title,
                notes=data.notes,
                priority=data.priority,
                due=data.due,
                tags=data.tags,
            )
            s.add(row)
            s.flush()
            return Task(**to_dict(row))

    def list(
        self,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        tag: Optional[str] = None,
        due_before: Optional[date] = None,
        query: Optional[str] = None,  # <-- arama desteği
    ) -> list[Task]:
        with get_session() as s:
            stmt = select(TaskORM)
            if status:
                stmt = stmt.where(TaskORM.status == status)
            if priority:
                stmt = stmt.where(TaskORM.priority == priority)
            if tag:
                stmt = stmt.where(TaskORM.tags.contains([tag]))
            if due_before:
                stmt = stmt.where(TaskORM.due <= due_before)
            if query:
                q = f"%{query.lower()}%"
                stmt = stmt.where(or_(TaskORM.title.ilike(q), TaskORM.notes.ilike(q)))
            rows = s.scalars(stmt).all()
            return [Task(**to_dict(r)) for r in rows]

    def set_status(self, task_id: int, status: str) -> Task | None:
        with get_session() as s, s.begin():
            row = s.get(TaskORM, task_id)
            if not row:
                return None
            row.status = status
            s.flush()
            return Task(**to_dict(row))

    def edit(self, task_id: int, data: TaskIn) -> Task | None:
        with get_session() as s, s.begin():
            row = s.get(TaskORM, task_id)
            if not row:
                return None
            row.title = data.title
            row.notes = data.notes
            row.priority = data.priority
            row.due = data.due
            row.tags = data.tags
            s.flush()
            return Task(**to_dict(row))

    def remove(self, task_id: int) -> bool:
        with get_session() as s, s.begin():
            row = s.get(TaskORM, task_id)
            if not row:
                return False
            s.delete(row)
            return True
