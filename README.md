# Harbor E-Shop

A free-to-host demo e-commerce store built with **Python FastAPI**, **SQLite**, and a responsive storefront UI.

Browse products, add to cart, and complete checkout — no payment processor required (demo mode).

## Features

| Feature | Details |
|---------|---------|
| Product catalog | 12 seeded products across 6 categories |
| Shopping cart | Session-based, persists while you browse |
| Checkout | Collects shipping details and creates orders |
| API | `GET /api/products` JSON endpoint |
| Container | Non-root Docker image ready for any host |
| Kubernetes | Kustomize manifests under `deploy/` |

## Quick start (local)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt

# Run the dev server
uvicorn src.main:app --reload --port 8080
```

Open http://localhost:8080

## Free hosting on Render

1. Push this repo to GitHub (`panagiod/eshop` or your fork).
2. Sign up at [render.com](https://render.com) (free tier).
3. **New → Blueprint** → connect your GitHub repo.
4. Render reads `render.yaml` and deploys the Docker service.
5. Your shop is live at `https://harbor-eshop.onrender.com` (or similar).

> **Note:** Free tier spins down after inactivity (~50 s cold start). SQLite data resets on redeploy because free tier has no persistent disk.

Set `SESSION_SECRET` in Render dashboard if you rotate secrets.

## Create the GitHub repo

From this directory:

```bash
git init
git add .
git commit -m "feat: harbor e-shop with free Render hosting"

# Create repo under your account (requires gh CLI as panagiod)
gh repo create panagiod/eshop --public --source=. --push
```

Enable **Settings → Actions → Workflow permissions → Read and write** so release tags can push to GHCR.

## Release workflow

Tag a version to build and push a container image:

```bash
git tag v0.1.0
git push origin v0.1.0
```

Image: `ghcr.io/panagiod/eshop:v0.1.0`

## Deploy on Kubernetes (optional)

If you use the [panagiod/infra](https://github.com/panagiod/infra) platform:

1. Add an Argo CD Application pointing at `deploy/overlays/staging` in this repo.
2. Or copy manifests into `gitops/apps/eshop/` in the infra repo.

See [application-project.md](https://github.com/panagiod/infra/blob/main/docs/applications/application-project.md) in infra.

## Environment variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `PORT` | `8080` | HTTP listen port |
| `SESSION_SECRET` | dev placeholder | Signs session cookies — **set in production** |
| `SHOP_NAME` | `Harbor` | Store branding in the UI |
| `DATA_DIR` | `/tmp/eshop-data` | SQLite database directory |

## Project structure

```
src/           FastAPI application
templates/     Jinja2 HTML pages
static/        CSS assets
deploy/        Kubernetes Kustomize overlays
tests/         Pytest smoke tests
render.yaml    Render Blueprint for free hosting
```

## License

MIT — use freely for learning and demos.
