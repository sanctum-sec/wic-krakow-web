# wic-krakow-web — workshop portal

> Workshop landing page + S3 file-drop + access-cards + Day-3 exercise page, shipped during the **STEP UP 3! Women's Cyber Defense Workshop** (Kraków, 21–23 April 2026).

Serves `https://wic-krakow.sanctumsec.com` (Basic Auth-gated) on a single Lightsail instance (`wic-krakow-web`, `eu-central-1`).

---

## What it serves

| Path | Auth | What it is |
| ---- | ---- | ---------- |
| `/` | Basic Auth | Landing page — Day-3 team banner, Day-2 session artifacts grid, drag-drop uploader, recent-drops table |
| `/day3` | Basic Auth | Day-3 team-building exercise page (English) — six-team table with repo links, checkpoints, golden rules |
| `/day3/uk` | Basic Auth | Same, in Ukrainian |
| `/wic-access-ghosttrace` | Basic Auth | Access cards — per-team Lightsail credentials + SSH methods + git deploy-key workflow + Claude Code activation notes |
| `/upload` | Basic Auth | POST endpoint — writes into `s3://wic-krakow-2026/drops/<YYYY-MM-DD>/<filename>` |
| `/artifacts/<session>/<path:filename>` | Basic Auth | Per-file download from the Day-2 session artifacts tree on disk |
| `/healthz` | public | Liveness probe |

The Day-2 session artifacts that the landing indexes live under `/home/ubuntu/artifacts/` on the running box (about 5.4 MB, 8 session subdirectories — they're a separate archival asset, not part of this repo).

---

## Stack

- **Flask** (FastAPI-style decorators) + **Jinja2** templates + **HTMX** for partial refreshes
- **gunicorn** serving `uploader_app:app` on `127.0.0.1:5000` (2 workers, sync)
- **nginx** reverse proxy on `:443` with Let's Encrypt TLS (auto-renewing)
- **boto3** for S3 uploads
- **systemd** unit (`wic-uploader.service`) for process supervision

Three visual themes across the four pages:

- **Landing (`/`)**: light theme with a Ukrainian flag-stripe accent — soft, document-oriented. Styles in `static/styles.css`.
- **Day-3 exercise (`/day3`)** and **access cards (`/wic-access-ghosttrace`)**: dark "tactical HMI" theme borrowed from the Bohdanivka WTP scenario of Day 2 — monospace, LED indicators, status chips. Styles split across `static/hmi.css` (base), `static/wic_access.css` (cards), `static/day3.css` (exercise page + lang toggle).

---

## Local dev

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install flask boto3 gunicorn

# Secrets / config — NOT checked in
cp cards.json.example cards.json     # then edit with real Lightsail creds
export UPLOADER_PASSWORD='local-dev-password'

# If testing uploads, set AWS creds too
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...
export AWS_DEFAULT_REGION=eu-central-1

# Run it
python3 -m flask --app uploader_app run --host 0.0.0.0 --port 8000
```

Then open `http://localhost:8000` and auth with `wic / local-dev-password`.

---

## Production layout on `wic-krakow-web`

```
/home/ubuntu/uploader/
├── uploader_app.py           ← tracked in this repo
├── templates/                ← tracked
├── static/                   ← tracked
├── cards.json                ← NOT tracked (contains Lightsail passwords)
└── uploader.env              ← NOT tracked (contains Basic Auth password)

/home/ubuntu/artifacts/       ← Day-2 session artifacts, separate archival set
/etc/systemd/system/wic-uploader.service      ← tracked as ops/wic-uploader.service
/etc/nginx/sites-enabled/wic-uploader         ← tracked as ops/nginx-wic-krakow.conf
/etc/letsencrypt/live/wic-krakow.sanctumsec.com/   ← auto-managed by certbot
```

`uploader.env` contains:

```
UPLOADER_PASSWORD=<basic-auth-password>
```

`cards.json` is the access-cards data; see `cards.json.example` for shape.

---

## Redeploy

After the post-workshop consolidation, the production box runs from a git checkout of this repo's `main`. Future updates:

```bash
# On wic-krakow-web
cd /home/ubuntu/uploader
git fetch origin
git reset --hard origin/main
sudo systemctl restart wic-uploader
```

Changes to the systemd unit or nginx config require manually copying from `ops/` into `/etc/` and reloading the respective service.

---

## Provenance

- **Repo created:** 2026-04-23, post-workshop, as part of the documentation consolidation pass.
- **Code provenance:** pulled from the live production box (`/home/ubuntu/uploader/` on `wic-krakow-web`) where it was authored during the workshop.
- **Before publication:** inline access-cards password list extracted out of source into `cards.json` (gitignored).

See [`CHANGELOG.md`](CHANGELOG.md) for the full timeline.

---

## Related

- [`sanctum-sec/soc-protocol`](https://github.com/sanctum-sec/soc-protocol) — shared contract the six teams implemented
- [`sanctum-sec/soc-day3-*`](https://github.com/orgs/sanctum-sec/repositories?q=soc-day3-) — the six team repos built during Day 3
- Project folder (private, local): full workshop record including pre-course survey replies, original course materials, retrospective
