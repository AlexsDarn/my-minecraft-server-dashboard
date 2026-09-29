"""Settings cargados desde .env con valores por defecto sensatos."""
import os

from dotenv import load_dotenv

load_dotenv()


def _get(name: str, default: str) -> str:
    return os.getenv(name, default)


MC_CONTAINER: str = _get("MC_CONTAINER", "maincra2")
MC_HOST: str = _get("MC_HOST", "localhost")
MC_PORT: int = int(_get("MC_PORT", "25565"))
MC_TIMEOUT: float = float(_get("MC_TIMEOUT", "2"))
MC_DATA_DIR: str = _get("MC_DATA_DIR", "/opt/minecraft/data")
MC_BACKUP_DIR: str = _get("MC_BACKUP_DIR", "/opt/minecraft/backups")
RCON_CMD: str = _get("RCON_CMD", "rcon-cli")
ADMIN_ALLOW: str = _get(
    "ADMIN_ALLOW", "127.0.0.1/32,::1/128,192.168.0.0/16,10.0.0.0/8,100.64.0.0/10"
)
TRUST_PROXY: bool = _get("TRUST_PROXY", "false").lower() in ("1", "true", "yes")
