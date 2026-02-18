# Quick Start Guide

## Local Development

### Prerequisites
- Python 3.11+
- pip

### Setup Steps

1. **Install dependencies**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

3. **Run the application**
   ```bash
   uvicorn app.main:app --reload
   ```

4. **Access the API**
   - API: http://localhost:8000
   - Interactive docs: http://localhost:8000/docs
   - Health check: http://localhost:8000/health

## Docker Deployment

### SQLite (Quick Start)

```bash
docker-compose up -d
```

The service will be available at http://localhost:8000

### PostgreSQL (Production)

```bash
docker-compose -f docker-compose.dev.yml up -d
```

This starts both the app and a PostgreSQL database.

## First Steps

### 1. Create a device (automatic on first reading)

Submit a weight reading:
```bash
curl -X POST http://localhost:8000/api/v1/readings/ \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "scale01",
    "uid": "04AABBCCDD",
    "gross_weight_g": 850.0
  }'
```

### 2. Set tare weight

```bash
curl -X POST http://localhost:8000/api/v1/tags/04AABBCCDD/tare \
  -H "Content-Type: application/json" \
  -d '{"tare_weight_g": 150.0}'
```

### 3. Assign to Spoolman spool

```bash
curl -X POST http://localhost:8000/api/v1/tags/04AABBCCDD/assign \
  -H "Content-Type: application/json" \
  -d '{"spoolman_spool_id": 1}'
```

### 4. View all tags

```bash
curl http://localhost:8000/api/v1/tags/
```

## Integration with ESP32

Your ESP32 scale should POST to `/api/v1/readings/` with this JSON:

```json
{
  "device_id": "scale01",
  "uid": "04AABBCCDD",
  "gross_weight_g": 823.4
}
```

## Common Tasks

### View logs (Docker)
```bash
docker-compose logs -f propus_spool
```

### Stop services
```bash
docker-compose down
```

### Rebuild after code changes
```bash
docker-compose up -d --build
```

### Run tests
```bash
pytest tests/ -v
```

## Troubleshooting

### Database locked (SQLite)
Stop the application before running migrations:
```bash
docker-compose down
# Run migrations
docker-compose up -d
```

### Connection refused
Check if the service is running:
```bash
docker-compose ps
curl http://localhost:8000/health
```

### Spoolman sync not working
1. Verify SPOOLMAN_URL in .env
2. Test connectivity:
   ```bash
   curl http://your-spoolman-url/api/v1/info
   ```
3. Check API key if required

## Next Steps

- Read the full [README.md](README.md) for detailed documentation
- Check [EXAMPLES.md](EXAMPLES.md) for more API examples
- Configure Spoolman integration in .env
- Set up automatic backups for your database
- Deploy to your NAS or Raspberry Pi

## Support

For issues or questions, please check:
- Project documentation
- GitHub Issues
- API documentation at http://localhost:8000/docs
