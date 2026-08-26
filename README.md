# Print Me Maybe

Small e-shop for **3D prints** ([@print.me.maybe](https://www.instagram.com/print.me.maybe/)) and **laser engraving** ([@lasercraft.27](https://www.instagram.com/lasercraft.27/)). Made in Cyprus. Prices in **EUR**.

This repository is a FastAPI + SQLite storefront with a session cart, demo checkout (no card payments), and a password-protected studio for orders and stock. Production is meant to run on [Render](https://render.com) **Starter** with a persistent disk (~$7.25/month) so orders survive redeploys.

**Live shop:** [https://print-me-maybe.onrender.com](https://print-me-maybe.onrender.com)

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/panagiod/eshop)

## Contents

- [What this project is](#what-this-project-is)
- [Features](#features)
- [Stack](#stack)
- [Repository layout](#repository-layout)
- [Local development](#local-development)
- [Tests and CI](#tests-and-ci)
- [Production (Render)](#production-render)
- [Configuration](#configuration)
- [Shop behaviour](#shop-behaviour)
- [Studio admin](#studio-admin)
- [Order emails](#order-emails)
- [Security](#security)
- [Data on Render Free](#data-on-render-free)
- [Keeping data (persistence)](#keeping-data-persistence)
- [License](#license)

## What this project is

| This project **does** | This project **does not** |
|-----------------------|---------------------------|
| Show a catalog, cart, and checkout form | Charge cards or talk to Revolut/Stripe |
| Save orders in SQLite and email the studio (once mail is configured) | Keep data on Render **Free** (`/tmp` is wiped) |
| Let the studio update order status, notes, stock, and add products | Use `print-me-maybe.onrender.com` as an email-sending domain |
| Rate-limit login/checkout and send security alerts | Collect payment at checkout |

Customers are told to send custom names, photos, or print files via **Instagram DM**. Payment is arranged off-site.

## Features

- Catalog with category filter (3D Prints / Laser Engraving)
- Session cart; quantity cannot exceed stock
- Shipping €3.50 under €25, free at €25+
- Demo checkout: name, email, address — **no payment collected**
- Customer order page at `/order/{unguessable-token}` (numeric `/order/1` is not public)
- Studio at `/admin` (not linked in public nav): orders, notes, cancel/restock, add product + photo
- Background order email via [Resend](https://resend.com) (needs a domain you own — see [Order emails](#order-emails))
- JSON catalog at `GET /api/products`
- Liveness at `GET /health` (`{"status":"ok","service":"eshop","mail":true|false}`)

## Stack

- **Python 3.12**, [FastAPI](https://fastapi.tiangolo.com/), Uvicorn
- **Jinja2** HTML templates + `static/css`
- **SQLite** under `DATA_DIR` (default `/tmp/eshop-data/eshop.db`)
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
  notify.py          Resend/SMTP mail, attack alerts
  ratelimit.py       Per-IP limits
  security.py        Secrets, HTTPS cookies, CSP/HSTS
  uploads.py         Admin product photos
templates/           HTML (base, shop, cart, checkout, admin)
static/              CSS and seed product images
tests/               pytest (shop, admin, mail, rate limit, security)
render.yaml          Render Blueprint (Free, Frankfurt)
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

## Production (Render)

Blueprint: `render.yaml`. Service name **print-me-maybe**, Python, **Starter**, region **Frankfurt**, **1 GB disk** at `/var/data` (~$7.25/month).

The **live** service is still on Free until you upgrade it in the dashboard (a git push does not attach a disk by itself).

1. GitHub: [panagiod/eshop](https://github.com/panagiod/eshop)
2. [dashboard.render.com](https://dashboard.render.com) → **print-me-maybe**
3. Follow [Keeping data](#keeping-data-persistence) (Starter + disk + `DATA_DIR=/var/data`)
4. Shop URL: **https://print-me-maybe.onrender.com**

Render generates `SESSION_SECRET` and `ADMIN_PASSWORD`. Copy the admin password from the service **Environment** tab. The service **will not boot** on Render without those two values.

**Manual Deploy** after environment or disk changes. `/health` should show `"persistent": true` once `DATA_DIR` is not `/tmp`.

Two dashboards that are easy to mix up:

| Site | URL | Role |
|------|-----|------|
| **Render** | https://dashboard.render.com | Runs the website |
| **Resend** | https://resend.com | Sends email |

## Configuration

Set these on Render → **print-me-maybe** → **Environment**. Never commit secrets or paste API keys into git/chat.

| Variable | Default | Purpose |
|----------|---------|---------|
| `PORT` | set by Render | HTTP listen port |
| `PYTHON_VERSION` | `3.12.3` | Render runtime |
| `SESSION_SECRET` | generated on Render | Signs session cookies; **required** in production |
| `ADMIN_PASSWORD` | `printmemaybe` locally; **required** on Render | Studio login |
| `SESSION_HTTPS_ONLY` | on when `RENDER` is set | Secure cookie flag |
| `SHOP_NAME` | `Print Me Maybe` | Branding |
| `SHOP_URL` | `https://print-me-maybe.onrender.com` | Links in emails |
| `NOTIFY_EMAIL` | `dimitrioupanagiotis@outlook.com` | Inbox for order and attack alerts |
| `RESEND_API_KEY` | empty (mail skipped) | Resend API key (`re_…`) |
| `RESEND_FROM` | `Print Me Maybe <beth.t@example.com>` | Must be an address on a **verified** Resend domain — not onrender.com / outlook.com |
| `ATTACK_ALERT_COOLDOWN` | `3600` | Seconds between similar security emails |
| `DATA_DIR` | `/tmp/eshop-data` locally; `/var/data` on Render with a disk | SQLite + uploaded photos |
| `NOTIFY_SYNC` | unset | Set to `1` in tests so checkout waits for mail |
| `RATE_LIMIT_DISABLED` | unset | Set to `1` to turn limits off (tests) |

`GET /health` includes `"mail": true|false` and `"persistent": true|false`. `mail` means a key is present, not that Resend accepted the From domain. `persistent` is true when `DATA_DIR` is not under `/tmp`.

## Shop behaviour

**Catalog.** Seed SKUs live in `src/seed.py` (names, euro prices, photos from public Instagram where a price was named). On boot, seed rows are upserted **by slug**. Stock changes and products added in studio are kept; seed does not reset quantity.

**Cart.** Stored in the signed session cookie (7 days). Add/update quantity is capped at remaining stock. Zero stock hides a product from the shop.

**Checkout.** POST `/checkout` with name, email, shipping address. Creates an order, decrements stock, clears the cart, then emails the studio in a **background thread** (checkout does not wait on Resend).

**Customer order URL.** `/order/{lookup_token}` — random token, not the numeric id.

## Studio admin

Public nav does not advertise `/admin`. Login: [https://print-me-maybe.onrender.com/admin/login](https://print-me-maybe.onrender.com/admin/login).

| Page | What it does |
|------|----------------|
| `/admin/orders` | Filter by status; **Send test email** |
| `/admin/orders/{id}` | Status, notes, cancel (restock) / reopen (deduct again) |
| `/admin/stock` | Add product (name, description, EUR price, category, photo, qty); set stock |

Order statuses: New → In progress → Ready to ship → Shipped, plus Cancelled.

Uploaded photos are served from `/media/products/...` and stored under `DATA_DIR/product-images`. On Render Free they disappear when `/tmp` is wiped.

## Order emails

New checkouts and blocked login/checkout floods email **dimitrioupanagiotis@outlook.com**. Checkout still succeeds if mail fails.

**Current status:** `RESEND_API_KEY` is on Render. The shop can call Resend. Order **#2** was accepted as an API call and **rejected (HTTP 403)** with “domain not verified”. Outlook stays empty until you buy a domain, verify it at Resend, and set `RESEND_FROM`. Do that after you own a domain — not before.

### What you cannot add in Resend → Domains

These names are not yours. Verification will fail:

- `print-me-maybe.onrender.com` — Render’s **web** address (keep using it in the browser)
- `onrender.com` — belongs to Render
- `outlook.com` — belongs to Microsoft (Outlook can still *receive*)
- `resend.dev` / `example.com` / `beth.t@example.com` — Resend shared test sender; this account returns 403
- `@print.me.maybe` — Instagram, not a domain

A domain is a name you **buy**, such as `printmemaybe.com`. Mail then sends as `orders@printmemaybe.com` and can still land in Outlook.

### Already done

1. Resend account **dimitrioupanagiotis** (aligned with the Outlook address)
2. API key created (`re_…`) and saved on Render as `RESEND_API_KEY` (never paste the key into git or chat)
3. Shop `User-Agent`: `PrintMeMaybeShop/1.0` — see Resend **Logs**, not **Emails → Receiving**

**Emails → Receiving** is inbound `@….resend.app` and is unused. Use **Emails → Sending** and **Logs**. Status **403** means refused, not delivered.

### When you have bought a domain

Replace `printmemaybe.com` with the name you bought.

1. Buy a domain (Cloudflare, Namecheap, Google, or similar). `.com` or `.cy` is fine.
2. [resend.com/domains](https://resend.com/domains) → **Add Domain** → `printmemaybe.com` (no `https://`).
3. Copy every DNS record Resend shows (TXT / MX) into the registrar DNS. Save. Do not skip rows.
4. Wait until Resend shows **Verified**. Do not continue while Pending.
5. [dashboard.render.com](https://dashboard.render.com) → **print-me-maybe** → **Environment**.
6. Set `RESEND_FROM` to `Print Me Maybe <orders@printmemaybe.com>` (any local-part: `orders`, `studio`, `hello` — no mailbox required at that address).
7. Confirm `NOTIFY_EMAIL` is `dimitrioupanagiotis@outlook.com`.
8. **Save**, then **Manual Deploy**.
9. Studio [Orders](https://print-me-maybe.onrender.com/admin/orders) → **Send test email**.
10. Resend **Sending** / **Logs**: **Delivered**, not 403.
11. Outlook: search Inbox, Junk, Other, Focused. Mark Not junk the first time.

Optional later: point the **website** at the same domain (Render → Settings → **Custom Domains**). That is separate from mail. Mail only needs Resend verification + `RESEND_FROM`.

Attack alerts (blocked studio login or checkout flood) email at most once per hour per type.

## Security

- On Render, missing `SESSION_SECRET` or `ADMIN_PASSWORD` refuses to boot
- Session cookies: `SameSite=lax`, HTTPS-only in production
- Studio password compared with SHA-256 + `hmac.compare_digest` (failed logins are logged, never the password)
- Security headers: `nosniff`, `DENY` framing, Referrer-Policy, Permissions-Policy, CSP, HSTS on HTTPS
- Customer orders use `lookup_token`, not sequential public URLs

Rate limits (in-memory, per instance, by IP):

| Action | Default |
|--------|---------|
| Pages | 240 / minute |
| Studio login POST | 5 / 15 minutes |
| Checkout POST | 12 / hour |
| Cart POST | 60 / minute |

`/health`, `/static/`, `/media/` are exempt. HTTP 429 includes `Retry-After`.

## Data on Render Free

There is **no persistent disk** on Free. `DATA_DIR=/tmp/eshop-data` is wiped when the instance sleeps or redeploys. Do not keep the live shop on Free if you need orders.

## Keeping data (persistence)

**Do this on the live service now** (about **$7.25/month**). Order matters: attach the disk **before** pointing `DATA_DIR` at `/var/data`.

1. Open [dashboard.render.com](https://dashboard.render.com) → **print-me-maybe**.
2. Instance type: **Free → Starter** (requires a card). Starter stays awake.
3. **Disks** → Add disk:
   - Name: `eshop-data`
   - Mount path: **`/var/data`** (not `/tmp`)
   - Size: **1 GB**
4. Wait until the disk deploy finishes.
5. **Environment** → set `DATA_DIR` to `/var/data` (replace `/tmp/eshop-data`).
6. **Save** → **Manual Deploy**.
7. Open `https://print-me-maybe.onrender.com/health` — you want `"persistent": true`.
8. Place a test order (and optionally upload a product photo). **Manual Deploy** once more. The order and photo must still be there.

Do **not** use `/tmp`. Do **not** skip the disk and only change `DATA_DIR` — `/var/data` without a mount is still wiped.

`render.yaml` already describes Starter + this disk for new deploys. The existing Free service must be upgraded in the dashboard.

After the disk is on, download `/var/data/eshop.db` occasionally (Render shell on Starter) so a disk failure is not the only copy of orders.

## License

[MIT](LICENSE) — use freely for learning and demos.
