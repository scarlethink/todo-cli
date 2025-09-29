import subprocess
import os
from pathlib import Path

def run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True)

def setup_module(module):
    # clear DB
    if Path("todo.db").exists():
        os.remove("todo.db")

def test_add_and_list():
    add = run(["python", "-m", "src.todo_cli.cli", "add", "first-task", "--priority", "high", "--tag", "work"])
    assert add.returncode == 0
    ls = run(["python", "-m", "src.todo_cli.cli", "ls"])
    assert "first-task" in ls.stdout

def test_done():
    done = run(["python", "-m", "src.todo_cli.cli", "done", "1"])
    assert done.returncode == 0
    ls = run(["python", "-m", "src.todo_cli.cli", "ls", "--status", "done"])
    assert "first-task" in ls.stdout
