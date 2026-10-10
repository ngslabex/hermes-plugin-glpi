"""Read-only Hermes tool handlers for GLPI 12."""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Iterable, List

from .client import (
    GLPIError,
    api_prefix,
    base_url,
    endpoint,
    first_value,
    get_access_token,
    normalize_collection,
    request_get,
    ticket_endpoint,
)
from .schemas import (
    GLPI_FIND_OPEN_ASSET_SCHEMA,
    GLPI_FIND_TICKETS_SCHEMA,
    GLPI_GET_FOLLOWUPS_SCHEMA,
    GLPI_GET_TICKET_SCHEMA,
    GLPI_STATUS_SCHEMA,
)


def _available() -> bool:
    required = (
        "GLPI_URL",
        "GLPI_CLIENT_ID",
        "GLPI_CLIENT_SECRET",
        "GLPI_USERNAME",
        "GLPI_PASSWORD",
    )
    return all(os.environ.get(name) for name in required)


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, default=str)


def _safe_limit(args: Dict[str, Any], default: int = 20) -> int:
    try:
        return max(1, min(100, int(args.get("limit") or default)))
    except (TypeError, ValueError) as exc:
        raise GLPIError("limit must be an integer") from exc


def _text_blob(item: Dict[str, Any]) -> str:
    return json.dumps(item, ensure_ascii=False, default=str).lower()


def _scalar(value: Any) -> Any:
    if isinstance(value, dict):
        return first_value(value, ("name", "label", "value", "id"), value)
    return value


def _ticket_summary(item: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": first_value(item, ("id", "ID")),
        "name": first_value(item, ("name", "title", "subject")),
        "status": _scalar(first_value(item, ("status", "status_name", "statusLabel"))),
        "priority": _scalar(first_value(item, ("priority", "priority_name", "priorityLabel"))),
        "urgency": _scalar(first_value(item, ("urgency", "urgency_name"))),
        "entity": _scalar(first_value(item, ("entity", "entities_id", "entity_name"))),
        "category": _scalar(first_value(item, ("category", "itilcategories_id", "category_name"))),
        "date": first_value(item, ("date", "created_at", "date_creation")),
        "date_mod": first_value(item, ("date_mod", "updated_at", "date_update")),
        "content": first_value(item, ("content", "description")),
        "raw": item,
    }


def _looks_open(item: Dict[str, Any]) -> bool:
    value = str(_scalar(first_value(item, ("status", "status_name", "statusLabel"), ""))).lower()
    if not value:
        return True
    closed_words = ("closed", "solved", "resolved", "clos", "résolu", "çözüldü", "kapalı")
    if any(word in value for word in closed_words):
        return False
    # Common GLPI legacy numeric statuses: 5 solved, 6 closed.
    return value not in {"5", "6"}


def _matches(item: Dict[str, Any], terms: Iterable[str]) -> bool:
    blob = _text_blob(item)
    return all(term.lower() in blob for term in terms if term)


def _fetch_recent(limit: int) -> List[Dict[str, Any]]:
    # High-Level API versions can differ slightly in pagination envelopes.
    data = request_get(ticket_endpoint(), {"page": 1, "limit": min(100, max(limit, 50))})
    return normalize_collection(data)


def handle_glpi_status(args: Dict[str, Any], **_) -> str:
    try:
        token = get_access_token()
        result: Dict[str, Any] = {
            "ok": True,
            "base_url": base_url(),
            "api_prefix": api_prefix(),
            "oauth_access_token_present": bool(token),
            "mode": "read_only",
        }
        try:
            status_data = request_get(endpoint("Status"))
            result["status"] = status_data
        except GLPIError as exc:
            # OAuth success is useful even if the optional status route/scope is absent.
            result["status_endpoint_warning"] = str(exc)
        return _json(result)
    except Exception as exc:
        return _json({"ok": False, "error": str(exc)})


def handle_glpi_find_tickets(args: Dict[str, Any], **_) -> str:
    try:
        limit = _safe_limit(args)
        ticket_id = args.get("ticket_id")
        if ticket_id is not None:
            data = request_get(ticket_endpoint(int(ticket_id)))
            items = normalize_collection(data)
        else:
            items = _fetch_recent(limit)

        terms = [str(args.get("query") or "").strip()]
        status = str(args.get("status") or "").strip()
        priority = str(args.get("priority") or "").strip()
        if status:
            terms.append(status)
        if priority:
            terms.append(priority)
        filtered = [item for item in items if _matches(item, terms)]
        return _json(
            {
                "count": len(filtered[:limit]),
                "tickets": [_ticket_summary(item) for item in filtered[:limit]],
                "read_only": True,
            }
        )
    except Exception as exc:
        return _json({"error": str(exc), "read_only": True})


def handle_glpi_get_ticket(args: Dict[str, Any], **_) -> str:
    try:
        ticket_id = int(args["ticket_id"])
        data = request_get(ticket_endpoint(ticket_id))
        items = normalize_collection(data)
        if not items:
            return _json({"error": f"Ticket {ticket_id} was not found"})
        return _json(_ticket_summary(items[0]))
    except Exception as exc:
        return _json({"error": str(exc), "read_only": True})


def handle_glpi_get_ticket_followups(args: Dict[str, Any], **_) -> str:
    try:
        ticket_id = int(args["ticket_id"])
        limit = _safe_limit(args)
        candidates = (
            endpoint(f"Assistance/Ticket/{ticket_id}/ITILFollowup"),
            endpoint(f"Assistance/Ticket/{ticket_id}/Followup"),
            endpoint(f"Assistance/ITILFollowup"),
        )
        errors: List[str] = []
        for path in candidates:
            try:
                params = {"page": 1, "limit": limit}
                if path.endswith("ITILFollowup") and f"/{ticket_id}/" not in path:
                    params["filter"] = f"items_id=={ticket_id}"
                data = request_get(path, params)
                items = normalize_collection(data)
                if items or f"/{ticket_id}/" in path:
                    return _json(
                        {
                            "ticket_id": ticket_id,
                            "count": len(items[:limit]),
                            "followups": items[:limit],
                            "endpoint": path,
                            "read_only": True,
                        }
                    )
            except GLPIError as exc:
                errors.append(str(exc))
        return _json(
            {
                "ticket_id": ticket_id,
                "error": "No supported followup endpoint was available",
                "attempts": errors,
                "read_only": True,
            }
        )
    except Exception as exc:
        return _json({"error": str(exc), "read_only": True})


def handle_glpi_find_open_ticket_for_asset(args: Dict[str, Any], **_) -> str:
    try:
        asset = str(args.get("asset_name") or "").strip()
        ip_address = str(args.get("ip_address") or "").strip()
        if not asset and not ip_address:
            raise GLPIError("asset_name or ip_address is required")
        limit = _safe_limit(args)
        items = _fetch_recent(max(limit, 50))
        terms = [term for term in (asset, ip_address) if term]
        matched = [item for item in items if _looks_open(item) and _matches(item, terms)]
        # If both terms were supplied but no ticket contains both, return union matches.
        if not matched and len(terms) > 1:
            matched = [
                item for item in items
                if _looks_open(item) and any(term.lower() in _text_blob(item) for term in terms)
            ]
        return _json(
            {
                "asset_name": asset or None,
                "ip_address": ip_address or None,
                "count": len(matched[:limit]),
                "tickets": [_ticket_summary(item) for item in matched[:limit]],
                "read_only": True,
            }
        )
    except Exception as exc:
        return _json({"error": str(exc), "read_only": True})


TOOL_DEFINITIONS = [
    (GLPI_STATUS_SCHEMA, handle_glpi_status, _available),
    (GLPI_FIND_TICKETS_SCHEMA, handle_glpi_find_tickets, _available),
    (GLPI_GET_TICKET_SCHEMA, handle_glpi_get_ticket, _available),
    (GLPI_GET_FOLLOWUPS_SCHEMA, handle_glpi_get_ticket_followups, _available),
    (GLPI_FIND_OPEN_ASSET_SCHEMA, handle_glpi_find_open_ticket_for_asset, _available),
]
