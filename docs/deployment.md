# 369 Deployment Guide

## Backyard Scale (Docker Compose)

### Prerequisites
- Raspberry Pi 4B (4GB+) with 64-bit Raspberry Pi OS
- Docker and Docker Compose installed
- Network connectivity for weather API

### Steps

```bash
# 1. Clone the repo
git clone https://github.com/theorjiugovictor/369.git
cd 369

# 2. Configure environment
cp .env.example .env
# Edit .env — set ANTHROPIC_API_KEY if using awareness agent

# 3. Start infrastructure
docker compose up -d

# 4. Run scheduler in mock mode (no hardware)
python -m core.scheduler --config config/backyard.yaml --mock

# 5. Or run with real hardware
python -m core.scheduler --config config/backyard.yaml
```

### Verify
```bash
# Check services
docker compose ps

# Test API
curl http://localhost:8369/health

# View logs
docker compose logs -f api
```

## Edge Deployment (Raspberry Pi)

Use the lightweight compose file:

```bash
docker compose -f docker-compose.edge.yml up -d
```

This uses:
- Reduced memory limits for Redis (128MB)
- Single uvicorn worker
- No dashboard service

## Village Scale (K3s)

### Prerequisites
- 3+ nodes (Pi 4 or x86)
- K3s installed on all nodes
- Shared storage (NFS or Longhorn)

### Architecture

```
┌─────────────────────────────────────────┐
│              K3s Cluster                  │
│                                           │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐ │
│  │  Node 1 │  │  Node 2 │  │  Node 3 │ │
│  │ Redis   │  │ Postgres│  │  API    │ │
│  │ MQTT    │  │         │  │ Agents  │ │
│  └─────────┘  └─────────┘  └─────────┘ │
└─────────────────────────────────────────┘
```

### Deployment

```bash
# Apply Kubernetes manifests (TODO: create helm chart)
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/redis.yaml
kubectl apply -f k8s/postgres.yaml
kubectl apply -f k8s/mqtt.yaml
kubectl apply -f k8s/api.yaml
kubectl apply -f k8s/scheduler.yaml
```

## Monitoring

### Health Endpoints
- `GET /health` — API health
- `GET /api/agents` — Agent statuses
- `GET /api/insights/alerts` — Active alerts

### Logs
All components log to stdout in structured format. Use Docker logs or K8s logging:

```bash
# Docker
docker compose logs -f --tail=100

# K3s
kubectl logs -f deployment/369-scheduler
```

## Backup

### PostgreSQL
```bash
docker compose exec postgres pg_dump -U 369 three_six_nine > backup.sql
```

### Redis
Redis uses AOF persistence — data survives restarts. For manual backup:
```bash
docker compose exec redis redis-cli BGSAVE
```
