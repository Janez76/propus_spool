# Propus Spool

Modular filament scale and NFC UID management system for 3D printing.

## Overview

Propus Spool is a Docker-based system that manages filament spools using NFC tags and weight scales. It integrates with Spoolman for spool management and optionally supports OpenSpool format for NFC tag writing.

### Key Features

- **NFC UID-based tracking**: Uses NFC tag UIDs as primary keys (no writing to tags by default)
- **Weight monitoring**: Tracks gross, tare, and net weight of filament spools
- **Spoolman integration**: Bi-directional sync with Spoolman API
- **OpenSpool support**: Optional NFC tag writing (feature flag controlled)
- **Multi-arch Docker**: Supports amd64 and arm64 architectures
- **Flexible database**: PostgreSQL or SQLite backend
- **RESTful API**: Complete FastAPI-based REST API

## Architecture

### Components

- **Backend**: Python with FastAPI
- **Database**: PostgreSQL (primary) or SQLite (fallback)
- **External Integration**: Spoolman API client
- **Deployment**: Docker and Docker Compose

### Database Models

- `devices`: Scale devices
- `tags`: NFC tags with UIDs
- `spools_map`: Mapping between tags and Spoolman spools
- `spool_state`: Current weight and status of spools
- `spool_meta_cache`: Cached filament metadata from Spoolman
- `printer_binding`: Optional printer/slot bindings
- `weight_readings`: Historical weight measurements

## Quick Start

### Prerequisites

- Docker and Docker Compose
- (Optional) Spoolman instance running

### Installation

1. Clone the repository:
```bash
git clone https://github.com/Janez76/propus_spool.git
cd propus_spool
```

2. Copy the example environment file:
```bash
cp .env.example .env
```

3. Edit `.env` with your settings:
```bash
# For SQLite (default)
DATABASE_URL=sqlite:////data/propus_spool.db

# For PostgreSQL
# DATABASE_URL=postgresql://propus:propus_password@postgres:5432/propus_spool

# Spoolman configuration
SPOOLMAN_URL=http://your-spoolman-instance:7912
SPOOLMAN_API_KEY=your_api_key_here

# Feature flags
WRITE_MODE=false
PUSH_REMAINING_TO_SPOOLMAN=true
```

4. Start the application:
```bash
docker-compose up -d
```

5. Access the API:
- API: http://localhost:8000
- Health check: http://localhost:8000/health
- API docs: http://localhost:8000/docs

## API Endpoints

### Core Reading Endpoint

**POST /api/v1/readings**

Submit a weight reading from a scale device.

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

Response:
```json
{
  "success": true,
  "uid": "04AABBCCDD",
  "gross_weight_g": 823.4,
  "net_weight_g": 673.4,
  "tare_weight_g": 150.0
}
```

### Tag Management

**GET /api/v1/tags**

List all tags with their current state.

```bash
curl http://localhost:8000/api/v1/tags
```

**GET /api/v1/tags/{uid}**

Get details of a specific tag.

```bash
curl http://localhost:8000/api/v1/tags/04AABBCCDD
```

**POST /api/v1/tags/{uid}/assign**

Assign a Spoolman spool ID to a tag.

```bash
curl -X POST http://localhost:8000/api/v1/tags/04AABBCCDD/assign \
  -H "Content-Type: application/json" \
  -d '{
    "spoolman_spool_id": 123,
    "assigned_by": "user@example.com"
  }'
```

**POST /api/v1/tags/{uid}/tare**

Set tare weight for a tag.

```bash
curl -X POST http://localhost:8000/api/v1/tags/04AABBCCDD/tare \
  -H "Content-Type: application/json" \
  -d '{
    "tare_weight_g": 150.0
  }'
```

### Spoolman Synchronization

**POST /api/v1/sync/spoolman/pull**

Pull spool metadata from Spoolman.

```bash
curl -X POST http://localhost:8000/api/v1/sync/spoolman/pull
```

**POST /api/v1/sync/spoolman/push/{uid}**

Push current weight of a tag to Spoolman.

```bash
curl -X POST http://localhost:8000/api/v1/sync/spoolman/push/04AABBCCDD
```

### OpenSpool Integration

**POST /api/v1/tags/{uid}/write_openspools**

Generate OpenSpool-compatible payload for NFC writing.

```bash
curl -X POST http://localhost:8000/api/v1/tags/04AABBCCDD/write_openspools \
  -H "Content-Type: application/json" \
  -d '{
    "force": false
  }'
```

## Deployment

### On Ugreen NAS (8800DPX)

1. Install Container Manager on your Ugreen NAS
2. Upload the docker-compose.yml file
3. Create a `.env` file with your configuration
4. Start the container via Container Manager UI

### On Raspberry Pi

1. Install Docker and Docker Compose:
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo apt-get install docker-compose-plugin
```

2. Clone and configure:
```bash
git clone https://github.com/Janez76/propus_spool.git
cd propus_spool
cp .env.example .env
nano .env  # Edit configuration
```

3. Start the service:
```bash
docker-compose up -d
```

### With PostgreSQL

To use PostgreSQL instead of SQLite:

1. Uncomment the PostgreSQL service in `docker-compose.yml`
2. Update `.env`:
```
DATABASE_URL=postgresql://propus:propus_password@postgres:5432/propus_spool
```

3. Restart containers:
```bash
docker-compose down
docker-compose up -d
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite:///./propus_spool.db` | Database connection string |
| `SPOOLMAN_URL` | `http://localhost:7912` | Spoolman API URL |
| `SPOOLMAN_API_KEY` | (empty) | Spoolman API key |
| `WRITE_MODE` | `false` | Enable NFC tag writing |
| `PUSH_REMAINING_TO_SPOOLMAN` | `true` | Auto-push weights to Spoolman |
| `ENABLE_KLIPPER` | `false` | Enable Klipper integration (future) |
| `API_V1_PREFIX` | `/api/v1` | API path prefix |
| `LOG_LEVEL` | `INFO` | Logging level |

## Development

### Running Locally

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create `.env` file from example

4. Run the application:
```bash
uvicorn app.main:app --reload
```

### Database Migrations

Generate a new migration:
```bash
alembic revision --autogenerate -m "Description of changes"
```

Apply migrations:
```bash
alembic upgrade head
```

## Integration with ESP32 Scales

Your ESP32 scale hardware should POST weight readings to the `/api/v1/readings` endpoint:

```cpp
// Example ESP32 code snippet
HTTPClient http;
http.begin("http://propus-spool:8000/api/v1/readings");
http.addHeader("Content-Type", "application/json");

String payload = "{\"device_id\":\"" + deviceId + 
                 "\",\"uid\":\"" + nfcUid + 
                 "\",\"gross_weight_g\":" + String(weight) + "}";

int httpCode = http.POST(payload);
```

## Future Extensions

- Klipper/Moonraker integration
- Printer/slot management UI
- Advanced conflict resolution
- Multi-device support
- Web dashboard

## License

MIT License

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.