import random
from fastapi import APIRouter, HTTPException
from models import Task, TaskCreate
from db import get_connection

router = APIRouter()


@router.get("/focus-tasks")
def get_focus_tasks() -> list[Task]:
    # 1) Open DB connection
    conn = get_connection()
    cur = conn.cursor()

    # 2) Run a query to fetch tasks
    cur.execute(
        """
        SELECT id, title, size, category, importance, due_date, status
        FROM tasks
        WHERE status = 'pending'
        ORDER BY
            importance DESC NULLS LAST,
            due_date ASC NULLS LAST,
            id ASC
        LIMIT 20;
        """
    )
    rows = cur.fetchall()

    # 3) Close DB stuff
    cur.close()
    conn.close()

    # 4) Convert rows (tuples) into Task objects
    tasks: list[Task] = []
    for row in rows:
        task = Task(
            id=row[0],
            title=row[1],
            size=row[2],
            category=row[3],
            importance=row[4],
            due_date=row[5],
            status=row[6],
        )
        tasks.append(task)

    return tasks
@router.get("/focus-tasks/random")
def get_random_focus_tasks() -> list[Task]:
    """
    Pick up to 3 pending tasks, trying to mix sizes:
    - 1 tiny
    - 1 medium
    - 1 big
    If there aren't enough, fill with whatever is available.
    """
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT id, title, size, category, importance, due_date, status
        FROM tasks
        WHERE status = 'pending';
        """
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()

    # Convert rows into Task objects, and group by size
    tiny_tasks: list[Task] = []
    medium_tasks: list[Task] = []
    big_tasks: list[Task] = []

    all_tasks: list[Task] = []

    for row in rows:
        task = Task(
            id=row[0],
            title=row[1],
            size=row[2],       # row[2] is 'tiny' | 'medium' | 'big'
            category=row[3],
            importance=row[4],
            due_date=row[5],
            status=row[6],
        )
        all_tasks.append(task)

        if row[2] == "tiny":
            tiny_tasks.append(task)
        elif row[2] == "medium":
            medium_tasks.append(task)
        elif row[2] == "big":
            big_tasks.append(task)

    selected: list[Task] = []

    # Try to pick one from each size bucket
    if tiny_tasks:
        selected.append(random.choice(tiny_tasks))
    if medium_tasks:
        selected.append(random.choice(medium_tasks))
    if big_tasks:
        selected.append(random.choice(big_tasks))

    # If we still have fewer than 3, fill up with remaining tasks
    if len(selected) < 3:
        remaining = [t for t in all_tasks if t not in selected]
        random.shuffle(remaining)
        needed = 3 - len(selected)
        selected.extend(remaining[:needed])

    return selected


@router.post("/tasks")
def create_task(task_in: TaskCreate) -> Task:
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO tasks (title, size, category, importance, due_date, status)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id, title, size, category, importance, due_date, status;
        """,
        (
            task_in.title,
            task_in.size,
            task_in.category,
            task_in.importance,
            task_in.due_date,
            "pending",
        ),
    )

    row = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()

    return Task(
        id=row[0],
        title=row[1],
        size=row[2],
        category=row[3],
        importance=row[4],
        due_date=row[5],
        status=row[6],
    )


@router.post("/tasks/{task_id}/complete")
def complete_task(task_id: int) -> Task:
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        UPDATE tasks
        SET status = 'completed'
        WHERE id = %s
        RETURNING id, title, size, category, importance, due_date, status;
        """,
        (task_id,),
    )

    row = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()

    if row is None:
        # no task with that id
        raise HTTPException(status_code=404, detail="Task not found")

    return Task(
        id=row[0],
        title=row[1],
        size=row[2],
        category=row[3],
        importance=row[4],
        due_date=row[5],
        status=row[6],
    )
@router.get("/tasks")
def list_tasks(status: str | None = None) -> list[Task]:
    """
    List tasks, optionally filtered by status.
    - status can be 'pending', 'completed', or None (all)
    """
    conn = get_connection()
    cur = conn.cursor()

    if status in ("pending", "completed"):
        cur.execute(
            """
            SELECT id, title, size, category, importance, due_date, status
            FROM tasks
            WHERE status = %s
            ORDER BY id ASC;
            """,
            (status,),
        )
    else:
        # no filter → return all
        cur.execute(
            """
            SELECT id, title, size, category, importance, due_date, status
            FROM tasks
            ORDER BY id ASC;
            """
        )

    rows = cur.fetchall()
    cur.close()
    conn.close()

    tasks: list[Task] = []
    for row in rows:
        task = Task(
            id=row[0],
            title=row[1],
            size=row[2],
            category=row[3],
            importance=row[4],
            due_date=row[5],
            status=row[6],
        )
        tasks.append(task)

    return tasks
