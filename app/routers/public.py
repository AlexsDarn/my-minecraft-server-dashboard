"""Rutas públicas (solo lectura): índice, parciales HTMX y API JSON."""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.services import docker_service, status_service

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(request, "index.html", {})


@router.get("/partials/status", response_class=HTMLResponse)
def partial_status(request: Request):
    container = docker_service.container_status()
    mc = status_service.query_status()
    return templates.TemplateResponse(
        request, "partials/status.html", {"container": container, "mc": mc}
    )


@router.get("/partials/players", response_class=HTMLResponse)
def partial_players(request: Request):
    mc = status_service.query_status()
    return templates.TemplateResponse(
        request, "partials/players.html", {"mc": mc}
    )


@router.get("/api/status")
def api_status():
    return {
        "container": docker_service.container_status(),
        "minecraft": status_service.query_status(),
    }
