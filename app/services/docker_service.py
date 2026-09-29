"""Acceso a Docker con docker-py. Funciones sync (FastAPI las corre en threadpool)."""
from __future__ import annotations

import re
import subprocess
from functools import lru_cache

from app import config

# Secuencias de color ANSI (las emite rcon-cli y a veces el log del server)
ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")


def strip_ansi(text: str) -> str:
    return ANSI_RE.sub("", text)


def _client():
    try:
        import docker

        return docker.from_env()
    except Exception:
        return None


@lru_cache(maxsize=1)
def _cli_available() -> bool:
    try:
        subprocess.run(
            ["docker", "ps"], capture_output=True, timeout=5, check=False
        )
        return True
    except Exception:
        return False


def container_status(name: str | None = None) -> dict:
    """Devuelve estado del contenedor. Nunca lanza excepción."""
    name = name or config.MC_CONTAINER
    client = _client()
    if client is None:
        return {"name": name, "status": "unavailable", "detail": "docker-py no disponible"}
    try:
        c = client.containers.get(name)
        c.reload()
        return {"name": name, "status": c.status, "detail": c.status}
    except Exception as e:
        return {"name": name, "status": "not_found", "detail": str(e)}


def container_action(action: str, name: str | None = None) -> dict:
    """start / stop / restart. Devuelve dict con ok o error."""
    name = name or config.MC_CONTAINER
    client = _client()
    if client is None:
        return {"ok": False, "error": "docker no disponible"}
    try:
        c = client.containers.get(name)
        if action == "start":
            c.start()
        elif action == "stop":
            c.stop(timeout=30)
        elif action == "restart":
            c.restart(timeout=30)
        else:
            return {"ok": False, "error": f"acción desconocida: {action}"}
        return {"ok": True, "action": action}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def exec_rcon(command: str) -> dict:
    """Ejecuta un comando vía rcon-cli dentro del contenedor (sin exponer RCON)."""
    client = _client()
    if client is None:
        return {"ok": False, "error": "docker no disponible"}
    try:
        c = client.containers.get(config.MC_CONTAINER)
        code, out = c.exec_run([config.RCON_CMD, command])
        text = out.decode(errors="replace") if isinstance(out, bytes) else str(out)
        text = strip_ansi(text).replace("\r\n", "\n").replace("\r", "\n").strip()
        return {"ok": code == 0, "output": text}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def log_lines(tail: int = 100) -> list[str]:
    """Últimas N líneas del log (no streaming)."""
    client = _client()
    if client is None:
        return ["docker no disponible"]
    try:
        c = client.containers.get(config.MC_CONTAINER)
        raw = c.logs(tail=tail).decode(errors="replace")
        return [strip_ansi(line) for line in raw.splitlines()[-tail:]]
    except Exception as e:
        return [f"error leyendo logs: {e}"]
