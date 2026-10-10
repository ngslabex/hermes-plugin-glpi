"""Hermes Agent entry point for the read-only GLPI tools plugin."""

from __future__ import annotations

_TOOLSET = "glpi"
_REQUIRES_ENV = [
    "GLPI_URL",
    "GLPI_CLIENT_ID",
    "GLPI_CLIENT_SECRET",
    "GLPI_USERNAME",
    "GLPI_PASSWORD",
]
_EMOJI = {
    "glpi_status": "🩺",
    "glpi_find_tickets": "🔎",
    "glpi_get_ticket": "🎫",
    "glpi_get_ticket_followups": "💬",
    "glpi_find_open_ticket_for_asset": "🔗",
}


def register(ctx) -> None:
    """Register five read-only GLPI tools with Hermes 0.21.5+."""
    from .tools import TOOL_DEFINITIONS

    for schema, handler, check_fn in TOOL_DEFINITIONS:
        name = schema["name"]
        ctx.register_tool(
            name=name,
            toolset=_TOOLSET,
            schema=schema,
            handler=handler,
            check_fn=check_fn,
            requires_env=_REQUIRES_ENV,
            description=schema["description"].split(". ")[0],
            emoji=_EMOJI.get(name, ""),
        )
