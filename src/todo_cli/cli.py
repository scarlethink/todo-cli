from __future__ import annotations
import json
import csv
from pathlib import Path
import typer
from rich.table import Table
from rich.console import Console
from datetime import date
from typing import Optional
from todo_cli.db import init_db
from todo_cli.models import TaskIn
from todo_cli.repository import TaskRepo


app = typer.Typer(help="Simple, professional TODO CLI")
console = Console()
repo = TaskRepo()


@app.callback()
def _init():
    init_db()


@app.command("add")
def add(
    title: str = typer.Argument(..., help="Task title"),
    notes: Optional[str] = typer.Option(None, "--notes", "-n"),
    due: Optional[str] = typer.Option(None, "--due", help="YYYY-MM-DD"),
    priority: str = typer.Option("med", "--priority", "-p", help="[low|med|high]"),
    tags: list[str] = typer.Option([], "--tag", "-t"),
):
    due_dt = date.fromisoformat(due) if due else None
    task = repo.add(TaskIn(title=title, notes=notes, due=due_dt, priority=priority, tags=tags))
    console.print(f"[bold green]Added[/] #{task.id}: {task.title}")


@app.command("ls")
def ls(
    status: Optional[str] = typer.Option(None, "--status"),
    priority: Optional[str] = typer.Option(None, "--priority"),
    tag: Optional[str] = typer.Option(None, "--tag"),
    due_before: Optional[str] = typer.Option(None, "--due-before"),
    query: Optional[str] = typer.Option(None, "--query", "-q"),  # <-- arama
):
    due_dt = date.fromisoformat(due_before) if due_before else None
    tasks = repo.list(status=status, priority=priority, tag=tag, due_before=due_dt, query=query)

    table = Table(title="Tasks", show_lines=True)
    for col in ["id", "title", "status", "priority", "due", "tags"]:
        table.add_column(col)

    for t in tasks:
        table.add_row(str(t.id), t.title, t.status, t.priority, str(t.due), ", ".join(t.tags))
    console.print(table)


@app.command("done")
def done(task_id: int):
    t = repo.set_status(task_id, "done")
    if not t:
        console.print("[red]Not found[/]")
        raise typer.Exit(code=1)
    console.print(f"[bold green]Completed[/] #{t.id}: {t.title}")


@app.command("edit")
def edit(
    task_id: int,
    title: str = typer.Option(..., "--title"),
    notes: Optional[str] = typer.Option(None, "--notes"),
    due: Optional[str] = typer.Option(None, "--due"),
    priority: str = typer.Option("med", "--priority"),
    tags: list[str] = typer.Option([], "--tag"),
):
    due_dt = date.fromisoformat(due) if due else None
    t = repo.edit(task_id, TaskIn(title=title, notes=notes, due=due_dt, priority=priority, tags=tags))
    if not t:
        console.print("[red]Not found[/]")
        raise typer.Exit(code=1)
    console.print(f"[bold cyan]Updated[/] #{t.id}: {t.title}")


@app.command("rm")
def rm(task_id: int):
    ok = repo.remove(task_id)
    if not ok:
        console.print("[red]Not found[/]")
        raise typer.Exit(code=1)
    console.print(f"[yellow]Removed[/] #{task_id}")


@app.command("export")
def export_cmd(
    out: Path = typer.Argument(..., help="Çıktı dosya yolu (örn. data.csv / data.json)"),
    fmt: Optional[str] = typer.Option(None, "--format", "-f", help="[csv|json] (uzantıdan da anlar)"),
):
    ext = (fmt or out.suffix.lstrip(".")).lower()
    tasks = repo.list()
    records = [t.model_dump() for t in tasks]

    if ext == "json":
        out.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
        console.print(f"[bold green]Exported[/] {len(records)} task(s) → {out}")
    elif ext == "csv":
        fieldnames = (
            list(records[0].keys())
            if records
            else ["id", "title", "notes", "status", "priority", "due", "tags", "created_at", "updated_at"]
        )
        with out.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in records:
                r = dict(r)
                r["tags"] = ", ".join(r.get("tags", []))
                writer.writerow(r)
        console.print(f"[bold green]Exported[/] {len(records)} task(s) → {out}")
    else:
        console.print("[red]Desteklenmeyen format. csv veya json kullanın.[/]")
        raise typer.Exit(code=1)


def main():
    app()


if __name__ == "__main__":
    main()
