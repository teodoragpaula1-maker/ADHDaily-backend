from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer

from pydantic import BaseModel, EmailStr

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    ForeignKey,
)
from sqlalchemy.orm import sessionmaker, declarative_base, relationship, Session

import hashlib

# ------------------------------------------------------------------------------
# Database setup
# ------------------------------------------------------------------------------

SQLALCHEMY_DATABASE_URL = "sqlite:///./adhdaily.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ------------------------------------------------------------------------------
# Models
# ------------------------------------------------------------------------------


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    tasks = relationship("Task", back_populates="owner")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    size = Column(String, default="tiny")  # tiny | medium | big
    category = Column(String, default="general")
    status = Column(String, default="pending")  # pending | completed
    importance = Column(Integer, default=1)
    due_date = Column(DateTime, nullable=True)
    is_routine = Column(Boolean, default=False)
    recurrence = Column(String, nullable=True)  # daily | weekly | monthly | None

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    owner = relationship("User", back_populates="tasks")


Base.metadata.create_all(bind=engine)

# ------------------------------------------------------------------------------
# Security helpers (simple hashing + simple token)
# ------------------------------------------------------------------------------

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")
oauth2_scheme_optional = OAuth2PasswordBearer(
    tokenUrl="auth/login", auto_error=False
)


def hash_password(password: str) -> str:
    # NOTE: for real production you’d use passlib / bcrypt etc.
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def verify_password(password: str, hashed: str) -> bool:
    return hash_password(password) == hashed


def get_user_from_token(db: Session, token: str) -> User:
    """
    Very simple "token" = user_id as string.
    In production you'd use a signed JWT instead.
    """
    try:
        user_id = int(token)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found for token",
        )
    return user


async def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
) -> User:
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    return get_user_from_token(db, token)


async def get_current_or_demo_user(
    db: Session = Depends(get_db),
    token: Optional[str] = Depends(oauth2_scheme_optional),
) -> User:
    """
    Used for task endpoints for now, so your existing frontend keeps working.
    - If a token is provided: use it to identify the user.
    - If no token: use a shared demo user.
    """
    if token:
        return get_user_from_token(db, token)

    demo_email = "demo@adhdaily.local"
    user = db.query(User).filter(User.email == demo_email).first()
    if not user:
        user = User(
            email=demo_email,
            hashed_password=hash_password("demo"),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


# ------------------------------------------------------------------------------
# Schemas
# ------------------------------------------------------------------------------


class UserCreate(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    email: EmailStr
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str


class TaskBase(BaseModel):
    title: str
    size: str = "tiny"  # tiny | medium | big
    category: str = "general"
    importance: int = 1
    due_date: Optional[datetime] = None
    is_routine: bool = False
    recurrence: Optional[str] = None  # daily | weekly | monthly


class TaskCreate(TaskBase):
    pass


class TaskOut(TaskBase):
    id: int
    status: str
    created_at: datetime
    updated_at: datetime
    user_id: int

    class Config:
        from_attributes = True


# ------------------------------------------------------------------------------
# App setup
# ------------------------------------------------------------------------------


app = FastAPI(title="ADHDaily API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # in dev you can keep this wide open
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ------------------------------------------------------------------------------
# Auth endpoints
# ------------------------------------------------------------------------------


@app.post("/auth/register", response_model=UserOut)
def register_user(payload: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.post("/auth/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """
    OAuth2PasswordRequestForm sends:
    - username (we use this as email)
    - password
    """
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    # Very simple "token" = user.id as string
    access_token = str(user.id)

    return Token(access_token=access_token, token_type="bearer")


@app.get("/auth/me", response_model=UserOut)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user


# ------------------------------------------------------------------------------
# Task endpoints (now bound to a user)
# ------------------------------------------------------------------------------


@app.get("/tasks/focus", response_model=List[TaskOut])
def get_focus_tasks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_or_demo_user),
):
    """
    Return all *pending* tasks for this user.
    (Frontend will choose which ones to show.)
    """
    tasks = (
        db.query(Task)
        .filter(
            Task.user_id == current_user.id,
            Task.status == "pending",
        )
        .order_by(Task.created_at.asc())
        .all()
    )
    return tasks


@app.get("/tasks/completed", response_model=List[TaskOut])
def get_completed_tasks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_or_demo_user),
):
    tasks = (
        db.query(Task)
        .filter(
            Task.user_id == current_user.id,
            Task.status == "completed",
        )
        .order_by(Task.updated_at.desc())
        .all()
    )
    return tasks


@app.post("/tasks", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
def create_task(
    payload: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_or_demo_user),
):
    task = Task(
        title=payload.title,
        size=payload.size,
        category=payload.category,
        importance=payload.importance,
        due_date=payload.due_date,
        is_routine=payload.is_routine,
        recurrence=payload.recurrence,
        status="pending",
        user_id=current_user.id,
    )

    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@app.post("/tasks/{task_id}/complete", response_model=TaskOut)
def complete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_or_demo_user),
):
    task = (
        db.query(Task)
        .filter(
            Task.id == task_id,
            Task.user_id == current_user.id,
        )
        .first()
    )
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    task.status = "completed"
    task.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(task)
    return task


@app.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_or_demo_user),
):
    task = (
        db.query(Task)
        .filter(
            Task.id == task_id,
            Task.user_id == current_user.id,
        )
        .first()
    )
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    db.delete(task)
    db.commit()
    return None


@app.get("/")
def health_check():
    return {"status": "ok", "message": "ADHDaily API with users is running"}
