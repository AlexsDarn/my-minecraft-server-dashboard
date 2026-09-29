"""Rutas públicas: estado, jugadores, mods, fichas y arranque del server."""
import logging
import re
import time

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.services import docker_service, player_service, status_service

log = logging.getLogger("mc-dashboard.public")

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

# Anti-spam del botón público de arranque (segundos entre intentos)
START_COOLDOWN_S = 60
_last_public_start = 0.0


@router.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(request, "index.html", {})


@router.get("/partials/status", response_class=HTMLResponse)
def partial_status(request: Request):
    container = docker_service.container_status()
    mc = status_service.query_status()
    return templates.TemplateResponse(
        request, "partials/status.html",
        {
            "container": container,
            "mc": mc,
            # Si se pidió arranque hace poco, el parcial muestra
            # "ARRANCANDO" en vez del botón (sobrevive al polling).
            "starting_recently": (time.monotonic() - _last_public_start) < 120,
        },
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


@router.post("/start", response_class=HTMLResponse)
def public_start(request: Request):
    """Botón público: SOLO arranca (docker start). Stop/restart siguen en /admin.

    Es seguro exponerlo: idempotente y sin griefing posible. Con cooldown
    para que nadie martille la API de Docker.
    """
    global _last_public_start
    now = time.monotonic()
    wait = int(START_COOLDOWN_S - (now - _last_public_start))
    if wait > 0:
        return templates.TemplateResponse(
            request, "partials/start_button.html",
            {"state": "cooldown", "wait": wait},
        )
    if docker_service.container_status().get("status") == "running":
        return templates.TemplateResponse(
            request, "partials/start_button.html", {"state": "already"},
        )
    _last_public_start = now
    result = docker_service.container_action("start")
    client = request.client.host if request.client else "?"
    log.warning("arranque público del server pedido por %s: %s", client, result)
    if result.get("ok"):
        return templates.TemplateResponse(
            request, "partials/start_button.html", {"state": "starting"},
        )
    return templates.TemplateResponse(
        request, "partials/start_button.html",
        {"state": "error", "detail": result.get("error", "?")},
    )
