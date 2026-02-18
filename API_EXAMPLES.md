# API Examples

This document provides example curl commands for testing the Propus Spool API.

## Prerequisites

Start the server:
```bash
# Local development
uvicorn app.main:app --reload

# Or with Docker
docker-compose up -d
```

## Health Check

```bash
curl http://localhost:8000/health
```

Response:
```json
{
  "status": "ok",
  "database": "ok",
  "spoolman": null
}
```

## Submit Weight Reading

Submit a weight reading from an ESP32 scale:

```bash
curl -X POST http://localhost:8000/api/v1/readings \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "scale01",
    "uid": "04AABBCCDD",
    "gross_weight_g": 823.4
  }'
```

Response:
```json
{
  "success": true,
  "uid": "04AABBCCDD",
  "gross_weight_g": 823.4,
  "tare_weight_g": 0.0,
  "net_weight_g": 823.4,
  "spoolman_pushed": false,
  "timestamp": "2026-02-18T20:24:26.725633"
}
```

With custom timestamp:
```bash
curl -X POST http://localhost:8000/api/v1/readings \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "scale01",
    "uid": "04AABBCCDD",
    "gross_weight_g": 750.2,
    "timestamp": "2024-01-15T10:30:00Z"
  }'
```

## List All Tags

```bash
curl http://localhost:8000/api/v1/tags
```

Response:
```json
[
  {
    "uid": "04AABBCCDD",
    "notes": null,
    "created_at": "2026-02-18T20:24:26",
    "last_seen_at": "2026-02-18T20:24:39.208263"
  }
]
```

With pagination:
```bash
curl "http://localhost:8000/api/v1/tags?skip=0&limit=50"
```

## Get Tag Details

```bash
curl http://localhost:8000/api/v1/tags/04AABBCCDD
```

Response:
```json
{
  "uid": "04AABBCCDD",
  "notes": null,
  "created_at": "2026-02-18T20:24:26",
  "last_seen_at": "2026-02-18T20:24:39.208263",
  "spool_mapping": {
    "uid": "04AABBCCDD",
    "spoolman_spool_id": 123,
    "assigned_at": "2026-02-18T20:24:39",
    "assigned_by": null
  },
  "spool_state": {
    "uid": "04AABBCCDD",
    "gross_weight_g": 700.5,
    "tare_weight_g": 250.0,
    "net_weight_g": 450.5,
    "last_weight_at": "2026-02-18T20:24:39.208263",
    "status": "active"
  }
}
```

## Set Tare Weight

Set the tare weight (spool + holder) for a tag:

```bash
curl -X POST http://localhost:8000/api/v1/tags/04AABBCCDD/tare \
  -H "Content-Type: application/json" \
  -d '{"tare_weight_g": 250.0}'
```

Response:
```json
{
  "success": true,
  "uid": "04AABBCCDD",
  "tare_weight_g": 250.0,
  "gross_weight_g": 823.4,
  "net_weight_g": 573.4
}
```

## Assign Spoolman Spool

Link an NFC tag to a Spoolman spool ID:

```bash
curl -X POST http://localhost:8000/api/v1/tags/04AABBCCDD/assign \
  -H "Content-Type: application/json" \
  -d '{
    "spoolman_spool_id": 123,
    "assigned_by": "admin@example.com"
  }'
```

Response:
```json
{
  "uid": "04AABBCCDD",
  "spoolman_spool_id": 123,
  "assigned_at": "2026-02-18T20:24:39",
  "assigned_by": "admin@example.com"
}
```

## Sync with Spoolman

### Pull Metadata from Spoolman

Fetch filament metadata for all mapped spools:

```bash
curl -X POST http://localhost:8000/api/v1/sync/spoolman/pull
```

Response:
```json
{
  "success": true,
  "message": "Synced 5 spools from Spoolman",
  "synced_count": 5
}
```

### Push Weight to Spoolman

Update remaining weight in Spoolman:

```bash
curl -X POST http://localhost:8000/api/v1/sync/spoolman/push/04AABBCCDD
```

Response:
```json
{
  "success": true,
  "message": "Updated Spoolman spool 123 with 450.5g",
  "synced_count": null
}
```

## OpenSpool Write

Generate OpenSpool-compatible JSON (requires WRITE_MODE=true or force parameter):

```bash
# With force flag (bypasses WRITE_MODE check)
curl -X POST "http://localhost:8000/api/v1/sync/tags/04AABBCCDD/write_openspool?force=true"
```

Response:
```json
{
  "success": true,
  "message": "OpenSpool payload generated (NFC write stub - hardware integration needed)",
  "payload": {
    "version": 1,
    "uid": "04AABBCCDD",
    "manufacturer": "Polymaker",
    "material": "PLA",
    "color": "#FF0000",
    "diameter": 1.75,
    "weight": 450.5,
    "temperature": {
      "min": 200,
      "max": 240
    }
  }
}
```

## Interactive API Documentation

Visit these URLs in your browser:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- OpenAPI JSON: http://localhost:8000/openapi.json

## Testing Workflow

Complete workflow example:

```bash
# 1. Check health
curl http://localhost:8000/health

# 2. Submit initial reading
curl -X POST http://localhost:8000/api/v1/readings \
  -H "Content-Type: application/json" \
  -d '{"device_id": "scale01", "uid": "04AABBCCDD", "gross_weight_g": 1250.0}'

# 3. Set tare weight
curl -X POST http://localhost:8000/api/v1/tags/04AABBCCDD/tare \
  -H "Content-Type: application/json" \
  -d '{"tare_weight_g": 250.0}'

# 4. Assign to Spoolman spool
curl -X POST http://localhost:8000/api/v1/tags/04AABBCCDD/assign \
  -H "Content-Type: application/json" \
  -d '{"spoolman_spool_id": 42}'

# 5. Submit usage reading
curl -X POST http://localhost:8000/api/v1/readings \
  -H "Content-Type: application/json" \
  -d '{"device_id": "scale01", "uid": "04AABBCCDD", "gross_weight_g": 800.0}'

# 6. Check tag details
curl http://localhost:8000/api/v1/tags/04AABBCCDD

# 7. Push to Spoolman
curl -X POST http://localhost:8000/api/v1/sync/spoolman/push/04AABBCCDD
```

## Error Responses

### Tag Not Found (404)
```bash
curl http://localhost:8000/api/v1/tags/NOTFOUND
```

Response:
```json
{
  "detail": "Tag not found"
}
```

### Write Mode Disabled (403)
```bash
curl -X POST http://localhost:8000/api/v1/sync/tags/04AABBCCDD/write_openspool
```

Response:
```json
{
  "detail": "Write mode is disabled. Set WRITE_MODE=true or use force parameter"
}
```

### Spoolman Not Configured (400)
```bash
curl -X POST http://localhost:8000/api/v1/sync/spoolman/pull
```

Response (when SPOOLMAN_URL not set):
```json
{
  "detail": "Spoolman URL not configured"
}
```
