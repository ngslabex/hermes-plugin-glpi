import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = "glpi_plugin_test"


def load_package():
    spec = importlib.util.spec_from_file_location(
        PACKAGE,
        ROOT / "__init__.py",
        submodule_search_locations=[str(ROOT)],
    )
    package = importlib.util.module_from_spec(spec)
    sys.modules[PACKAGE] = package
    spec.loader.exec_module(package)
    return package


def load_module(name):
    load_package()
    return __import__(f"{PACKAGE}.{name}", fromlist=[name])


class FakeContext:
    def __init__(self):
        self.calls = []

    def register_tool(self, name, toolset, schema, handler, **kwargs):
        self.calls.append((name, toolset, schema, handler, kwargs))


def test_registers_five_named_tools():
    package = load_package()
    ctx = FakeContext()
    package.register(ctx)
    names = [call[0] for call in ctx.calls]
    assert names == [
        "glpi_status",
        "glpi_find_tickets",
        "glpi_get_ticket",
        "glpi_get_ticket_followups",
        "glpi_find_open_ticket_for_asset",
    ]
    assert all(call[1] == "glpi" for call in ctx.calls)
    assert all(call[4]["requires_env"] for call in ctx.calls)


def test_status_uses_ticket_probe(monkeypatch):
    tools = load_module("tools")
    monkeypatch.setattr(tools, "get_access_token", lambda: "secret-token")
    monkeypatch.setattr(tools, "base_url", lambda: "http://glpi-api")
    monkeypatch.setattr(tools, "api_prefix", lambda: "/api.php/v2.2")
    monkeypatch.setattr(tools, "ticket_endpoint", lambda ticket_id=None: "/api.php/v2.2/Assistance/Ticket")
    seen = {}

    def fake_get(path, params=None):
        seen["path"] = path
        seen["params"] = params
        return {"data": [{"id": 1}]}

    monkeypatch.setattr(tools, "request_get", fake_get)
    result = json.loads(tools.handle_glpi_status({}))
    assert result["ok"] is True
    assert result["ticket_api_accessible"] is True
    assert result["probe_ticket_count"] == 1
    assert seen["path"].endswith("/Assistance/Ticket")
    assert "Status" not in seen["path"]


def test_asset_handler_read_only(monkeypatch):
    tools = load_module("tools")
    monkeypatch.setattr(
        tools,
        "_fetch_recent",
        lambda limit: [{"id": 9, "name": "CBS002-RTR-01 10.251.2.11 unavailable", "status": "Assigned"}],
    )
    result = json.loads(tools.handle_glpi_find_open_ticket_for_asset({"asset_name": "CBS002-RTR-01", "ip_address": "10.251.2.11"}))
    assert result["count"] == 1
    assert result["read_only"] is True


def test_closed_statuses():
    tools = load_module("tools")
    assert tools._looks_open({"status": "Assigned"})
    assert not tools._looks_open({"status": "Solved"})
    assert not tools._looks_open({"status": 6})
