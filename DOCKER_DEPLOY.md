# How to Install Propus Spool via Docker

This guide explains how to run the Propus Spool application using a Docker image.

---

## English

### Prerequisites

- You must have **Docker** installed on your system.

### Installation Steps

```bash
docker run -d \
  --name propus-spool-app \
  --restart unless-stopped \
  -p 8000:8000 \
  -v propus_spool_data:/app/data \
  propus-spool:latest
```

### Accessing the Application

- **URL:** http://localhost:8000
- **Default Username:** `admin@example.com`
- **Default Password:** `admin123`

It is strongly recommended to change this password after your first login.

### Managing the Container
- **To stop the container:** `docker stop propus-spool-app`
- **To start the container again:** `docker start propus-spool-app`
- **To view logs:** `docker logs -f propus-spool-app`

---

## Deutsch

### Voraussetzungen

- Sie muessen **Docker** auf Ihrem System installiert haben.

### Installationsschritte

```bash
docker run -d \
  --name propus-spool-app \
  --restart unless-stopped \
  -p 8000:8000 \
  -v propus_spool_data:/app/data \
  propus-spool:latest
```

### Zugriff auf die Anwendung

- **URL:** http://localhost:8000
- **Standard-Benutzername:** `admin@example.com`
- **Standard-Passwort:** `admin123`

### Container verwalten
- **Container stoppen:** `docker stop propus-spool-app`
- **Container wieder starten:** `docker start propus-spool-app`
- **Logs ansehen:** `docker logs -f propus-spool-app`
