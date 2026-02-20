# Propus Spool - Filament Management System

A filament management system for 3D printing with spool tracking, AMS integration, and multi-user support.

---

## Deutsch

### Schnellstart (Docker)

```bash
docker run -d \
  --name propus-spool-app \
  --restart unless-stopped \
  -p 8083:8000 \
  -v propus_spool_data:/app/data \
  propus-spool:latest
```

Die Anwendung ist dann unter http://localhost:8083 erreichbar.

Default EMail: admin@example.com
Default Passwort: admin123

### Docker Container selber bauen

#### Voraussetzungen

- Docker
- Docker Buildx mit Multi-Architektur-Unterstuetzung (fuer ARM/AMD)

#### Build

```bash
# Clone repo
git clone https://github.com/Janez76/propus_spool.git && cd propus_spool

# Image bauen
docker build -t propus-spool:latest .

# Oder mit docker-compose
docker-compose up --build
```

#### Ausfuehren

```bash
# Container starten
docker run -d \
  --name propus-spool-app \
  --restart unless-stopped \
  -p 8083:8000 \
  -v propus_spool_data:/app/data \
  -e DEBUG=false \
  -e SECRET_KEY=your-secret-key \
  -e CSRF_SECRET_KEY=your-csrf-secret \
  -e ADMIN_EMAIL=admin@example.com \
  -e ADMIN_PASSWORD=your-admin-password \
  propus-spool:latest
```

### Lokale Entwicklung

#### Voraussetzungen

- Python 3.11+
- Node.js 18+
- uv (Python Package Manager)

#### Backend starten

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload
```

Das Backend ist unter http://localhost:8000 verfuegbar.

#### Frontend starten

```bash
cd frontend
npm install
npm run dev
```

Das Frontend ist unter http://localhost:4321 verfuegbar.

#### Frontend fuer Produktion bauen

```bash
cd frontend
npm run build
```

Die statischen Dateien liegen in `frontend/dist/`.

### Umgebungsvariablen

Erstelle eine `.env` Datei im Projektverzeichnis. Verwende `.env.example` als Vorlage:

```bash
# Datenbank-Konfiguration
# SQLite (Standard):
DATABASE_URL=sqlite+aiosqlite:///./propus_spool.db

# PostgreSQL:
# DATABASE_URL=postgresql+asyncpg://username:password@hostname:5432/database
```

#### Secrets generieren

```bash
openssl rand -hex 32
```

### Technologie

**Backend:**
- FastAPI
- SQLAlchemy 2.0 + Alembic
- Python 3.11+

**Frontend:**
- Astro
- Static Build

### Lizenz

MIT

---

## English

### Quick Start (Docker)

```bash
docker run -d \
  --name propus-spool-app \
  --restart unless-stopped \
  -p 8083:8000 \
  -v propus_spool_data:/app/data \
  propus-spool:latest
```

The application will be available at http://localhost:8083.

### Build Docker Container Yourself

#### Prerequisites

- Docker
- Docker Buildx with multi-architecture support (for ARM/AMD)

#### Build

```bash
# Clone repo
git clone https://github.com/Janez76/propus_spool.git && cd propus_spool

# Build image
docker build -t propus-spool:latest .

# Or with docker-compose
docker-compose up --build
```

#### Run

```bash
docker run -d \
  --name propus-spool-app \
  --restart unless-stopped \
  -p 8083:8000 \
  -v propus_spool_data:/app/data \
  -e DEBUG=false \
  -e SECRET_KEY=your-secret-key \
  -e CSRF_SECRET_KEY=your-csrf-secret \
  -e ADMIN_EMAIL=admin@example.com \
  -e ADMIN_PASSWORD=your-admin-password \
  propus-spool:latest
```

### Local Development

#### Prerequisites

- Python 3.11+
- Node.js 18+
- uv (Python package manager)

#### Start Backend

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload
```

#### Start Frontend

```bash
cd frontend
npm install
npm run dev
```

### License

MIT
