# Print Me Maybe (Hetzner)

Cheap, persistent copy of the Print Me Maybe shop: **Hetzner VPS + your domain + Stripe Checkout + Resend**.

The **current Render shop is unchanged** at [github.com/panagiod/eshop](https://github.com/panagiod/eshop) (`main`, live [print-me-maybe.onrender.com](https://print-me-maybe.onrender.com)). Do not merge this tree into that `main` branch.

This tree is meant to become **https://github.com/panagiod/print-me-maybe** (create that empty public repo with no README, then push this code as `main` there).

**Fixed cost:** about **€8/month** (Hetzner CX23 + VAT) + **~$11/year** domain. Cards: Stripe **1.5% + €0.25** on EEA cards, **no monthly Stripe fee**.

## Contents

- [What this project is](#what-this-project-is)
- [Go live (cheapest stack)](#go-live-cheapest-stack)
- [Features](#features)
- [Stack](#stack)
- [Repository layout](#repository-layout)
- [Local development](#local-development)
- [Tests and CI](#tests-and-ci)
- [Configuration](#configuration)
- [Shop behaviour](#shop-behaviour)
- [Studio admin](#studio-admin)
- [Order emails](#order-emails)
- [Security](#security)
- [Backups](#backups)
- [License](#license)

## What this project is

| This project **does** | This project **does not** |
|-----------------------|---------------------------|
| Keep orders and photos on the Hetzner disk (`/var/lib/eshop`) | Wipe data on sleep (Render Free does that) |
| Take **card payment** via Stripe Checkout when `STRIPE_SECRET_KEY` is set | Charge a monthly Stripe or Shopify fee |
| Email the studio via Resend after you verify **your** domain | Send from `onboarding@resend.dev` or `outlook.com` |

Custom names/files still go over **Instagram DM**.

## Go live (cheapest stack)

1. **GitHub** — create empty public repo **panagiod/print-me-maybe** (no README, no license). Push this code as `main`.
2. **Domain** — Cloudflare Registrar, e.g. `printmemaybe.com` (~$11/year).
3. **Server** — [Hetzner Cloud](https://www.hetzner.com/cloud) **CX23**, location Falkenstein or Helsinki, Ubuntu 24.04, with an IPv4 address. ~€5.49/month + EU VAT.
4. **DNS** — A record `@` and `www` → the server IPv4. Wait until it resolves.
5. **Install** (SSH as root):

   ```bash
   git clone https://github.com/panagiod/print-me-maybe.git /opt/eshop
   sudo bash /opt/eshop/deploy/install.sh
   nano /etc/eshop.env   # SHOP_URL, Stripe, Resend
   nano /etc/caddy/Caddyfile   # your real domain
   systemctl restart eshop
   systemctl reload caddy
   ```

   `install.sh` generates `SESSION_SECRET` and `ADMIN_PASSWORD` and prints the admin password once. Caddy gets HTTPS automatically after DNS points at the server.
6. **Stripe** — [dashboard.stripe.com](https://dashboard.stripe.com) → activate payments, EUR, copy the **secret** key (`sk_live_…` or `sk_test_…` for a dry run) into `STRIPE_SECRET_KEY`. Checkout redirects to Stripe and only creates the order after `payment_status=paid`.
7. **Resend** — [resend.com/domains](https://resend.com/domains) → add **your** domain (not `onrender.com`) → paste DNS records → wait for **Verified** → set `RESEND_FROM=Print Me Maybe <orders@your-domain>`.
8. Check `https://your-domain/health` — `"payments": true`, `"persistent": true`. Place a **test** card order (`ACCT-000015`), reboot the VPS, confirm the order is still in studio.

Until `STRIPE_SECRET_KEY` is set, checkout stays a no-card demo (same as the Render shop).

## Features

- Catalog with category filter (3D Prints / Laser Engraving)
- Session cart; quantity cannot exceed stock
- Shipping €3.50 under €25, free at €25+
- Checkout: name, email, address, then **Stripe Checkout** when `STRIPE_SECRET_KEY` is set
- Customer order page at `/order/{unguessable-token}`
- Studio at `/admin` (not linked in public nav): orders, notes, cancel/restock, add product + photo
- Background order email via [Resend](https://resend.com) (needs a domain you own — see [Order emails](#order-emails))
- JSON catalog at `GET /api/products`
- Liveness at `GET /health` (`mail`, `payments`, `persistent`)

## Stack

- **Python 3.12**, [FastAPI](https://fastapi.tiangolo.com/), Uvicorn
- **Jinja2** HTML templates + `static/css`
- **SQLite** under `DATA_DIR` (local default `/tmp/eshop-data`; production `/var/lib/eshop`)
- Signed **session cookies** for cart and studio login
- GitHub Actions CI: pytest + smoke `curl` of `/health` and home

## Repository layout

```
src/                 FastAPI app
  main.py            Storefront routes (home, product, cart, checkout, health)
  admin.py           Studio login, orders, stock, test email
  store.py           Products, cart lines, place_order
  db.py              SQLite schema and DATA_DIR
  models.py          Product/Order types, EUR formatting, shipping rules
  seed.py            Catalog copied from Instagram listings
  payments.py        Stripe Checkout
  notify.py          Resend/SMTP mail, attack alerts
  ratelimit.py       Per-IP limits
  security.py        Secrets, HTTPS cookies, CSP/HSTS
  uploads.py         Admin product photos
templates/           HTML (base, shop, cart, checkout, admin)
static/              CSS and seed product images
tests/               pytest
deploy/              Hetzner systemd unit, Caddyfile, install.sh, env.example, backup.sh
.github/workflows/ci.yml
```

## Local development

Requires Python 3.12+.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
uvicorn src.main:app --reload --port 8080
```

Open [http://localhost:8080](http://localhost:8080). Studio: [http://localhost:8080/admin/login](http://localhost:8080/admin/login) — password `printmemaybe` unless you set `ADMIN_PASSWORD`.

SQLite and uploaded photos go to `DATA_DIR` (default `/tmp/eshop-data`).

## Tests and CI

```bash
python3 -m pytest tests/ -v
```

GitHub Actions (`.github/workflows/ci.yml`) runs on every pull request and on push to `main`: install deps, pytest, then boot Uvicorn and `curl` `/health` and `/`.

## Configuration

Set these in `/etc/eshop.env` on the server (`deploy/env.example`). Never commit secrets or paste API keys into git/chat. After changes: `systemctl restart eshop`.

| Variable | Default | Purpose |
|----------|---------|---------|
| `ENV` | unset locally; `production` on the VPS | Requires `SESSION_SECRET` and `ADMIN_PASSWORD` |
| `SESSION_SECRET` | generated by `install.sh` | Signs session cookies; **required** in production |
| `ADMIN_PASSWORD` | `printmemaybe` locally; generated by `install.sh` | Studio login |
| `SESSION_HTTPS_ONLY` | on when `ENV=production` | Secure cookie flag |
| `SHOP_NAME` | `Print Me Maybe` | Branding |
| `SHOP_URL` | your `https://` domain | Links in emails |
| `DATA_DIR` | `/tmp/eshop-data` locally; `/var/lib/eshop` in production | SQLite + uploaded photos |
| `NOTIFY_EMAIL` | `dimitrioupanagiotis@outlook.com` | Inbox for order and attack alerts |
| `RESEND_API_KEY` | empty (mail skipped) | Resend API key (`re_…`) |
| `RESEND_FROM` | `Print Me Maybe <beth.t@example.com>` | Must be an address on a **verified** Resend domain |
| `STRIPE_SECRET_KEY` | empty (demo checkout, no card) | Stripe secret key (`sk_test_…` or `sk_live_…`) |
| `ATTACK_ALERT_COOLDOWN` | `3600` | Seconds between similar security emails |
| `NOTIFY_SYNC` | unset | Set to `1` in tests so checkout waits for mail |
| `RATE_LIMIT_DISABLED` | unset | Set to `1` to turn limits off (tests) |

`GET /health` includes `"mail"` and `"payments"` (booleans, no secrets) and `"persistent"` (true when `DATA_DIR` is not under `/tmp`).

Two dashboards that are easy to mix up:

| Site | URL | Role |
|------|-----|------|
| **Hetzner** | https://console.hetzner.cloud | Runs the website (this server) |
| **Stripe** | https://dashboard.stripe.com | Card payments |
| **Resend** | https://resend.com | Sends email |
| **Render** | https://dashboard.render.com | The *old* Free shop only (`panagiod/eshop`) |

## Shop behaviour

**Catalog.** Seed SKUs live in `src/seed.py` (names, euro prices, photos from public Instagram where a price was named). On boot, seed rows are upserted **by slug**. Stock changes and products added in studio are kept; seed does not reset quantity.

**Cart.** Stored in the signed session cookie (7 days). Add/update quantity is capped at remaining stock. Zero stock hides a product from the shop.

**Checkout.** POST `/checkout` with name, email, shipping address. If Stripe is configured, the browser goes to Stripe Checkout; the order is created only on `GET /pay/success` after Stripe reports `payment_status=paid`. The cart is also stored in Stripe metadata so a lost cookie cannot drop a paid order. Without Stripe, checkout is the old no-card demo.

**Customer order URL.** `/order/{lookup_token}` — random token, not the numeric id.

## Studio admin

Public nav does not advertise `/admin`. Login: `/admin/login` on your domain.

| Page | What it does |
|------|----------------|
| `/admin/orders` | Filter by status; Paid/Unpaid; **Send test email** |
| `/admin/orders/{id}` | Status, notes, cancel (restock) / reopen (deduct again) |
| `/admin/stock` | Add product (name, description, EUR price, category, photo, qty); set stock |

Order statuses: New → In progress → Ready to ship → Shipped, plus Cancelled.

Uploaded photos are served from `/media/products/...` and stored under `DATA_DIR/product-images`.

## Order emails

New checkouts and blocked login/checkout floods email **dimitrioupanagiotis@outlook.com**. Checkout still succeeds if mail fails.

### What you cannot add in Resend → Domains

These names are not yours. Verification will fail:

- `print-me-maybe.onrender.com` / `onrender.com` — Render’s web address (old shop only)
- `outlook.com` — belongs to Microsoft (Outlook can still *receive*)
- `resend.dev` / `example.com` / `beth.t@example.com` — Resend shared test sender
- `@print.me.maybe` — Instagram, not a domain

A domain is a name you **buy**, such as `printmemaybe.com`. Mail then sends as `orders@printmemaybe.com` and can still land in Outlook.

### When you have bought a domain

Replace `printmemaybe.com` with the name you bought.

1. Buy a domain (Cloudflare Registrar is usually cheapest for `.com`).
2. [resend.com/domains](https://resend.com/domains) → **Add Domain** → `printmemaybe.com` (no `https://`).
3. Copy every DNS record Resend shows (TXT / MX) into Cloudflare DNS. Save. Do not skip rows.
4. Wait until Resend shows **Verified**.
5. On the server, set `RESEND_FROM` to `Print Me Maybe <orders@printmemaybe.com>` in `/etc/eshop.env`.
6. Confirm `NOTIFY_EMAIL` is `dimitrioupanagiotis@outlook.com`.
7. `systemctl restart eshop`
8. Studio **Orders** → **Send test email**.
9. Resend **Emails → Sending** and **Logs** (not **Receiving**): **Delivered**, not 403.
10. Outlook: search Inbox, Junk, Other, Focused. Mark Not junk the first time.

Attack alerts (blocked studio login or checkout flood) email at most once per hour per type.

## Security

- `ENV=production` refuses to boot without `SESSION_SECRET` and `ADMIN_PASSWORD`
- Session cookies: `SameSite=lax`, HTTPS-only in production
- Studio password compared with SHA-256 + `hmac.compare_digest` (failed logins are logged, never the password)
- Security headers: `nosniff`, `DENY` framing, Referrer-Policy, Permissions-Policy, CSP, HSTS on HTTPS
- Customer orders use `lookup_token`, not sequential public URLs
- `/etc/eshop.env` is mode `640`, owned by `root:eshop`

Rate limits (in-memory, per instance, by IP):

| Action | Default |
|--------|---------|
| Pages | 240 / minute |
| Studio login POST | 5 / 15 minutes |
| Checkout POST | 12 / hour |
| Cart POST | 60 / minute |

`/health`, `/static/`, `/media/` are exempt. HTTP 429 includes `Retry-After`.

## Backups

SQLite lives at `/var/lib/eshop/eshop.db`. Nightly local copies:

```bash
15 3 * * * /opt/eshop/deploy/backup.sh
```

Copy a backup off the server occasionally (`scp`) or enable a Hetzner snapshot (extra cost). Reboot the VPS after a test order and confirm studio still shows it.

## License

[MIT](LICENSE) — use freely for learning and demos.
