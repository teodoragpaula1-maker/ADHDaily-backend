from fastapi import APIRouter
from models import Task

router = APIRouter()

@router.get("/focus-tasks")
def get_focus_tasks() -> list[Task]:
    tasks = [
        Task(id=1, title="Put baby clothes in the hamper", size="tiny", category="home"),
        Task(id=2, title="Reply to insurance email", size="medium", category="admin"),
        Task(id=3, title="Sort documents for 10 minutes", size="big", category="home"),
    ]
    return tasks
