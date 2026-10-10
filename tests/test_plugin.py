import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = "glpi_plugin_test"


def load_package():
    for key in list(sys.modules):
        if key == PACKAGE or key.startswith(PACKAGE + "."):
            del sys.modules[key]
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
    assert [call[0] for call in ctx.calls] == [
        "glpi_status",
        "glpi_find_tickets",
        "glpi_get_ticket",
        "glpi_get_ticket_followups",
        "glpi_find_open_ticket_for_asset",
    ]
    assert all(call[1] == "glpi" for call in ctx.calls)
    assert all(call[4]["requires_env"] for call in ctx.calls)


def test_fetch_recent_paginates_and_deduplicates(monkeypatch):
    tools = load_module("tools")
    pages = {
        0: {"data": [{"id": i, "name": f"T{i}"} for i in range(1, 101)]},
        100: {"data": [{"id": i, "name": f"T{i}"} for i in range(101, 201)]},
        200: {"data": [{"id": i, "name": f"T{i}"} for i in range(201, 251)]},
    }

    def fake_get(path, params=None):
        return pages.get((params or {}).get("start", 0), {"data": []})

    monkeypatch.setattr(tools, "request_get", fake_get)
    result = tools._fetch_recent(300)
    assert len(result) == 250
    assert result[0]["id"] == 1
    assert result[-1]["id"] == 250


def test_status_uses_start_and_ticket_probe(monkeypatch):
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
    assert seen["params"]["start"] == 0
    assert "page" not in seen["params"]


def test_asset_handler_reports_diagnostics(monkeypatch):
    tools = load_module("tools")
    monkeypatch.setattr(
        tools,
        "_fetch_recent",
        lambda: [
            {"id": 263, "name": "CBS002-RTR-01 10.251.2.11 unavailable", "status": "Assigned", "priority": "High"},
            {"id": 264, "name": "Other", "status": "Solved"},
        ],
    )
    result = json.loads(
        tools.handle_glpi_find_open_ticket_for_asset(
            {"asset_name": "CBS002-RTR-01", "ip_address": "10.251.2.11"}
        )
    )
    assert result["count"] == 1
    assert result["scanned"] == 2
    assert result["open_scanned"] == 1
    assert result["match_mode"] == "all_terms"


def test_closed_statuses():
    tools = load_module("tools")
    assert tools._looks_open({"status": "Assigned"})
    assert not tools._looks_open({"status": "Solved"})
    assert not tools._looks_open({"status": 6})
