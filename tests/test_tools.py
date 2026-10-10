import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = "glpi_test_plugin"


def load_module(name):
    package_spec = importlib.util.spec_from_file_location(
        PACKAGE,
        ROOT / "__init__.py",
        submodule_search_locations=[str(ROOT)],
    )
    package = importlib.util.module_from_spec(package_spec)
    sys.modules[PACKAGE] = package
    package_spec.loader.exec_module(package)
    return __import__(f"{PACKAGE}.{name}", fromlist=[name])


def test_ticket_summary_and_open_detection():
    tools = load_module("tools")
    item = {
        "id": 1842,
        "name": "CBS002-RTR-01 unavailable",
        "status": {"name": "Assigned"},
        "priority": {"name": "High"},
    }
    result = tools._ticket_summary(item)
    assert result["id"] == 1842
    assert result["status"] == "Assigned"
    assert tools._looks_open(item)


def test_closed_ticket_detection():
    tools = load_module("tools")
    assert not tools._looks_open({"status": "Solved"})
    assert not tools._looks_open({"status": 6})


def test_asset_handler_is_read_only(monkeypatch):
    tools = load_module("tools")
    monkeypatch.setattr(
        tools,
        "_fetch_recent",
        lambda limit: [
            {
                "id": 9,
                "name": "CBS002-RTR-01 10.251.2.11 unavailable",
                "status": "Assigned",
            }
        ],
    )
    data = json.loads(
        tools.handle_glpi_find_open_ticket_for_asset(
            {"asset_name": "CBS002-RTR-01", "ip_address": "10.251.2.11"}
        )
    )
    assert data["count"] == 1
    assert data["read_only"] is True
