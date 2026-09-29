"""Rutas públicas (solo lectura): índice, parciales HTMX y API JSON."""
import re

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.services import docker_service, player_service, status_service

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


@router.get("/partials/mods", response_class=HTMLResponse)
def partial_mods(request: Request):
    mc = status_service.query_status()
    return templates.TemplateResponse(
        request, "partials/mods.html", {"mc": mc}
    )


@router.get("/partials/player/{name}", response_class=HTMLResponse)
def partial_player(request: Request, name: str):
    # Solo [A-Za-z0-9_], máx 16 (nicks de Minecraft): nada raro llega al fs
    clean = re.sub(r"[^A-Za-z0-9_]", "", name)[:16]
    if not clean:
        return templates.TemplateResponse(
            request,
            "partials/player_modal.html",
            {"p": {"ok": False, "error": "nombre inválido"}},
        )
    return templates.TemplateResponse(
        request, "partials/player_modal.html", {"p": player_service.get_player(clean)}
    )


@router.get("/api/status")
def api_status():
    return {
        "container": docker_service.container_status(),
        "minecraft": status_service.query_status(),
    }
