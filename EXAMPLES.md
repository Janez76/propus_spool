# API Usage Examples

This document provides curl examples for all API endpoints.

## Base URL

```
http://localhost:8000
```

## Health Check

Check if the service is running:

```bash
curl http://localhost:8000/health
```

## Weight Readings

### Submit a Reading

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

With timestamp:

```bash
curl -X POST http://localhost:8000/api/v1/readings \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "scale01",
    "uid": "04AABBCCDD",
    "gross_weight_g": 823.4,
    "timestamp": "2024-01-15T10:30:00Z"
  }'
```

## Tag Management

### List All Tags

```bash
curl http://localhost:8000/api/v1/tags
```

### Get Specific Tag

```bash
curl http://localhost:8000/api/v1/tags/04AABBCCDD
```

### Assign Spool to Tag

```bash
curl -X POST http://localhost:8000/api/v1/tags/04AABBCCDD/assign \
  -H "Content-Type: application/json" \
  -d '{
    "spoolman_spool_id": 123,
    "assigned_by": "admin"
  }'
```

### Set Tare Weight

Set the tare weight (empty spool + holder weight):

```bash
curl -X POST http://localhost:8000/api/v1/tags/04AABBCCDD/tare \
  -H "Content-Type: application/json" \
  -d '{
    "tare_weight_g": 150.0
  }'
```

## Spoolman Synchronization

### Pull Metadata from Spoolman

Sync filament metadata (brand, material, color, temperatures) from Spoolman:

```bash
curl -X POST http://localhost:8000/api/v1/sync/spoolman/pull
```

### Push Weight to Spoolman

Manually push current weight of a specific spool to Spoolman:

```bash
curl -X POST http://localhost:8000/api/v1/sync/spoolman/push/04AABBCCDD
```

## OpenSpool Integration

### Generate OpenSpool Payload

Generate OpenSpool-compatible JSON for NFC tag writing:

```bash
curl -X POST http://localhost:8000/api/v1/tags/04AABBCCDD/write_openspools \
  -H "Content-Type: application/json" \
  -d '{
    "force": false
  }'
```

With force flag (bypass WRITE_MODE check):

```bash
curl -X POST http://localhost:8000/api/v1/tags/04AABBCCDD/write_openspools \
  -H "Content-Type: application/json" \
  -d '{
    "force": true
  }'
```

## Typical Workflow

### Initial Setup

1. Set tare weight for a new tag:
```bash
curl -X POST http://localhost:8000/api/v1/tags/04AABBCCDD/tare \
  -H "Content-Type: application/json" \
  -d '{"tare_weight_g": 150.0}'
```

2. Assign the tag to a Spoolman spool:
```bash
curl -X POST http://localhost:8000/api/v1/tags/04AABBCCDD/assign \
  -H "Content-Type: application/json" \
  -d '{"spoolman_spool_id": 123}'
```

3. Pull metadata from Spoolman:
```bash
curl -X POST http://localhost:8000/api/v1/sync/spoolman/pull
```

### Regular Use

ESP32 scale continuously sends weight readings:

```bash
# This would be automated by ESP32 firmware
curl -X POST http://localhost:8000/api/v1/readings \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "scale01",
    "uid": "04AABBCCDD",
    "gross_weight_g": 673.4
  }'
```

### Monitoring

Check current state of all spools:

```bash
curl http://localhost:8000/api/v1/tags | jq
```

Check specific spool:

```bash
curl http://localhost:8000/api/v1/tags/04AABBCCDD | jq
```

## Testing with Multiple Tags

### Tag 1 - PLA Red

```bash
# Set tare
curl -X POST http://localhost:8000/api/v1/tags/041122334455/tare \
  -H "Content-Type: application/json" \
  -d '{"tare_weight_g": 140.0}'

# Assign spool
curl -X POST http://localhost:8000/api/v1/tags/041122334455/assign \
  -H "Content-Type: application/json" \
  -d '{"spoolman_spool_id": 1}'

# Submit reading
curl -X POST http://localhost:8000/api/v1/readings \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "scale01",
    "uid": "041122334455",
    "gross_weight_g": 890.5
  }'
```

### Tag 2 - PETG Blue

```bash
# Set tare
curl -X POST http://localhost:8000/api/v1/tags/046677889900/tare \
  -H "Content-Type: application/json" \
  -d '{"tare_weight_g": 145.0}'

# Assign spool
curl -X POST http://localhost:8000/api/v1/tags/046677889900/assign \
  -H "Content-Type: application/json" \
  -d '{"spoolman_spool_id": 2}'

# Submit reading
curl -X POST http://localhost:8000/api/v1/readings \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "scale02",
    "uid": "046677889900",
    "gross_weight_g": 1120.3
  }'
```

## Error Handling

### Tag Not Found

```bash
curl http://localhost:8000/api/v1/tags/INVALID_UID
# Returns: 404 Not Found
```

### Invalid Request

```bash
curl -X POST http://localhost:8000/api/v1/readings \
  -H "Content-Type: application/json" \
  -d '{"invalid": "data"}'
# Returns: 422 Unprocessable Entity
```

### OpenSpool Write Without Permission

```bash
curl -X POST http://localhost:8000/api/v1/tags/04AABBCCDD/write_openspools \
  -H "Content-Type: application/json" \
  -d '{"force": false}'
# Returns: 403 Forbidden (if WRITE_MODE=false)
```
