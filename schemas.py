"""OpenAI-style tool schemas exposed by the GLPI plugin."""

from typing import Any, Dict

GLPI_STATUS_SCHEMA: Dict[str, Any] = {
    "name": "glpi_status",
    "description": "Check GLPI OAuth and read-only High-Level API connectivity.",
    "parameters": {"type": "object", "properties": {}, "required": []},
}

GLPI_FIND_TICKETS_SCHEMA: Dict[str, Any] = {
    "name": "glpi_find_tickets",
    "description": (
        "Search GLPI tickets read-only. Filters may include free text, exact ticket "
        "ID, status text, priority text, asset name, or IP address."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Text to find in ticket data."},
            "ticket_id": {"type": "integer", "description": "Exact GLPI ticket ID."},
            "status": {"type": "string", "description": "Optional status text filter."},
            "priority": {"type": "string", "description": "Optional priority text filter."},
            "limit": {
                "type": "integer",
                "description": "Maximum tickets returned (1-100, default 20).",
                "default": 20,
            },
        },
        "required": [],
    },
}

GLPI_GET_TICKET_SCHEMA: Dict[str, Any] = {
    "name": "glpi_get_ticket",
    "description": "Get one GLPI ticket by ID using a read-only request.",
    "parameters": {
        "type": "object",
        "properties": {"ticket_id": {"type": "integer"}},
        "required": ["ticket_id"],
    },
}

GLPI_GET_FOLLOWUPS_SCHEMA: Dict[str, Any] = {
    "name": "glpi_get_ticket_followups",
    "description": "Read followups for one GLPI ticket. Never adds or changes followups.",
    "parameters": {
        "type": "object",
        "properties": {
            "ticket_id": {"type": "integer"},
            "limit": {"type": "integer", "default": 20},
        },
        "required": ["ticket_id"],
    },
}

GLPI_FIND_OPEN_ASSET_SCHEMA: Dict[str, Any] = {
    "name": "glpi_find_open_ticket_for_asset",
    "description": (
        "Find read-only open GLPI tickets mentioning a device name or IP address. "
        "Useful for correlating Zabbix alarms and NetBox devices with existing tickets."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "asset_name": {"type": "string"},
            "ip_address": {"type": "string"},
            "limit": {"type": "integer", "default": 20},
        },
        "required": [],
    },
}
