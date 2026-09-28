"""Backups: save-all flush + tar del volumen de datos."""
from __future__ import annotations

import datetime as dt
import tarfile
from pathlib import Path

from app import config
from app.services import docker_service


def backup_dir() -> Path:
    p = Path(config.MC_BACKUP_DIR)
    p.mkdir(parents=True, exist_ok=True)
    return p


def list_backups() -> list[dict]:
    d = backup_dir()
    files = sorted(d.glob("*.tar.gz"), key=lambda f: f.stat().st_mtime, reverse=True)
    return [
        {
            "name": f.name,
            "size_mb": round(f.stat().st_size / 1024 / 1024, 1),
            "modified": dt.datetime.fromtimestamp(
                f.stat().st_mtime
            ).isoformat(timespec="seconds"),
        }
        for f in files
    ]


def run_backup() -> dict:
    """Sync y pesado: llamar desde BackgroundTask. Devuelve dict con ok."""
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = backup_dir() / f"mc-backup-{stamp}.tar.gz"
    src = Path(config.MC_DATA_DIR)
    if not src.is_dir():
        return {"ok": False, "error": f"MC_DATA_DIR no existe: {src}"}
    # flush del mundo antes de comprimir
    try:
        docker_service.exec_rcon("save-all flush")
    except Exception:
        pass
    try:
        with tarfile.open(dest, "w:gz") as tar:
            tar.add(src, arcname="data")
        return {"ok": True, "file": dest.name}
    except Exception as e:
        return {"ok": False, "error": str(e)}
