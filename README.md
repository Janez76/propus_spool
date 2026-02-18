# Propus Spool

A modular filament scale and NFC UID management system that runs in Docker (amd64 + arm64) and can be deployed on a NAS (Ugreen 8800DPX) or Raspberry Pi.

This system replaces older Filaman setups while keeping existing ESP32 scale hardware. It reads NTAG215 NFC tags by UID only (no writing by default), stores data locally, and synchronizes with Spoolman.

## Features

- **NFC UID Tracking**: Read NTAG215 tags by UID without writing data
- **Weight Management**: Track gross, tare, and net weights for filament spools
- **Spoolman Integration**: Bidirectional sync with Spoolman for metadata and weight
- **OpenSpool Support**: Optional NFC writing with feature flag (WRITE_MODE)
- **Multi-Database**: PostgreSQL primary with SQLite fallback
- **Docker Ready**: Multi-arch support (amd64 + arm64)
- **RESTful API**: FastAPI-based with automatic documentation
- **Extensible**: Modular architecture ready for Klipper/Moonraker integration

## Architecture

```
app/
├── main.py              # FastAPI application entry point
├── config.py            # Configuration management
├── database.py          # Database setup and session management
├── models/              # SQLAlchemy ORM models
├── schemas/             # Pydantic request/response schemas
├── routers/             # API route handlers
│   ├── health.py        # Health check endpoint
│   ├── readings.py      # Weight reading endpoints
│   ├── tags.py          # Tag management endpoints
│   └── sync.py          # Spoolman sync endpoints
├── services/            # Business logic layer
│   ├── readings.py      # Reading processing
│   ├── tags.py          # Tag operations
│   ├── sync.py          # Spoolman synchronization
│   └── openspool.py     # OpenSpool integration
├── clients/             # External API clients
│   └── spoolman.py      # Spoolman API client
└── workers/             # Background workers
    └── sync_worker.py   # Periodic sync worker
```

## Quick Start

### Docker Compose (Recommended)

1. Clone the repository:
```bash
git clone https://github.com/Janez76/propus_spool.git
cd propus_spool
```

2. Copy and configure environment:
```bash
cp .env.example .env
# Edit .env with your settings
```

3. Start services:
```bash
docker-compose up -d
```

4. Access the API:
- API: http://localhost:8000
- API Documentation: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

### Manual Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure environment:
```bash
cp .env.example .env
# Edit .env with your database and Spoolman settings
```

3. Run the application:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Configuration

Edit `.env` file with your settings:

```bash
# Database (PostgreSQL or SQLite)
DATABASE_URL=postgresql://propus:propus@db:5432/propus_spool
# Or for SQLite: DATABASE_URL=sqlite:///./propus_spool.db

# Spoolman Integration
SPOOLMAN_URL=http://spoolman:8000
SPOOLMAN_API_KEY=your_api_key_here

# NFC Write Mode (default: false)
WRITE_MODE=false

# Auto-push weights to Spoolman (default: true)
PUSH_REMAINING_TO_SPOOLMAN=true

# Future: Klipper Integration
ENABLE_KLIPPER=false

# Application Settings
LOG_LEVEL=INFO
API_HOST=0.0.0.0
API_PORT=8000
```

## API Endpoints

### Core Endpoints

#### POST /api/v1/readings
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

#### GET /api/v1/tags
List all NFC tags.

```bash
curl http://localhost:8000/api/v1/tags
```

#### GET /api/v1/tags/{uid}
Get detailed information for a specific tag.

```bash
curl http://localhost:8000/api/v1/tags/04AABBCCDD
```

#### POST /api/v1/tags/{uid}/assign
Assign a Spoolman spool ID to a tag.

```bash
curl -X POST http://localhost:8000/api/v1/tags/04AABBCCDD/assign \
  -H "Content-Type: application/json" \
  -d '{
    "spoolman_spool_id": 123,
    "assigned_by": "user@example.com"
  }'
```

#### POST /api/v1/tags/{uid}/tare
Set tare weight for a tag.

```bash
curl -X POST http://localhost:8000/api/v1/tags/04AABBCCDD/tare \
  -H "Content-Type: application/json" \
  -d '{"tare_weight_g": 250.0}'
```

### Sync Endpoints

#### POST /api/v1/sync/spoolman/pull
Pull metadata from Spoolman for all mapped spools.

```bash
curl -X POST http://localhost:8000/api/v1/sync/spoolman/pull
```

#### POST /api/v1/sync/spoolman/push/{uid}
Push weight update to Spoolman for a specific spool.

```bash
curl -X POST http://localhost:8000/api/v1/sync/spoolman/push/04AABBCCDD
```

### OpenSpool Endpoint

#### POST /api/v1/sync/tags/{uid}/write_openspool
Generate OpenSpool payload (requires WRITE_MODE=true or force parameter).

```bash
curl -X POST http://localhost:8000/api/v1/sync/tags/04AABBCCDD/write_openspool?force=true
```

## Database Models

### devices
- `id`: Primary key
- `name`: Device name
- `device_id`: Unique device identifier
- `location`: Physical location
- `created_at`: Creation timestamp

### tags
- `uid`: NFC tag UID (primary key)
- `created_at`: First seen timestamp
- `last_seen_at`: Last seen timestamp
- `notes`: Optional notes

### spools_map
- `uid`: Tag UID (foreign key)
- `spoolman_spool_id`: Spoolman spool ID
- `assigned_at`: Assignment timestamp
- `assigned_by`: User who assigned

### spool_state
- `uid`: Tag UID (foreign key)
- `gross_weight_g`: Gross weight
- `tare_weight_g`: Tare weight (spool + holder)
- `net_weight_g`: Net weight (filament only)
- `last_weight_at`: Last measurement timestamp
- `status`: active | empty | archived

### spool_meta_cache
- `spoolman_spool_id`: Primary key
- `brand`, `material`, `color`: Filament properties
- `diameter`: Filament diameter
- `temp_min`, `temp_max`: Temperature range
- `updated_at`: Cache update timestamp

### weight_readings
- `id`: Primary key
- `device_id`: Device that made the reading
- `uid`: Tag UID
- `gross_weight_g`: Measured weight
- `created_at`: Reading timestamp

## Deployment

### Ugreen NAS (Docker)

1. Copy files to NAS
2. SSH into NAS and navigate to project directory
3. Run `docker-compose up -d`
4. Access via NAS IP on port 8000

### Raspberry Pi

1. Install Docker and Docker Compose:
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo apt-get install -y docker-compose
```

2. Clone repository and run:
```bash
git clone https://github.com/Janez76/propus_spool.git
cd propus_spool
docker-compose up -d
```

## Development

### Running Tests
```bash
# Install dev dependencies
pip install -r requirements.txt

# Run tests (when implemented)
pytest
```

### Building Docker Image
```bash
docker build -t propus_spool:latest .
```

### Multi-arch Build
```bash
docker buildx build --platform linux/amd64,linux/arm64 -t propus_spool:latest .
```

## Integration with ESP32 Scale

Your ESP32 scale should POST readings to `/api/v1/readings`:

```cpp
// Example ESP32 code snippet
HTTPClient http;
http.begin("http://your-server:8000/api/v1/readings");
http.addHeader("Content-Type", "application/json");

String payload = "{";
payload += "\"device_id\":\"scale01\",";
payload += "\"uid\":\"" + nfcUID + "\",";
payload += "\"gross_weight_g\":" + String(weight);
payload += "}";

int httpCode = http.POST(payload);
```

## Spoolman Integration

Propus Spool integrates with Spoolman in two ways:

1. **Pull (Metadata)**: Periodically fetch filament metadata from Spoolman
2. **Push (Weight)**: Automatically update remaining weight in Spoolman when readings arrive

Configure in `.env`:
```bash
SPOOLMAN_URL=http://spoolman:8000
PUSH_REMAINING_TO_SPOOLMAN=true
```

## OpenSpool Support

OpenSpool tag writing is **disabled by default**. Enable via:

```bash
WRITE_MODE=true
```

When enabled, use the `/api/v1/sync/tags/{uid}/write_openspool` endpoint to generate OpenSpool-compatible JSON payloads.

**Note**: Actual NFC writing requires hardware integration (not included in this release).

## Future Extensions

- Klipper/Moonraker integration
- Bambu Lab printer integration
- Multi-material unit (MMU) support
- Web UI dashboard
- Mobile app
- Advanced analytics and reporting

## License

MIT License (see LICENSE file)

## Contributing

Contributions welcome! Please open an issue or PR.

## Support

For issues and questions, please use GitHub Issues.