# hermes-plugin-glpi

Read-only GLPI 12 ticket tools for Hermes Agent.

Version `0.1.0` uses the GLPI High-Level REST API with OAuth2 Password grant and exposes only read operations. It contains no ticket create, update, assignment, solve, close, followup-create, or delete handlers.

## Tools

- `glpi_status`
- `glpi_find_tickets`
- `glpi_get_ticket`
- `glpi_get_ticket_followups`
- `glpi_find_open_ticket_for_asset`

## Requirements

- GLPI 12
- Hermes Agent plugin support
- A dedicated GLPI OAuth client with only the `Password` grant and `api` scope
- A dedicated GLPI user with a read-only profile and access to the required entities
- Hermes and GLPI connected to the same Docker Swarm overlay network

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

`GLPI_API_PREFIX` is configurable because the High-Level API version available in GLPI can change. Confirm the active version in GLPI under **Setup > General > API > API Endpoints**. For GLPI 12, the documentation interface is commonly exposed under `/api.php/v2.2/doc`.

## Docker Swarm

Pass the variables into the Hermes process environment:

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

## Install

```bash
hermes plugins install ngslabex/hermes-plugin-glpi
hermes plugins enable glpi-tools
```

Manual installation:

```bash
git clone https://github.com/ngslabex/hermes-plugin-glpi.git \
  /opt/data/plugins/glpi-tools
```

Restart Hermes after installation:

```bash
docker service update --force hermes_hermes
```

## Verify

```bash
python -m py_compile \
  /opt/data/plugins/glpi-tools/client.py \
  /opt/data/plugins/glpi-tools/schemas.py \
  /opt/data/plugins/glpi-tools/tools.py
```

Ask Hermes:

```text
Use glpi_status to test GLPI OAuth and API connectivity.
```

```text
Use glpi_find_open_ticket_for_asset to find open tickets for
CBS002-RTR-01 or 10.251.2.11. Do not create or modify tickets.
```

## Security

- Use a separate OAuth client for Hermes.
- Allow only `Password` grant and `api` scope.
- Use a separate `hermes-integration` user.
- Give the user a read-only profile and only the required entities.
- Keep all credentials out of Git.
- Never log access tokens, client secrets, or passwords.
- Rotate credentials immediately if exposed.

## Endpoint compatibility

GLPI 12 exposes versioned High-Level API routes and publishes an OpenAPI interface. This plugin defaults to `/api.php/v2.2` and uses `/Assistance/Ticket` for ticket reads. The followup tool tries a small set of read-only endpoint variants because route names may vary between API revisions. If your GLPI deployment advertises another API version, set `GLPI_API_PREFIX` accordingly and run `glpi_status` plus the included smoke tests before production use.

## Limitations in v0.1.0

- The plugin is read-only by design.
- Free-text and asset correlation use a bounded recent ticket result set and client-side matching.
- Exact endpoint schemas may differ by GLPI High-Level API version.
- Followup endpoint availability must be validated against the instance OpenAPI page.
- No automatic ticket creation or ticket state changes are implemented.

## License

MIT
