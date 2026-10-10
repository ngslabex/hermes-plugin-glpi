# hermes-plugin-glpi

A read-only GLPI 12 plugin for Hermes Agent 0.21.5 or later.

## Changes in v0.1.2

- Fixed `PluginContext.register_tool()` registration using explicit `name`, `toolset`, `schema`, and `handler` arguments.
- Added `requires_env` metadata to every registered tool.
- Changed `glpi_status` to probe the real ticket API instead of `/Status`, eliminating the extra `status` OAuth scope requirement and its HTTP 403 failure.
- Kept all GLPI resource operations GET-only.
- Improved OAuth cache, HTTP errors, schema descriptions, tests, and package validation.

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

`GLPI_SCOPE=api` is sufficient in v0.1.2 because `glpi_status` checks ticket API access instead of the separately scoped GLPI status endpoint.

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

## OAuth client

Use a dedicated OAuth client:

- Grant: `Password`
- Scope: `api`
- User: a dedicated non-superuser account such as `hermes-integration`
- Profile: ticket/followup read access only

## Install or upgrade

```bash
hermes plugins install ngslabex/hermes-plugin-glpi --force
hermes plugins enable glpi-tools
docker service update --force hermes_hermes
```

Manual pinned installation:

```bash
git clone --branch v0.1.2 --depth 1 \
  https://github.com/ngslabex/hermes-plugin-glpi.git \
  /opt/data/plugins/glpi-tools
```

## Verify

```bash
hermes plugins doctor /opt/data/plugins/glpi-tools
hermes plugins validate /opt/data/plugins/glpi-tools
```

Expected:

```text
registrations: 5 tool(s), 0 hook(s)
Validation passed.
```

Mattermost test:

```text
@hermes glpi_status aracını kullanarak GLPI OAuth ve salt okunur ticket API erişimini kontrol et. Gizli değerleri gösterme.
```

## Security

The plugin implements no GLPI resource POST, PUT, PATCH, or DELETE handlers. OAuth token acquisition is the only POST request. Use a dedicated read-only GLPI profile, keep credentials out of Git, and rotate any credential exposed in logs or screenshots.

## API compatibility

The default prefix is `/api.php/v2.2`. Verify the active High-Level API version in the GLPI API Endpoints/OpenAPI page. If required, override `GLPI_API_PREFIX` without changing plugin code.

## License

MIT
