# hermes-plugin-glpi

A read-only GLPI 12 plugin for Hermes Agent 0.21.5 or later.

## Highlights in v0.1.3

- Correct Hermes `PluginContext.register_tool()` registration.
- OAuth2 Password-grant authentication with in-memory token caching.
- Real ticket API health probe instead of the separately scoped `/Status` route.
- Bounded pagination of up to 300 recently updated visible tickets.
- Ticket-ID deduplication and duplicate-page protection.
- Direct ticket lookup, bounded ticket search, timeline/followup lookup, and asset/IP correlation.
- Diagnostic fields for correlation: `scanned`, `open_scanned`, `matched`, and `match_mode`.
- No GLPI resource create, update, assignment, solve, close, or delete operation.

## Tools

- `glpi_status`
- `glpi_find_tickets`
- `glpi_get_ticket`
- `glpi_get_ticket_followups`
- `glpi_find_open_ticket_for_asset`

## Environment

```dotenv
GLPI_URL=http://glpi-api
GLPI_CLIENT_ID=replace_me
GLPI_CLIENT_SECRET=replace_me
GLPI_USERNAME=hermes-integration
GLPI_PASSWORD=replace_me
GLPI_SCOPE=api
GLPI_TIMEOUT=30
GLPI_VERIFY_SSL=true
GLPI_API_PREFIX=/api.php/v2.2
```

`GLPI_SCOPE=api` is sufficient because `glpi_status` verifies read-only ticket API access rather than the separately scoped GLPI status endpoint.

## Docker Swarm

```yaml
services:
  hermes:
    environment:
      GLPI_URL: "${GLPI_URL:-http://glpi-api}"
      GLPI_CLIENT_ID: "${GLPI_CLIENT_ID:?GLPI_CLIENT_ID must be set}"
      GLPI_CLIENT_SECRET: "${GLPI_CLIENT_SECRET:?GLPI_CLIENT_SECRET must be set}"
      GLPI_USERNAME: "${GLPI_USERNAME:-hermes-integration}"
      GLPI_PASSWORD: "${GLPI_PASSWORD:?GLPI_PASSWORD must be set}"
      GLPI_SCOPE: "${GLPI_SCOPE:-api}"
      GLPI_TIMEOUT: "${GLPI_TIMEOUT:-30}"
      GLPI_VERIFY_SSL: "${GLPI_VERIFY_SSL:-true}"
      GLPI_API_PREFIX: "${GLPI_API_PREFIX:-/api.php/v2.2}"
```

Hermes and GLPI must share the Docker Swarm integration network. The GLPI service alias may be `glpi-api`.

## OAuth client

Use a dedicated OAuth client and user:

- Grant: `Password`
- Scope: `api`
- User: `hermes-integration` or another dedicated non-superuser account
- Profile: ticket, timeline, and followup read access only
- Entity authorization: include every entity whose tickets Hermes must inspect

Do not reuse the default `glpi` account or the Zabbix integration client.

## Install or upgrade

```bash
hermes plugins install ngslabex/hermes-plugin-glpi --force
hermes plugins enable glpi-tools
docker service update --force hermes_hermes
```

Manual pinned installation:

```bash
git clone --branch v0.1.3 --depth 1 \
  https://github.com/ngslabex/hermes-plugin-glpi.git \
  /opt/data/plugins/glpi-tools
```

## Verify

```bash
python -m py_compile \
  /opt/data/plugins/glpi-tools/__init__.py \
  /opt/data/plugins/glpi-tools/client.py \
  /opt/data/plugins/glpi-tools/schemas.py \
  /opt/data/plugins/glpi-tools/tools.py
```

```bash
hermes plugins doctor /opt/data/plugins/glpi-tools
hermes plugins validate /opt/data/plugins/glpi-tools
```

Expected:

```text
registrations: 5 tool(s), 0 hook(s)
Validation passed.
```

## Mattermost tests

Connection and ticket API:

```text
@hermes glpi_status aracını doğrudan kullanarak GLPI OAuth ve salt okunur ticket API erişimini kontrol et. execute_code veya terminal kullanma. Gizli değerleri gösterme.
```

Exact ticket lookup:

```text
@hermes glpi_get_ticket aracını doğrudan kullanarak GLPI ticket 263 kaydını salt okunur getir. execute_code veya terminal kullanma. Araç hata verirse gerçek hatayı yaz.
```

Asset/IP correlation:

```text
@hermes glpi_find_open_ticket_for_asset aracını doğrudan kullanarak CBS002-RTR-01 veya 10.251.2.11 için açık ticket ara. Taranan ticket sayısını, açık ticket sayısını, eşleşme yöntemini ve bulunan kayıtları göster. execute_code kullanma.
```

## Pagination behavior

The plugin scans up to 300 recently updated visible tickets by default, in pages of 100, using:

```text
start=<offset>
limit=<page size>
sort=date_mod:desc
```

Returned Mattermost results remain limited by each tool's `limit` argument. Scanning and presentation limits are intentionally separate.

## Troubleshooting

If `count` is zero, inspect these fields:

- `scanned`: number of visible tickets read from GLPI
- `open_scanned`: number considered open
- `matched`: total matching tickets before output limiting
- `match_mode`: `all_terms` or fallback `any_term`

If `scanned` is zero, verify the integration user's profile and entity authorization. If tickets are visible but the asset match is zero, verify that the ticket title/content returned by GLPI actually contains the device name or IP address.

## Security

- GLPI resource requests are GET-only.
- OAuth token acquisition is the only POST request.
- The plugin implements no PUT, PATCH, DELETE, ticket creation, followup creation, assignment, solve, or close handler.
- Credentials and access tokens are never returned by tool handlers.
- Use a dedicated read-only GLPI account and rotate any credential exposed in logs or screenshots.

## API compatibility

The default prefix is `/api.php/v2.2`. Confirm the active High-Level API version in GLPI's API Endpoints/OpenAPI page. Override `GLPI_API_PREFIX` if the deployed route differs.

## License

MIT
