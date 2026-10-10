"""Hermes Agent entry point for the read-only GLPI tools plugin."""


def register(ctx):
    """Register all GLPI tools with Hermes."""
    from .tools import TOOL_DEFINITIONS

    for schema, handler, check_fn in TOOL_DEFINITIONS:
        ctx.register_tool(schema, handler, check_fn=check_fn)
