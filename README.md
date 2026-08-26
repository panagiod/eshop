# Harbor E-Shop

A **free-to-host** demo store: Python FastAPI, SQLite, and a responsive storefront.

Browse products, add to cart, checkout — no payment processor, **$0/month** on Render's free instance.

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/panagiod/eshop)

That button is the only step to go live. Sign in with GitHub, keep the **Free** plan, click Apply. After the first deploy the shop is at `https://harbor-eshop.onrender.com` (Render may add a suffix).

No credit card. No Kubernetes. No paid add-ons.

> Free instances sleep after ~15 minutes idle (~1 minute wake). SQLite in `/tmp` resets on redeploy because the free plan has no disk.

## Local run (optional)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
uvicorn src.main:app --reload --port 8080
```

Open http://localhost:8080

## What you get

| Feature | Details |
|---------|---------|
| Product catalog | 12 seeded products across 6 categories |
| Shopping cart | Session cookie while you browse |
| Shipping | $5.99 under $75, free at $75+ |
| Checkout | Shipping details + order confirmation |
| Order lookup | `/order/{id}` after checkout |
| Cost | $0 on Render Free (750 instance hours/month) |

## Environment variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `PORT` | set by Render | HTTP listen port |
| `SESSION_SECRET` | auto-generated on Render | Signs session cookies |
| `SHOP_NAME` | `Harbor` | Store branding |
| `DATA_DIR` | `/tmp/eshop-data` | SQLite directory |

## License

MIT — use freely for learning and demos.
