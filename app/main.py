"""Punto de entrada: crea la app, monta static y registra routers."""
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.routers import admin, public

BASE = Path(__file__).resolve().parent

app = FastAPI(title="Minecraft Dashboard")
app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")
app.include_router(public.router)
app.include_router(admin.router)
