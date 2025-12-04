from fastapi import FastAPI
from models import Task
from routes.tasks import router as tasks_router

app = FastAPI()

@app.get("/health")
def health_check():
    return {"status": "ok"}

# include the routes from routes/tasks.py
app.include_router(tasks_router)

