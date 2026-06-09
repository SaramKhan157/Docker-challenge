# Docker Challenge — Multi-Container Flask App

This is part of my DevOps learning portfolio. The goal was to containerise a Flask web application, connect it to a Redis database for persistent visit counting, and put Nginx in front of it as a load balancer — then scale Flask to three instances and verify everything still worked.

---

## What I Built

A multi-container application with four moving parts:

| Container | Role |
|-----------|------|
| `flask` (x3) | Python web app serving two routes |
| `redis` | In-memory store that persists the visit count |
| `nginx` | Reverse proxy that load balances across the three Flask instances |

**Routes:**
- `GET /` — returns a welcome message
- `GET /count` — increments and returns a visit counter stored in Redis

The whole thing is wired together with Docker Compose and can be spun up with a single command.

---

## Project Structure

```
Docker-challenge/
├── app.py                  # Flask application
├── Dockerfile              # Flask image
├── nginx.Dockerfile        # Custom Nginx image (config baked in)
├── nginx.conf              # Nginx reverse proxy config
├── docker-compose.yml      # Orchestrates all services
├── requirements.txt        # Python dependencies
└── doc/
    └── screenshots/        # App running, scaling, and verification
```

---

## How to Run It

```bash
# Start everything (1 Flask instance by default)
docker compose up --build -d

# Scale Flask to 3 instances
docker compose up -d --scale flask=3

# Check everything is running
docker compose ps

# Test it
curl http://localhost:5001
curl http://localhost:5001/count

# Tear it down (Redis data is preserved in a volume)
docker compose down
```

---

## My Approach

I started simple — get Flask talking to Redis, then add Nginx on top, then think about scaling.

The Compose file uses a health check on Redis so Flask doesn't try to connect before the database is actually ready. Nginx gets its config baked into a custom image rather than mounted as a file (more on why below). Flask runs under Gunicorn instead of the built-in dev server so it can actually handle real traffic when scaled.

For scaling to work without port conflicts, Flask containers don't expose any ports directly to the host — only Nginx does (port 5001). Docker's internal DNS handles routing: when Nginx proxies to `flask:5000`, Docker automatically round-robins across all three instances.

---

## What I Learned

- **Docker Compose is more than just a convenience wrapper.** `depends_on` with health checks, named volumes, and service discovery via DNS are genuinely powerful once you understand them.
- **Gunicorn matters.** Flask's built-in server is single-threaded and not meant for anything beyond local debugging. Swapping it out for Gunicorn was a small change that made a real difference.
- **Container networking clicks once you stop thinking in terms of IPs.** Services find each other by name. That's it. It took me a while to trust that, but it just works.
- **Volumes are what make persistence real.** Without the `redis_data` volume, the visit counter resets to zero every time you restart. With it, it picks up exactly where it left off.

---

## Challenges and How I Solved Them

**1. Docker Desktop's storage got corrupted**

At some point Docker Desktop stopped responding entirely — `docker ps` would hang and never return. Turned out the VM storage had gone into a bad state.

Fixed it by force-quitting Docker, deleting the corrupted VM directory, and letting Docker rebuild it fresh:

```bash
pkill -9 -f Docker
rm -rf ~/Library/Containers/com.docker.docker/Data/vms
# then reopen Docker Desktop
```

**2. Nginx kept crashing with a `pread() Resource deadlock` error**

After Docker recovered, Nginx would start and immediately exit with:

```
pread() "/etc/nginx/conf.d/default.conf" failed (35: Resource deadlock would occur)
```

This turned out to be a macOS-specific bug with Docker Desktop's VirtioFS file sharing. When you bind-mount a single file into a container, the filesystem layer can deadlock on reads.

The fix was to stop mounting `nginx.conf` as a volume and instead bake it into a custom Nginx image at build time:

```dockerfile
FROM nginx:alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
```

Not an obvious fix — I had to dig through the error code (`EDEADLK = 35` on Darwin) to work out it was a host filesystem issue rather than anything wrong with the config itself.

**3. Flask was only showing one instance after scaling**

When I first ran `--scale flask=3`, `docker compose ps` showed three containers, but I wasn't sure the load balancing was actually working. Verified it by running a loop that printed the hostname of each container handling a request:

```bash
for i in {1..6}; do docker exec docker-challenge-flask-$((i%3+1)) hostname; done
```

Three different hostnames cycling in order — confirmed.

---

## Verification Checklist

```bash
# 1. All five containers running
docker compose ps

# 2. Welcome route
curl http://localhost:5001
# → <h1>Welcome to the CoderCo Containers Challenge!</h1>

# 3. Visit counter increments
curl http://localhost:5001/count   # → Visit count: N
curl http://localhost:5001/count   # → Visit count: N+1
curl http://localhost:5001/count   # → Visit count: N+2

# 4. Redis persists across restarts
docker compose down && docker compose up -d
curl http://localhost:5001/count   # → continues from where it left off

# 5. Environment variables set correctly
docker compose exec flask env | grep REDIS
# → REDIS_HOST=redis
# → REDIS_PORT=6379

# 6. Scales to 3 instances without port conflicts
docker compose up -d --scale flask=3
docker compose ps   # → flask-1, flask-2, flask-3 all Up
```

---

## Screenshots

See `doc/screenshots/` for the app running, the containers listed, and the scaling verification.

---

## Intro Task

Before this challenge I built a simpler Flask + MySQL app to get comfortable with Dockerfiles and Compose basics. That lives in the `intro-tasks/` folder if you want to see where this started.
