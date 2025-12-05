from fastapi import APIRouter, HTTPException
from datetime import date
from models import Task, TaskCreate

router = APIRouter()

# ----------------------------------------
# In-memory "database"
# ----------------------------------------
tasks: list[Task] = []
next_id = 1


# ----------------------------------------
# Helper – generate new ID
# ----------------------------------------
def generate_id():
    global next_id
    current = next_id
    next_id += 1
    return current


# ----------------------------------------
# GET all tasks (optionally filter by status)
# ----------------------------------------
@router.get("/tasks")
def get_tasks(status: str | None = None):
    if status == "pending":
        return [t for t in tasks if t.status == "pending"]
    if status == "completed":
        return [t for t in tasks if t.status == "completed"]
    return tasks


# ----------------------------------------
# GET only completed tasks (History screen)
# ----------------------------------------
@router.get("/tasks/completed")
def get_completed_tasks():
    return [t for t in tasks if t.status == "completed"]


# ----------------------------------------
# CREATE a task
# ----------------------------------------
@router.post("/tasks", response_model=Task)
def create_task(task_data: TaskCreate):
    new_task = Task(
        id=generate_id(),
        title=task_data.title,
        size=task_data.size,
        category=task_data.category,
        importance=task_data.importance,
        due_date=task_data.due_date,
        status="pending",
        recurrence=task_data.recurrence,       # NEW: routine recurrence
        is_routine=task_data.recurrence is not None
    )

    tasks.append(new_task)
    return new_task


# ----------------------------------------
# COMPLETE a task
# ----------------------------------------
@router.post("/tasks/{task_id}/complete", response_model=Task)
def complete_task(task_id: int):
    for task in tasks:
        if task.id == task_id:
            task.status = "completed"
            return task
    raise HTTPException(status_code=404, detail="Task not found")


# ----------------------------------------
# DELETE a task
# ----------------------------------------
@router.delete("/tasks/{task_id}", response_model=Task)
def delete_task(task_id: int):
    """
    Deletes a task by ID and returns the deleted task.
    """
    global tasks
    for index, task in enumerate(tasks):
        if task.id == task_id:
            deleted = tasks.pop(index)
            return deleted

    raise HTTPException(status_code=404, detail="Task not found")


# ----------------------------------------
# STARTER TASKS for new users
# ----------------------------------------
@router.post("/tasks/starter")
def add_starter_tasks():
    global tasks

    starter_items = [
        ("Put baby clothes in the hamper", "tiny"),
        ("Brain dump for 5 minutes", "tiny"),
        ("Sort documents for 10 minutes", "big"),
    ]

    created = []
    for title, size in starter_items:
        new = Task(
            id=generate_id(),
            title=title,
            size=size,
            category=None,
            importance=None,
            due_date=None,
            status="pending",
            recurrence=None,
            is_routine=False
        )
        tasks.append(new)
        created.append(new)

    return {"added": created}
