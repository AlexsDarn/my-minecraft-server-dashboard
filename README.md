# my-minecraft-server-dashboard

Dashboard web (FastAPI + HTMX) para un servidor Minecraft en Docker.
Público: estado y jugadores (solo lectura). Admin (solo LAN): start/stop,
logs en vivo (SSE), comandos RCON y backups.

## Estructura

```text
minecraft-dashboard/
├── app/
│   ├── main.py              # crea la app, monta static y routers
│   ├── config.py            # settings desde .env
│   ├── deps.py              # restringe /admin por IP
│   ├── routers/
│   │   ├── public.py        # estado y jugadores (solo lectura)
│   │   └── admin.py         # start/stop, logs, comandos, backups
│   ├── services/
│   │   ├── docker_service.py
│   │   ├── status_service.py  # mcstatus
│   │   └── backup_service.py
│   ├── templates/
│   │   ├── base.html
│   │   ├── index.html
│   │   ├── admin.html
│   │   └── partials/        # status.html, players.html (HTMX los refresca)
│   └── static/
│       └── css/input.css, output.css
├── .env.example
├── requirements.txt
└── README.md
```

## Despliegue con Docker (en el server)

```bash
git clone <url> my-minecraft-server-dashboard
cd my-minecraft-server-dashboard
cp -n .env.example .env   # edítalo: MC_CONTAINER, MC_HOST, rutas, ADMIN_ALLOW
docker compose up -d --build
```

Notas:

- `MC_HOST=localhost` **no** funciona desde dentro del contenedor.
  Usa la IP LAN del host o pon el dashboard en la misma red docker
  del Minecraft y usa el nombre del contenedor como `MC_HOST`
  (ver bloque `networks` comentado en `docker-compose.yml`).
- El socket `/var/run/docker.sock` montado le da a la app control
  sobre el contenedor del MC (equivalente a estar en el grupo `docker`).
- Con puertos publicados, la app sigue viendo la IP real del cliente,
  así que `ADMIN_ALLOW` funciona igual.

## Desarrollo local (sin Docker)

```bash
cp -n .env.example .env   # ajusta MC_CONTAINER, rutas, ADMIN_ALLOW
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m uvicorn app.main:app --reload --port 8000
```

- `GET /` → estado + jugadores (HTMX refresca cada 5/10 s)
- `GET /api/status` → JSON con estado del contenedor y del juego
- `GET /admin` → panel admin (403 fuera de `ADMIN_ALLOW`)
- `GET /admin/logs/stream` → logs en vivo (SSE)
- `POST /admin/action/{start,stop,restart}`, `POST /admin/command`,
  `POST /admin/backup`, `GET /admin/backups/download/{name}`

## Notas

- Sin Docker o sin MC a mano, la app responde igual con
  `status: unavailable` / `online: false` (no rompe el dashboard).
- En producción: usuario en el grupo `docker`, servicio systemd con
  `Restart=always`, y `TRUST_PROXY=true` solo si hay proxy delante
  (la IP cliente se lee de `X-Forwarded-For`).
- Tailwind: `base.html` usa el CDN `@tailwindcss/browser` para dev;
  para prod compila con el CLI standalone:
  `tailwindcss -i app/static/css/input.css -o app/static/css/output.css --minify`
