# Website Project

A Flask web application containerized with Docker and deployed on Kubernetes. Features four UI pages and API endpoints for health checks and pod identification — useful for observing load balancing across replicas.

---

## Prerequisites

- Python 3.12+
- Docker
- [kind](https://kind.sigs.k8s.io/docs/user/quick-start/#installation) (Kubernetes in Docker)
- [kubectl](https://kubernetes.io/docs/tasks/tools/)

## Quick Start

### Local (dev server)
```bash
pip install -r requirements.txt
python app.py
# http://localhost:8080
```

### Docker
```bash
docker build -t website:latest .
docker run -p 8080:8080 website:latest
```

### Kubernetes (kind)
```bash
kind create cluster --config kind-config.yaml
docker build -t website:latest .
kind load docker-image website:latest   # required: imagePullPolicy is Never
kubectl apply -f k8s-deployment.yaml
# http://localhost:8080
```

### Verify
```bash
curl http://localhost:8080/health
curl http://localhost:8080/api/info
```

---

## Architecture Overview

### System Topology

```
  Browser / curl
       │
       │ HTTP :8080
       ▼
┌──────────────────────────────────────────────────────────────┐
│  kind cluster (Docker-in-Docker)                             │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  control-plane node                                    │  │
│  │                                                        │  │
│  │   hostPort 8080 ──► containerPort 30080                │  │
│  │                              │                         │  │
│  │                              ▼                         │  │
│  │        ┌─────────────────────────────────┐             │  │
│  │        │  Service: website (NodePort)    │             │  │
│  │        │  port 80 → targetPort 8080      │             │  │
│  │        │  nodePort 30080                 │             │  │
│  │        └──────────┬──────────────────────┘             │  │
│  │                   │ load balances across pods          │  │
│  │         ┌─────────┼─────────┐                          │  │
│  │         ▼         ▼         ▼                          │  │
│  │      ┌──────┐  ┌──────┐  ┌──────┐                     │  │
│  │      │ Pod  │  │ Pod  │  │ Pod  │  ← 3 replicas       │  │
│  │      │  1   │  │  2   │  │  3   │                     │  │
│  │      └──────┘  └──────┘  └──────┘                     │  │
│  │                                                        │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

### Pod Internals

```
┌─────────────────────────────────────────────────────┐
│  Pod (website container)                            │
│                                                     │
│  ┌───────────────────────────────────────────────┐  │
│  │  Gunicorn  (WSGI server, :8080)               │  │
│  │      │                                        │  │
│  │      ▼                                        │  │
│  │  Flask app  (app.py)                          │  │
│  │      │                                        │  │
│  │      ├── Pages (Jinja2 templates/)            │  │
│  │      │     ├── /            → index.html      │  │
│  │      │     ├── /exchange    → exchange.html   │  │
│  │      │     ├── /charts      → charts.html     │  │
│  │      │     └── /pool        → pool.html       │  │
│  │      │                                        │  │
│  │      └── API Endpoints                        │  │
│  │            ├── /health      → {"status","pod"}│  │
│  │            ├── /api/info    → system metadata │  │
│  │            └── /api/pod     → {"pod": name}   │  │
│  └───────────────────────────────────────────────┘  │
│                                                     │
│  Health probes → /health (liveness + readiness)     │
│  Security: non-root user, no privilege escalation   │
└─────────────────────────────────────────────────────┘
```

### Docker Image (Multi-Stage Build)

```
┌─────────────────────────────┐
│  Stage 1: builder           │
│  python:3.12-slim           │
│                             │
│  pip install requirements   │
│  → /opt/venv                │
└────────────┬────────────────┘
             │  COPY --from=builder /opt/venv
             ▼
┌─────────────────────────────┐
│  Stage 2: runtime           │
│  python:3.12-slim           │
│                             │
│  /opt/venv   (deps only)    │
│  app.py                     │
│  templates/                 │
│                             │
│  USER appuser (non-root)    │
│  CMD gunicorn :8080         │
└─────────────────────────────┘
```

### Request Flow

```
curl localhost:8080/exchange

  Host :8080
     │
     ▼ (kind port mapping)
  Node :30080
     │
     ▼ (NodePort service)
  Pod :8080  ← one of three replicas (round-robin)
     │
     ▼
  Gunicorn worker
     │
     ▼
  Flask route /exchange
     │
     ▼
  render_template("exchange.html", hostname=HOSTNAME)
     │
     ▼
  HTML response  (hostname in page identifies which pod responded)
```

---

## Endpoints

| Method | Path       | Description                                  |
|--------|------------|----------------------------------------------|
| GET    | `/`        | Home page                                    |
| GET    | `/exchange`| Exchange page                                |
| GET    | `/charts`  | Charts page                                  |
| GET    | `/pool`    | Pool page                                    |
| GET    | `/health`  | `{"status":"healthy","pod":"<hostname>"}`    |
| GET    | `/api/info`| Hostname, Python version, platform, uptime  |
| GET    | `/api/pod` | `{"pod":"<hostname>"}`                       |

---

## Tech Stack

| Layer              | Technology                  |
|--------------------|-----------------------------|
| Language           | Python 3.12                 |
| Web framework      | Flask 3.0.0                 |
| WSGI server        | Gunicorn 21.2.0             |
| Templating         | Jinja2                      |
| Container runtime  | Docker (multi-stage)        |
| Orchestration      | Kubernetes (kind for local) |

---

## Resource Limits (per pod)

| Resource | Request | Limit |
|----------|---------|-------|
| Memory   | 128 Mi  | 256 Mi|
| CPU      | 100 m   | 500 m |

---

## Observing Load Balancing

Each pod reports its own hostname. Poll `/api/pod` to see requests round-robin across replicas:

```bash
for i in $(seq 1 6); do curl -s http://localhost:8080/api/pod; echo; done
```

Expected output rotates across the three pod hostnames.
