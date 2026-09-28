"""Dependencia que restringe /admin a la LAN / localhost."""
import ipaddress

from fastapi import Header, HTTPException, Request

from app import config


def _allowed_networks() -> list[ipaddress._BaseNetwork]:
    nets: list[ipaddress._BaseNetwork] = []
    for part in config.ADMIN_ALLOW.split(","):
        part = part.strip()
        if part:
            nets.append(ipaddress.ip_network(part, strict=False))
    return nets


def _client_ip(request: Request, x_forwarded_for: str | None) -> str:
    if config.TRUST_PROXY and x_forwarded_for:
        # El primer valor es el cliente original.
        return x_forwarded_for.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "127.0.0.1"


async def require_admin(
    request: Request,
    x_forwarded_for: str | None = Header(default=None, alias="X-Forwarded-For"),
) -> None:
    ip_raw = _client_ip(request, x_forwarded_for)
    try:
        ip = ipaddress.ip_address(ip_raw)
    except ValueError:
        raise HTTPException(status_code=403, detail="IP no válida")
    if not any(ip in net for net in _allowed_networks()):
        raise HTTPException(status_code=403, detail="Solo red local")
