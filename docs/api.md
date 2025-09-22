# API Reference

All endpoints live under `/api`. Unless noted otherwise, responses are JSON encoded with `application/json`. The backend also exposes a minimal root endpoint that advertises metadata and documentation links.

## Rate Limiting

By default oss-subfinder enforces a lightweight in-memory rate limit. Configure the bucket size and window (seconds) via environment variables:

```
RATE_LIMIT_REQUESTS=30
RATE_LIMIT_WINDOW=60
```

If a client exceeds the limit a `429 Too Many Requests` response is returned with a `Retry-After` header to indicate when they may retry. Client identification currently relies on the request's remote address; set `TRUST_X_FORWARDED_FOR=true` when running behind a proxy that forwards `X-Forwarded-For`.

## Endpoints

### `GET /api/search`

Enumerates a domain and streams progress using [Server-Sent Events](https://html.spec.whatwg.org/multipage/server-sent-events.html). Query parameters:

- `domain` (required): target domain to scan.
- `refresh` (optional): set to `1` to bypass cached results and force a fresh run.

Each event payload is a JSON object. Stage events include a `stage` key (`started`, `cache_hit`, `crt_sh_found`, `resolving`, `done`, `error`). Entry events use `type: "entry"` and include discovery metadata:

```json
{
  "type": "entry",
  "name": "api.example.com",
  "ips": ["93.184.216.34"],
  "cname": "",
  "http_status": 200,
  "tls": true,
  "server": "nginx"
}
```

Errors are emitted as `stage: "error"` with an `error` message. The SSE stream responds with `200 OK` on success and `4xx/5xx` if validation fails before streaming begins.

### `GET /api/history`

Returns the latest cached results, summary metadata, and recent run timings for a domain.

Parameters:

- `domain` (required)

Example response:

```json
{
  "domain": "example.com",
  "cached": "2024-04-22T11:14:20+00:00",
  "total": 42,
  "results": [
    {
      "name": "api.example.com",
      "ips": ["93.184.216.34"],
      "cname": "",
      "http_status": 200,
      "tls": true,
      "server": "nginx"
    }
  ],
  "runs": [
    {
      "id": 123,
      "domain": "example.com",
      "timestamp": "2024-04-22T11:14:20+00:00",
      "total": 42,
      "duration_ms": 1850
    }
  ]
}
```

### `GET /api/recent`

Lists the most recent completed scans stored in Postgres. Query parameters:

- `limit` (optional): cap for results; defaults to 10 and cannot exceed the configured `RECENT_SCANS_LIMIT`.

Response shape:

```json
{
  "recent": [
    {
      "id": 123,
      "domain": "example.com",
      "timestamp": "2024-04-22T11:14:20+00:00",
      "total": 42,
      "duration_ms": 1850
    }
  ]
}
```

### `GET /api/status`

Performs an on-demand probe (DNS + HTTP(S) + TLS) for a single hostname.

Parameters:

- `domain` (required): hostname or subdomain to inspect.

Example response:

```json
{
  "domain": "login.example.com",
  "ips": ["203.0.113.4"],
  "http_status": 200,
  "tls": true,
  "server": "cloudfront",
  "cname": "d111111abcdef8.cloudfront.net",
  "last_probe": "2024-04-22T11:16:05+00:00"
}
```

### `GET /api/whois`

Returns structured WHOIS information, including registrar details, creation/expiration dates, and raw text fallback. Parameters:

- `domain` (required)

Response shape:

```json
{
  "domain": "example.com",
  "registrar": "Example Registrar",
  "created": "1995-08-13",
  "expires": "2030-08-12",
  "status": ["clientTransferProhibited"],
  "raw": "..."
}
```

### `GET /`

Root metadata endpoint intended for health checks. Returns version info, feature toggles, and links to documentation so API consumers know where to start.

## Error Handling

- Validation failures return `400` with `{"detail": "..."}` bodies.
- Rate limit breaches return `429` with a `Retry-After` header.
- Unexpected internal errors return `500` and include a correlation ID in logs.

When subscribing to `/api/search`, always handle premature stream termination gracefully — consumers should treat the SSE connection as best-effort.
