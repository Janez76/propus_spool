# Quick Start Guide

Get Propus Spool running in 5 minutes!

## Option 1: Docker Compose (Easiest)

```bash
# 1. Clone the repository
git clone https://github.com/Janez76/propus_spool.git
cd propus_spool

# 2. Start services
docker compose up -d

# 3. Check status
docker compose ps

# 4. View logs
docker compose logs -f app

# 5. Test the API
curl http://localhost:8000/health
```

**That's it!** The API is now running at http://localhost:8000

Access the interactive documentation at http://localhost:8000/docs

## Option 2: Python (Local Development)

```bash
# 1. Clone and setup
git clone https://github.com/Janez76/propus_spool.git
cd propus_spool
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the server
uvicorn app.main:app --reload

# 4. Test
curl http://localhost:8000/health
```

Access at http://localhost:8000

## First Steps

### 1. Submit a Weight Reading

```bash
curl -X POST http://localhost:8000/api/v1/readings \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "scale01",
    "uid": "04AABBCCDD",
    "gross_weight_g": 1250.0
  }'
```

### 2. Set Tare Weight

```bash
curl -X POST http://localhost:8000/api/v1/tags/04AABBCCDD/tare \
  -H "Content-Type: application/json" \
  -d '{"tare_weight_g": 250.0}'
```

### 3. View Tag Details

```bash
curl http://localhost:8000/api/v1/tags/04AABBCCDD | python3 -m json.tool
```

## Configuration

Edit `.env` file to configure:

```bash
# Required only if using Spoolman
SPOOLMAN_URL=http://your-spoolman:8000
SPOOLMAN_API_KEY=your_api_key

# Optional settings
WRITE_MODE=false  # Enable NFC writing
PUSH_REMAINING_TO_SPOOLMAN=true  # Auto-update Spoolman
LOG_LEVEL=INFO
```

## Next Steps

- Read the [README.md](README.md) for full documentation
- Check [API_EXAMPLES.md](API_EXAMPLES.md) for more API examples
- See [DEPLOYMENT.md](DEPLOYMENT.md) for production deployment
- Visit http://localhost:8000/docs for interactive API documentation

## Troubleshooting

### Port 8000 already in use?

Edit `docker-compose.yml` and change:
```yaml
ports:
  - "8080:8000"  # Use port 8080 instead
```

### Database connection failed?

Check if PostgreSQL is running:
```bash
docker compose ps db
```

Or switch to SQLite by editing `.env`:
```bash
DATABASE_URL=sqlite:///./propus_spool.db
```

### Need help?

- Check logs: `docker compose logs app`
- Visit: https://github.com/Janez76/propus_spool/issues
- Read the docs at http://localhost:8000/docs

## Connecting Your ESP32 Scale

Configure your ESP32 to POST to:
```
http://your-server:8000/api/v1/readings
```

Example JSON payload:
```json
{
  "device_id": "scale01",
  "uid": "04AABBCCDD",
  "gross_weight_g": 823.4
}
```

See README.md for ESP32 code examples.
