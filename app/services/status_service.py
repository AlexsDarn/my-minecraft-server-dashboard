"""Estado del servidor Minecraft vía mcstatus (query Java Edition)."""
from __future__ import annotations

import re

from app import config

# Códigos de formato del juego (§a, §l, §r...) que si no se ven crudos en la web
FORMAT_RE = re.compile(r"§.")


def _clean(text: object) -> str:
    return FORMAT_RE.sub("", str(text)).strip()


def query_status(
    host: str | None = None, port: int | None = None, timeout: float | None = None
) -> dict:
    """Nunca lanza excepción; devuelve dict serializable."""
    host = host or config.MC_HOST
    port = port or config.MC_PORT
    timeout = timeout if timeout is not None else config.MC_TIMEOUT
    try:
        from mcstatus import JavaServer

        server = JavaServer(host, port, timeout=timeout)
        status = server.status()
        players = [
            {"name": _clean(p.name), "id": str(p.id)}
            for p in (status.players.sample or [])
        ]
        mods: list[dict] = []
        mods_truncated = False
        forge = getattr(status, "forge_data", None)
        if forge is not None:
            try:
                mods = [
                    {"id": _clean(m.name), "version": _clean(m.marker)}
                    for m in (forge.mods or [])
                ]
                mods_truncated = bool(getattr(forge, "truncated", False))
            except Exception:
                mods = []
        return {
            "online": True,
            "latency_ms": round(status.latency, 1),
            "version": _clean(status.version.name),
            "motd": _clean(status.description),
            "players_online": status.players.online,
            "players_max": status.players.max,
            "players": players,
            "is_modded": bool(getattr(status, "is_modded", bool(mods))),
            "mods": sorted(mods, key=lambda m: m["id"].lower()),
            "mods_truncated": mods_truncated,
        }
    except Exception as e:
        return {
            "online": False,
            "latency_ms": None,
            "version": None,
            "motd": None,
            "players_online": 0,
            "players_max": 0,
            "players": [],
            "is_modded": False,
            "mods": [],
            "mods_truncated": False,
            "error": str(e),
        }
