"""Client IP resolution (trusting X-Forwarded-For only from configured proxies) and CIDR allowlist."""

import ipaddress

from fastapi import Request

from app.config import get_settings


def _split(value: str) -> list[str]:
    return [p.strip() for p in value.split(",") if p.strip()]


def client_ip(request: Request) -> str:
    peer = request.client.host if request.client else "0.0.0.0"
    trusted = _split(get_settings().trusted_proxies)
    if peer not in trusted:
        return peer
    xff = request.headers.get("x-forwarded-for", "")
    hops = _split(xff)
    # Walk from the right, skipping trusted proxies; first untrusted hop is the client.
    for hop in reversed(hops):
        if hop not in trusted:
            return hop
    return peer


def ip_allowed(ip: str) -> bool:
    cidrs = _split(get_settings().login_allow_cidrs)
    if not cidrs:
        return True
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return any(addr in ipaddress.ip_network(c, strict=False) for c in cidrs)


def request_is_https(request: Request) -> bool:
    peer = request.client.host if request.client else ""
    if peer in _split(get_settings().trusted_proxies):
        return request.headers.get("x-forwarded-proto", request.url.scheme) == "https"
    return request.url.scheme == "https"
