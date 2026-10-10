"""OpenAI tool-calling schemas for GLPI read operations."""

from typing import Any, Dict

GLPI_STATUS_SCHEMA: Dict[str, Any] = {
    "name": "glpi_status",
    "description": "Check GLPI OAuth and real read-only ticket API access.",
    "parameters": {"type": "object", "properties": {}, "required": []},
}
GLPI_FIND_TICKETS_SCHEMA: Dict[str, Any] = {
    "name": "glpi_find_tickets",
    "description": "Search a bounded recent GLPI ticket set without modifying GLPI.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Text contained in ticket data."},
            "ticket_id": {"type": "integer", "description": "Exact ticket ID."},
            "status": {"type": "string", "description": "Optional status text."},
            "priority": {"type": "string", "description": "Optional priority text."},
            "limit": {"type": "integer", "default": 20, "description": "1-100."},
        },
        "required": [],
    },
}
GLPI_GET_TICKET_SCHEMA: Dict[str, Any] = {
    "name": "glpi_get_ticket",
    "description": "Get one GLPI ticket by ID using GET only.",
    "parameters": {
        "type": "object",
        "properties": {"ticket_id": {"type": "integer"}},
        "required": ["ticket_id"],
    },
}
GLPI_GET_FOLLOWUPS_SCHEMA: Dict[str, Any] = {
    "name": "glpi_get_ticket_followups",
    "description": "Read ticket followups without adding or changing followups.",
    "parameters": {
        "type": "object",
        "properties": {
            "ticket_id": {"type": "integer"},
            "limit": {"type": "integer", "default": 20, "description": "1-100."},
        },
        "required": ["ticket_id"],
    },
}
GLPI_FIND_OPEN_ASSET_SCHEMA: Dict[str, Any] = {
    "name": "glpi_find_open_ticket_for_asset",
    "description": "Find open tickets mentioning a device name or IP address using GET only.",
    "parameters": {
        "type": "object",
        "properties": {
            "asset_name": {"type": "string"},
            "ip_address": {"type": "string"},
            "limit": {"type": "integer", "default": 20, "description": "1-100."},
        },
        "required": [],
    },
}
