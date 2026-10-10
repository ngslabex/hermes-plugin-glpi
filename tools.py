"""Hermes handlers for read-only GLPI 12 operations."""

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

DEFAULT_SCAN_LIMIT = 300
PAGE_SIZE = 100
MAX_PAGES = 10


def _available() -> bool:
    """Return True when all mandatory GLPI environment variables exist."""
    return all(
        os.environ.get(name)
        for name in (
            "GLPI_URL",
            "GLPI_CLIENT_ID",
            "GLPI_CLIENT_SECRET",
            "GLPI_USERNAME",
            "GLPI_PASSWORD",
        )
    )


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, default=str)


def _safe_limit(args: Dict[str, Any], default: int = 20) -> int:
    """Validate the number of results returned to Hermes."""
    try:
        return max(1, min(100, int(args.get("limit") or default)))
    except (TypeError, ValueError) as exc:
        raise GLPIError("limit must be an integer") from exc


def _text_blob(item: Dict[str, Any]) -> str:
    """Create a case-insensitive searchable representation of a ticket."""
    return json.dumps(item, ensure_ascii=False, default=str).lower()


def _scalar(value: Any) -> Any:
    """Return the most useful display value from a nested GLPI field."""
    if isinstance(value, dict):
        return first_value(value, ("name", "label", "value", "id"), value)
    return value


def _ticket_summary(item: Dict[str, Any]) -> Dict[str, Any]:
    """Return a compact ticket representation without the unrestricted raw payload."""
    return {
        "id": first_value(item, ("id", "ID")),
        "name": first_value(item, ("name", "title", "subject")),
        "status": _scalar(
            first_value(item, ("status", "status_name", "statusLabel"))
        ),
        "priority": _scalar(
            first_value(item, ("priority", "priority_name", "priorityLabel"))
        ),
        "urgency": _scalar(
            first_value(item, ("urgency", "urgency_name"))
        ),
        "entity": _scalar(
            first_value(item, ("entity", "entities_id", "entity_name"))
        ),
        "category": _scalar(
            first_value(
                item,
                ("category", "itilcategories_id", "category_name"),
            )
        ),
        "date": first_value(item, ("date", "created_at", "date_creation")),
        "date_mod": first_value(
            item,
            ("date_mod", "updated_at", "date_update"),
        ),
        "content": first_value(item, ("content", "description")),
    }


def _looks_open(item: Dict[str, Any]) -> bool:
    """Return False for known solved or closed GLPI ticket states."""
    value = str(
        _scalar(
            first_value(
                item,
                ("status", "status_name", "statusLabel"),
                "",
            )
        )
    ).lower()

    if not value:
        return True

    closed_words = (
        "closed",
        "solved",
        "resolved",
        "clos",
        "résolu",
        "çözüldü",
        "kapalı",
    )

    if any(word in value for word in closed_words):
        return False

    # Common GLPI numeric states: 5=solved, 6=closed.
    return value not in {"5", "6"}


def _matches(item: Dict[str, Any], terms: Iterable[str]) -> bool:
    """Return True when every non-empty search term exists in the ticket payload."""
    blob = _text_blob(item)
    return all(term.lower() in blob for term in terms if term)


def _fetch_recent(
    scan_limit: int = DEFAULT_SCAN_LIMIT,
) -> List[Dict[str, Any]]:
    """Read recently updated visible GLPI tickets with bounded pagination.

    Results are deduplicated by ticket ID. If the server ignores the ``start``
    offset and repeats a page, the function raises an explicit error instead of
    silently returning duplicated or misleading data.
    """
    try:
        scan_limit = int(scan_limit)
    except (TypeError, ValueError) as exc:
        raise GLPIError("scan_limit must be an integer") from exc

    scan_limit = max(1, min(scan_limit, PAGE_SIZE * MAX_PAGES))

    tickets: List[Dict[str, Any]] = []
    seen_keys = set()
    start = 0
    page_count = 0

    while len(tickets) < scan_limit and page_count < MAX_PAGES:
        current_limit = min(PAGE_SIZE, scan_limit - len(tickets))

        data = request_get(
            ticket_endpoint(),
            {
                "start": start,
                "limit": current_limit,
                "sort": "date_mod:desc",
            },
        )

        page = normalize_collection(data)

        if not page:
            break

        new_items = 0

        for item in page:
            ticket_id = first_value(item, ("id", "ID"))
            dedupe_key = (
                f"id:{ticket_id}"
                if ticket_id is not None
                else f"payload:{_text_blob(item)}"
            )

            if dedupe_key in seen_keys:
                continue

            seen_keys.add(dedupe_key)
            tickets.append(item)
            new_items += 1

            if len(tickets) >= scan_limit:
                break

        page_count += 1

        if len(page) < current_limit:
            break

        if new_items == 0:
            raise GLPIError(
                "GLPI pagination did not advance; "
                "the server returned a duplicate ticket page"
            )

        start += len(page)

    return tickets


def handle_glpi_status(args: Dict[str, Any], **_) -> str:
    """Validate OAuth and real read-only ticket API access."""
    try:
        token = get_access_token()
        probe = request_get(
            ticket_endpoint(),
            {
                "start": 0,
                "limit": 1,
                "sort": "date_mod:desc",
            },
        )
        tickets = normalize_collection(probe)

        return _json(
            {
                "ok": True,
                "base_url": base_url(),
                "api_prefix": api_prefix(),
                "oauth_access_token_present": bool(token),
                "ticket_api_accessible": True,
                "probe_ticket_count": len(tickets),
                "mode": "read_only",
            }
        )
    except Exception as exc:
        return _json(
            {
                "ok": False,
                "error": str(exc),
                "mode": "read_only",
            }
        )


def handle_glpi_find_tickets(args: Dict[str, Any], **_) -> str:
    """Find tickets in a bounded, paginated read-only ticket set."""
    try:
        limit = _safe_limit(args)

        if args.get("ticket_id") is not None:
            items = normalize_collection(
                request_get(ticket_endpoint(int(args["ticket_id"])))
            )
        else:
            items = _fetch_recent()

        terms = [str(args.get("query") or "").strip()]

        for key in ("status", "priority"):
            value = str(args.get(key) or "").strip()
            if value:
                terms.append(value)

        matched = [item for item in items if _matches(item, terms)]
        returned = matched[:limit]

        return _json(
            {
                "scanned": len(items),
                "matched": len(matched),
                "count": len(returned),
                "tickets": [_ticket_summary(item) for item in returned],
                "read_only": True,
            }
        )
    except Exception as exc:
        return _json(
            {
                "error": str(exc),
                "read_only": True,
            }
        )


def handle_glpi_get_ticket(args: Dict[str, Any], **_) -> str:
    """Retrieve one GLPI ticket by ID using GET only."""
    try:
        ticket_id = int(args["ticket_id"])
        items = normalize_collection(request_get(ticket_endpoint(ticket_id)))

        if not items:
            return _json(
                {
                    "error": f"Ticket {ticket_id} was not found",
                    "read_only": True,
                }
            )

        return _json(
            {
                "ticket": _ticket_summary(items[0]),
                "read_only": True,
            }
        )
    except Exception as exc:
        return _json(
            {
                "error": str(exc),
                "read_only": True,
            }
        )


def handle_glpi_get_ticket_followups(args: Dict[str, Any], **_) -> str:
    """Read ticket timeline or followup records without modifying GLPI."""
    try:
        ticket_id = int(args["ticket_id"])
        limit = _safe_limit(args)

        candidates = (
            endpoint(f"Assistance/Ticket/{ticket_id}/Timeline"),
            endpoint(f"Assistance/Ticket/{ticket_id}/ITILFollowup"),
            endpoint(f"Assistance/Ticket/{ticket_id}/Followup"),
            endpoint("Assistance/ITILFollowup"),
        )

        errors: List[str] = []

        for path in candidates:
            try:
                params: Dict[str, Any] = {
                    "start": 0,
                    "limit": limit,
                }

                if (
                    path.endswith("ITILFollowup")
                    and f"/{ticket_id}/" not in path
                ):
                    params["filter"] = f"items_id=={ticket_id}"

                items = normalize_collection(request_get(path, params))

                if items or f"/{ticket_id}/" in path:
                    returned = items[:limit]
                    return _json(
                        {
                            "ticket_id": ticket_id,
                            "count": len(returned),
                            "timeline_entries": returned,
                            "endpoint": path,
                            "read_only": True,
                        }
                    )
            except GLPIError as exc:
                errors.append(str(exc))

        return _json(
            {
                "ticket_id": ticket_id,
                "error": "No supported timeline or followup endpoint was available",
                "attempts": errors,
                "read_only": True,
            }
        )
    except Exception as exc:
        return _json(
            {
                "error": str(exc),
                "read_only": True,
            }
        )


def handle_glpi_find_open_ticket_for_asset(
    args: Dict[str, Any],
    **_,
) -> str:
    """Find open tickets containing a device name or IP address."""
    try:
        asset = str(args.get("asset_name") or "").strip()
        ip_address = str(args.get("ip_address") or "").strip()

        if not asset and not ip_address:
            raise GLPIError("asset_name or ip_address is required")

        limit = _safe_limit(args)
        items = _fetch_recent()
        terms = [term for term in (asset, ip_address) if term]
        open_items = [item for item in items if _looks_open(item)]

        # Prefer tickets containing all provided identifiers.
        matched = [
            item
            for item in open_items
            if _matches(item, terms)
        ]
        match_mode = "all_terms"

        # If device and IP do not occur together, accept either identifier.
        if not matched and len(terms) > 1:
            matched = [
                item
                for item in open_items
                if any(
                    term.lower() in _text_blob(item)
                    for term in terms
                )
            ]
            match_mode = "any_term"

        returned = matched[:limit]

        return _json(
            {
                "asset_name": asset or None,
                "ip_address": ip_address or None,
                "scanned": len(items),
                "open_scanned": len(open_items),
                "match_mode": match_mode,
                "matched": len(matched),
                "count": len(returned),
                "tickets": [_ticket_summary(item) for item in returned],
                "read_only": True,
            }
        )
    except Exception as exc:
        return _json(
            {
                "error": str(exc),
                "read_only": True,
            }
        )


TOOL_DEFINITIONS = [
    (GLPI_STATUS_SCHEMA, handle_glpi_status, _available),
    (GLPI_FIND_TICKETS_SCHEMA, handle_glpi_find_tickets, _available),
    (GLPI_GET_TICKET_SCHEMA, handle_glpi_get_ticket, _available),
    (GLPI_GET_FOLLOWUPS_SCHEMA, handle_glpi_get_ticket_followups, _available),
    (
        GLPI_FIND_OPEN_ASSET_SCHEMA,
        handle_glpi_find_open_ticket_for_asset,
        _available,
    ),
]
