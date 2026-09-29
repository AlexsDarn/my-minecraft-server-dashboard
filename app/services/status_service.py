"""Estado del servidor Minecraft vía mcstatus (query Java Edition)."""
from __future__ import annotations

from app import config


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
            {"name": p.name, "id": str(p.id)}
            for p in (status.players.sample or [])
        ]
        return {
            "online": True,
            "latency_ms": round(status.latency, 1),
            "version": status.version.name,
            "motd": str(status.description),
            "players_online": status.players.online,
            "players_max": status.players.max,
            "players": players,
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
            "error": str(e),
        }
