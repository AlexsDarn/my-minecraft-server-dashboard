"""Rutas admin protegidas por IP (ver deps.require_admin)."""
import asyncio
import threading
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, Form, Request
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

from app import config
from app.deps import require_admin
from app.services import backup_service, docker_service

router = APIRouter(dependencies=[Depends(require_admin)])
templates = Jinja2Templates(directory="app/templates")


@router.get("/admin", response_class=HTMLResponse)
def admin_page(request: Request):
    return templates.TemplateResponse(
        request, "admin.html", {"backups": backup_service.list_backups()}
    )


@router.post("/admin/action/{action}")
def admin_action(action: str):
    if action not in ("start", "stop", "restart"):
        return {"ok": False, "error": "acción no válida"}
    return docker_service.container_action(action)


@router.post("/admin/command")
def admin_command(command: str = Form(...)):
    command = command.strip()
    if not command:
        return {"ok": False, "error": "comando vacío"}
    return docker_service.exec_rcon(command)


@router.get("/admin/logs/stream")
async def admin_logs_stream():
    """SSE: emite las últimas líneas y luego sigue el log en vivo.

    El iterador de docker-py es bloqueante, así que se bombea desde
    un hilo hacia una cola (nunca en el event loop: lo congelaría
    y ningún otro request respondería).
    """

    async def gen():
        # 1) histórico (sync -> threadpool vía to_thread)
        lines = await asyncio.to_thread(docker_service.log_lines, 100)
        for line in lines:
            yield f"data: {line}\n\n"
        # Si el stream se corta, el navegador reintenta cada 10 s (no cada 3 s)
        yield "retry: 10000\n\n"

        # 2) seguimiento en vivo, bombeado desde un hilo
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue = asyncio.Queue()
        stop = threading.Event()

        def pump():
            try:
                import docker

                client = docker.from_env()
                container = client.containers.get(config.MC_CONTAINER)
                stream = container.logs(stream=True, follow=True, tail=0)
                for raw in stream:
                    if stop.is_set():
                        break
                    text = raw.decode(errors="replace").rstrip()
                    loop.call_soon_threadsafe(queue.put_nowait, text)
            except Exception as e:
                loop.call_soon_threadsafe(
                    queue.put_nowait, f"[error stream: {e}]"
                )
            finally:
                loop.call_soon_threadsafe(queue.put_nowait, None)

        thread = threading.Thread(target=pump, daemon=True)
        thread.start()
        try:
            while True:
                item = await queue.get()
                if item is None:
                    break
                yield f"data: {item}\n\n"
        except asyncio.CancelledError:
            return
        finally:
            stop.set()

    return StreamingResponse(gen(), media_type="text/event-stream")


@router.post("/admin/backup")
def admin_backup(background: BackgroundTasks):
    background.add_task(backup_service.run_backup)
    return {"ok": True, "detail": "backup lanzado en segundo plano"}


@router.get("/admin/backups")
def admin_backups():
    return {"backups": backup_service.list_backups()}


@router.get("/admin/backups/download/{name}")
def admin_backup_download(name: str):
    # Evita path traversal: solo el nombre base dentro del dir de backups.
    safe = Path(name).name
    path = backup_service.backup_dir() / safe
    if not path.is_file():
        return {"ok": False, "error": "no existe"}
    return FileResponse(path, filename=safe)
