# Changelog

## 0.1.3 - 2026-10-10

- Added bounded ticket pagination with `start`, `limit`, and `sort=date_mod:desc`.
- Increased the default correlation scan to 300 visible tickets in pages of 100.
- Added ticket-ID deduplication and duplicate-page detection.
- Added `scanned`, `open_scanned`, `matched`, and `match_mode` diagnostics.
- Updated `glpi_status` to use `start=0` against the ticket endpoint.
- Added `/Timeline` as the preferred ticket history endpoint.
- Replaced followup pagination `page` with `start`.
- Removed unrestricted raw ticket payloads from summaries.
- Retained GET-only GLPI resource behavior.

## 0.1.2 - 2026-10-10

- Fixed Hermes 0.21.5 tool registration.
- Replaced the separately scoped `/Status` check with a read-only ticket API probe.
- Added environment metadata, descriptions, emojis, and stronger tests.
- Retained GET-only GLPI resource behavior.

## 0.1.0

- Initial read-only GLPI 12 tools.
