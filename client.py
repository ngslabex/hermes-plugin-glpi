"""Synchronous, read-only GLPI 12 High-Level API client.

The only POST is OAuth token acquisition. Resource requests are GET-only.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Iterable, List, Optional


class GLPIError(RuntimeError):
    """Safe GLPI error which never embeds credentials."""


_TOKEN_CACHE: Dict[str, Any] = {"access_token": None, "expires_at": 0.0}


def _required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise GLPIError(f"{name} is not set")
    return value


def base_url() -> str:
    return _required("GLPI_URL").rstrip("/")


def api_prefix() -> str:
    value = os.environ.get("GLPI_API_PREFIX", "/api.php/v2.2").strip()
    if not value.startswith("/"):
        value = "/" + value
    return value.rstrip("/")


def timeout() -> float:
    try:
        return max(1.0, float(os.environ.get("GLPI_TIMEOUT", "30")))
    except ValueError as exc:
        raise GLPIError("GLPI_TIMEOUT must be numeric") from exc


def verify_ssl() -> bool:
    return os.environ.get("GLPI_VERIFY_SSL", "true").strip().lower() not in {
        "0", "false", "no", "off"
    }


def _ssl_context():
    if verify_ssl():
        return None
    import ssl
    return ssl._create_unverified_context()  # noqa: SLF001


def _decode_json(raw: bytes, context: str) -> Any:
    text = raw.decode("utf-8", errors="replace")
    if not text.strip():
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise GLPIError(f"{context} returned non-JSON: {text[:300]}") from exc


def _http_error(exc: urllib.error.HTTPError, method: str, path: str) -> GLPIError:
    body = exc.read().decode("utf-8", errors="replace")
    try:
        data = json.loads(body)
        detail = (
            data.get("error_description")
            or data.get("detail")
            or data.get("message")
            or data.get("error")
            or body
        )
    except (json.JSONDecodeError, AttributeError):
        detail = body
    return GLPIError(f"GLPI API {method} {path} -> HTTP {exc.code}: {str(detail)[:300]}")


def get_access_token(force_refresh: bool = False) -> str:
    """Get and cache an OAuth2 Password-grant token."""
    now = time.time()
    cached = _TOKEN_CACHE.get("access_token")
    if not force_refresh and cached and now < float(_TOKEN_CACHE["expires_at"]) - 60:
        return str(cached)

    path = "/api.php/token"
    payload = urllib.parse.urlencode(
        {
            "grant_type": "password",
            "client_id": _required("GLPI_CLIENT_ID"),
            "client_secret": _required("GLPI_CLIENT_SECRET"),
            "username": _required("GLPI_USERNAME"),
            "password": _required("GLPI_PASSWORD"),
            "scope": os.environ.get("GLPI_SCOPE", "api").strip() or "api",
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        base_url() + path,
        data=payload,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "hermes-plugin-glpi/0.1.2",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout(), context=_ssl_context()) as response:
            data = _decode_json(response.read(), "GLPI OAuth token endpoint")
    except urllib.error.HTTPError as exc:
        raise _http_error(exc, "POST", path) from exc
    except urllib.error.URLError as exc:
        raise GLPIError(f"GLPI OAuth connection failed: {exc.reason}") from exc

    token = data.get("access_token") if isinstance(data, dict) else None
    if not token:
        raise GLPIError("GLPI OAuth response did not include access_token")
    try:
        expires_in = int(data.get("expires_in", 3600))
    except (TypeError, ValueError):
        expires_in = 3600
    _TOKEN_CACHE.update({"access_token": token, "expires_at": now + max(60, expires_in)})
    return str(token)


def request_get(path: str, params: Optional[Dict[str, Any]] = None, *, retry_auth: bool = True) -> Any:
    """Perform one authenticated resource GET."""
    if not path.startswith("/"):
        path = "/" + path
    url = base_url() + path
    if params:
        clean = {key: value for key, value in params.items() if value is not None}
        url += "?" + urllib.parse.urlencode(clean, doseq=True)
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {get_access_token()}",
            "User-Agent": "hermes-plugin-glpi/0.1.2",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout(), context=_ssl_context()) as response:
            return _decode_json(response.read(), f"GLPI GET {path}")
    except urllib.error.HTTPError as exc:
        if exc.code == 401 and retry_auth:
            exc.close()
            get_access_token(force_refresh=True)
            return request_get(path, params, retry_auth=False)
        raise _http_error(exc, "GET", path) from exc
    except urllib.error.URLError as exc:
        raise GLPIError(f"GLPI API connection failed: {exc.reason}") from exc


def endpoint(resource: str) -> str:
    return f"{api_prefix()}/{resource.lstrip('/')}"


def ticket_endpoint(ticket_id: Optional[int] = None) -> str:
    path = endpoint("Assistance/Ticket")
    return f"{path}/{int(ticket_id)}" if ticket_id is not None else path


def normalize_collection(data: Any) -> List[Dict[str, Any]]:
    """Normalize common GLPI collection envelopes."""
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if not isinstance(data, dict):
        return []
    for key in ("data", "items", "results", "content"):
        value = data.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    if data.get("id") is not None:
        return [data]
    return []


def first_value(item: Dict[str, Any], names: Iterable[str], default: Any = None) -> Any:
    for name in names:
        if name in item and item[name] not in (None, ""):
            return item[name]
    return default
