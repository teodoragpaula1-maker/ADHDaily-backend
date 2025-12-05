from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from models import Task
from routes.tasks import router as tasks_router

app = FastAPI()

# --- CORS FIX ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # allow your frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# ----------------

@app.get("/health")
def health_check():
    return {"status": "ok"}

# Include the routes from routes/tasks.py
app.include_router(tasks_router)
