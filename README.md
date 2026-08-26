# Print Me Maybe

Shop for **3D prints** ([@print.me.maybe](https://www.instagram.com/print.me.maybe/)) and **laser engraving** ([@lasercraft.27](https://www.instagram.com/lasercraft.27/)).

Free to host on Render — **$0/month**, no Kubernetes.

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/panagiod/eshop)

Sign in with GitHub, keep the **Free** plan, click Apply. After the first deploy the shop is at:

**https://print-me-maybe.onrender.com**

(Render may add a suffix if that name is taken.) Add your own domain later in Render → Settings → Custom Domains.

No credit card. Free instances sleep after ~15 minutes idle (~1 minute wake). SQLite in `/tmp` resets on redeploy.

## Local run (optional)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
uvicorn src.main:app --reload --port 8080
```

Open http://localhost:8080

## Catalog

Listings for **3D prints** come from public [@print.me.maybe](https://www.instagram.com/print.me.maybe/) posts (names, euro prices, and photos). Posts that did not name a price (cake toppers, bear keychains) use starting prices in line with similar EU listings. **Laser engraving** is custom work from [@lasercraft.27](https://www.instagram.com/lasercraft.27/) — that profile is login-walled, so those SKUs use branded placeholders and comparable EU laser prices until studio photos and quotes are added.

Prices are in **EUR**. Shipping is €3.50 under €25, free at €25+. Custom names, colours, and files: order notes or Instagram DM.

On boot, catalog copy and prices for seed SKUs are upserted by slug. Admin stock changes and products added from `/admin/stock` are kept.

## Studio admin

After login at `/admin`:

- **Orders** — list by status (New → In progress → Ready to ship → Shipped)
- **Order detail** — customer, items, studio notes (Instagram custom requests). Cancelling restocks; reopening deducts stock again.
- **Stock** — add a product (name, description, euro price, category, photo, starting quantity) and set remaining quantity. Zero hides the product from the shop.

Photos uploaded in admin are stored under `DATA_DIR` (default `/tmp/eshop-data`). On Render Free that directory resets when the instance sleeps or redeploys, same as the SQLite catalog.

Local password default: `printmemaybe`. On Render, copy `ADMIN_PASSWORD` from the service Environment tab (it is generated for you).

Studio login allows 5 tries per 15 minutes per visitor. Checkout allows 12 orders per hour. Extra traffic gets HTTP 429.

On Render, `SESSION_SECRET` and `ADMIN_PASSWORD` are required (the service will not start without them). Session cookies are HTTPS-only. Customer order pages use an unguessable token, not `/order/1`. Cart quantity cannot exceed stock.

## Order emails

New checkouts email **dimitrioupanagiotis@outlook.com**. Reply to that message to write the customer.

Mail only goes out when `SMTP_PASSWORD` is set. On Render:

1. Open the `print-me-maybe` service → **Environment**
2. Add `SMTP_PASSWORD` with an [Outlook app password](https://account.microsoft.com/security) (Microsoft account → Security → two-step verification → App passwords). Do not use your normal Outlook login password.
3. **Manual Deploy** so the live shop picks it up

If Outlook blocks SMTP, use a Gmail app password instead and set `SMTP_HOST=smtp.gmail.com`, `SMTP_USER` to that Gmail address, and `SMTP_PASSWORD` to the 16-character app password.

Checkout still succeeds if mail fails.

## Environment variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `PORT` | set by Render | HTTP listen port |
| `SESSION_SECRET` | auto-generated on Render | Signs session cookies |
| `ADMIN_PASSWORD` | `printmemaybe` locally; required on Render | Studio admin login |
| `SESSION_HTTPS_ONLY` | on when `RENDER` is set | Secure session cookie |
| `SHOP_NAME` | `Print Me Maybe` | Store branding |
| `SHOP_URL` | `https://print-me-maybe.onrender.com` | Links in order emails |
| `NOTIFY_EMAIL` | `dimitrioupanagiotis@outlook.com` | Inbox for new-order alerts |
| `SMTP_HOST` | `smtp-mail.outlook.com` | Outgoing mail server |
| `SMTP_PORT` | `587` | `587` STARTTLS or `465` SSL |
| `SMTP_USER` | same as `NOTIFY_EMAIL` | SMTP login |
| `SMTP_PASSWORD` | empty (mail skipped) | Outlook/Gmail app password |
| `DATA_DIR` | `/tmp/eshop-data` | SQLite directory |

## License

MIT — use freely for learning and demos.
