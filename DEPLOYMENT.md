# Deployment Guide

This guide covers deploying Propus Spool on various platforms.

## Table of Contents

- [Docker Compose (Recommended)](#docker-compose-recommended)
- [Ugreen NAS 8800DPX](#ugreen-nas-8800dpx)
- [Raspberry Pi](#raspberry-pi)
- [Standalone Python](#standalone-python)
- [Configuration](#configuration)
- [Database Options](#database-options)

---

## Docker Compose (Recommended)

The easiest way to run Propus Spool with PostgreSQL.

### Requirements
- Docker 20.10+
- Docker Compose 2.0+

### Setup

1. Clone the repository:
```bash
git clone https://github.com/Janez76/propus_spool.git
cd propus_spool
```

2. Create environment file:
```bash
cp .env.example .env
```

3. Edit `.env` with your settings:
```bash
nano .env
```

4. Start services:
```bash
docker-compose up -d
```

5. Check logs:
```bash
docker-compose logs -f app
```

6. Access the API:
- API: http://localhost:8000
- Documentation: http://localhost:8000/docs

### Updating

```bash
git pull
docker-compose down
docker-compose build
docker-compose up -d
```

### Backup

Backup PostgreSQL data:
```bash
docker-compose exec db pg_dump -U propus propus_spool > backup_$(date +%Y%m%d).sql
```

Restore:
```bash
cat backup_20240115.sql | docker-compose exec -T db psql -U propus propus_spool
```

---

## Ugreen NAS 8800DPX

Deploy on Ugreen NAS using the built-in Docker support.

### Requirements
- Ugreen NAS with Docker installed
- SSH access to NAS
- Basic terminal knowledge

### Steps

1. **Enable SSH** on your Ugreen NAS (via web interface)

2. **SSH into NAS**:
```bash
ssh admin@your-nas-ip
```

3. **Create project directory**:
```bash
mkdir -p /volume1/docker/propus_spool
cd /volume1/docker/propus_spool
```

4. **Copy files to NAS** (from your local machine):
```bash
# Using SCP
scp -r propus_spool admin@your-nas-ip:/volume1/docker/

# Or use the NAS web file manager to upload
```

5. **Configure environment**:
```bash
cd /volume1/docker/propus_spool
cp .env.example .env
nano .env
```

Update database URL for NAS storage:
```bash
DATABASE_URL=sqlite:////volume1/docker/propus_spool/data/propus_spool.db
```

6. **Run with Docker Compose**:
```bash
docker-compose up -d
```

7. **Access the service**:
```
http://nas-ip:8000
```

### Using NAS Web Docker Manager

Alternatively, use the Ugreen Docker web interface:

1. Open Docker manager in NAS web interface
2. Create a new stack/compose project
3. Paste the `docker-compose.yml` content
4. Set environment variables in the UI
5. Start the stack

### Persistence

Ensure data persists across restarts by using volumes on the NAS storage:

```yaml
volumes:
  - /volume1/docker/propus_spool/data:/app/data
```

---

## Raspberry Pi

Deploy on Raspberry Pi 4/5 (arm64).

### Requirements
- Raspberry Pi 4 or 5 (2GB+ RAM recommended)
- Raspberry Pi OS (64-bit)
- Docker installed

### Setup

1. **Install Docker** (if not already installed):
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
```

2. **Install Docker Compose**:
```bash
sudo apt-get update
sudo apt-get install -y docker-compose
```

3. **Clone repository**:
```bash
cd ~
git clone https://github.com/Janez76/propus_spool.git
cd propus_spool
```

4. **Configure**:
```bash
cp .env.example .env
nano .env
```

For Pi, consider using SQLite for lower resource usage:
```bash
DATABASE_URL=sqlite:///./propus_spool.db
```

5. **Start services**:
```bash
docker-compose up -d
```

### Optimization for Raspberry Pi

For better performance on Pi, create a custom `docker-compose.pi.yml`:

```yaml
version: '3.8'

services:
  app:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=sqlite:///./data/propus_spool.db
      - SPOOLMAN_URL=${SPOOLMAN_URL:-}
      - SPOOLMAN_API_KEY=${SPOOLMAN_API_KEY:-}
      - WRITE_MODE=${WRITE_MODE:-false}
      - PUSH_REMAINING_TO_SPOOLMAN=${PUSH_REMAINING_TO_SPOOLMAN:-true}
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
    volumes:
      - ./data:/app/data
    restart: unless-stopped
```

Run with:
```bash
docker-compose -f docker-compose.pi.yml up -d
```

### Auto-start on Boot

Enable Docker to start on boot:
```bash
sudo systemctl enable docker
```

---

## Standalone Python

Run directly with Python (without Docker).

### Requirements
- Python 3.11+
- PostgreSQL 15+ or SQLite

### Setup

1. **Clone repository**:
```bash
git clone https://github.com/Janez76/propus_spool.git
cd propus_spool
```

2. **Create virtual environment**:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**:
```bash
pip install -r requirements.txt
```

4. **Configure**:
```bash
cp .env.example .env
nano .env
```

5. **Run application**:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Production with Gunicorn

For production, use Gunicorn:

```bash
pip install gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### Systemd Service

Create `/etc/systemd/system/propus_spool.service`:

```ini
[Unit]
Description=Propus Spool Service
After=network.target

[Service]
Type=simple
User=propus
WorkingDirectory=/opt/propus_spool
Environment="PATH=/opt/propus_spool/venv/bin"
ExecStart=/opt/propus_spool/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable propus_spool
sudo systemctl start propus_spool
```

---

## Configuration

### Environment Variables

Key configuration options:

```bash
# Database
DATABASE_URL=postgresql://user:pass@host/db
# Or: sqlite:///./propus_spool.db

# Spoolman Integration
SPOOLMAN_URL=http://spoolman:8000
SPOOLMAN_API_KEY=your_key_here

# Features
WRITE_MODE=false  # Enable NFC writing
PUSH_REMAINING_TO_SPOOLMAN=true  # Auto-push weights

# Application
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR
API_HOST=0.0.0.0
API_PORT=8000

# CORS (for web frontends)
CORS_ORIGINS=*  # Or: https://app.example.com,https://other.com
```

### Reverse Proxy

#### Nginx

```nginx
server {
    listen 80;
    server_name spool.example.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

#### Traefik (Docker Labels)

```yaml
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.propus.rule=Host(`spool.example.com`)"
  - "traefik.http.routers.propus.entrypoints=websecure"
  - "traefik.http.routers.propus.tls.certresolver=letsencrypt"
```

---

## Database Options

### PostgreSQL (Recommended for Production)

Best for multiple users, high traffic, or production deployments.

```bash
DATABASE_URL=postgresql://propus:propus@localhost:5432/propus_spool
```

### SQLite (Good for Single User)

Simplest option, good for Raspberry Pi or single-user setups.

```bash
DATABASE_URL=sqlite:///./propus_spool.db
```

SQLite is automatically used if no PostgreSQL connection is available.

---

## Monitoring

### Health Checks

The `/health` endpoint provides system status:

```bash
curl http://localhost:8000/health
```

### Logs

Docker:
```bash
docker-compose logs -f app
```

Systemd:
```bash
journalctl -u propus_spool -f
```

### Metrics

Future versions will include Prometheus metrics at `/metrics`.

---

## Troubleshooting

### Port Already in Use

Change port in `.env` or `docker-compose.yml`:
```yaml
ports:
  - "8080:8000"  # Use port 8080 instead
```

### Database Connection Failed

Check database is running:
```bash
docker-compose ps db
```

Test connection:
```bash
docker-compose exec db psql -U propus -d propus_spool
```

### Permission Denied

Ensure proper file ownership:
```bash
sudo chown -R 1000:1000 /path/to/propus_spool
```

---

## Security Considerations

1. **Change default credentials** in production
2. **Use HTTPS** with reverse proxy
3. **Restrict CORS_ORIGINS** to trusted domains
4. **Keep API_KEY secret** for Spoolman integration
5. **Regular backups** of database
6. **Update regularly** for security patches

---

## Support

- GitHub Issues: https://github.com/Janez76/propus_spool/issues
- Documentation: See README.md
- API Docs: http://your-server:8000/docs
