import os, secrets
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database import Base, engine
from .routers import patients, reports

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Hematology Lab Reports API")

# Fixed single-technician credentials (simple auth)
TECH_USERNAME = "technician"
TECH_PASSWORD = "lab123"

# Simple in-memory token store {token: expiry}
_tokens = {}

# CORS: accept production frontend URL(s) from env, plus local dev defaults.
_extra_origins = os.environ.get("CORS_ORIGINS", "").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "https://hematology-lab-project.vercel.app",
        *[_o.strip() for _o in _extra_origins if _o.strip()],
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    token: str


@app.post("/auth/login", response_model=TokenResponse)
def login(credentials: LoginRequest):
    if (
        credentials.username == TECH_USERNAME
        and credentials.password == TECH_PASSWORD
    ):
        token = secrets.token_urlsafe(32)
        _tokens[token] = datetime.now() + timedelta(hours=12)
        return TokenResponse(token=token)
    raise HTTPException(status_code=401, detail="Invalid credentials")


@app.get("/auth/me")
def me(authorization: Optional[str] = Header(None)):
    token = _extract_token(authorization)
    if token not in _tokens or _tokens[token] < datetime.now():
        raise HTTPException(status_code=401, detail="Not authenticated")
    return {"username": TECH_USERNAME}


def _extract_token(authorization: Optional[str]) -> Optional[str]:
    if not authorization:
        return None
    parts = authorization.split()
    return parts[1] if len(parts) == 2 else None


app.include_router(patients.router)
app.include_router(reports.router)


@app.get("/")
def root():
    return {"status": "ok", "service": "hematology-lab-reports"}
