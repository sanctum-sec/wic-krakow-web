# Changelog

All notable changes to this repository. Format based on [Keep a Changelog](https://keepachangelog.com/).

---

## [post-workshop] — 2026-04-23

Initial public archival of the workshop portal code. Everything below happened on
a single day after the workshop closed.

### Added

- `README.md` describing what the site serves, the stack, local-dev instructions, production layout, and redeploy steps.
- `.gitignore` — standard Python excludes plus `cards.json` and `*.env`.
- `cards.json.example` — structure template for the access-cards data.
- `ops/wic-uploader.service` — systemd unit from `/etc/systemd/system/wic-uploader.service` on the live box.
- `ops/nginx-wic-krakow.conf` — nginx site from `/etc/nginx/sites-enabled/wic-uploader` on the live box (includes the Let's Encrypt-managed TLS config).
- `CHANGELOG.md` — this file.

### Changed

- **Access-cards data (Lightsail passwords) extracted out of source** into a sibling `cards.json` file that is gitignored. The old inline `LIGHTSAIL_CARDS = [...]` list with all six `GhostTrace-0N!` passwords is replaced with a JSON loader. If the file is missing the list is empty, which fails safely (access cards page shows no entries instead of silently shipping secrets).
- Production code imported from `wic-krakow-web:/home/ubuntu/uploader/` (excluding `.env`, `__pycache__`, macOS metadata).

### Security

- Pre-publication secret scan: `GhostTrace-0[1-6]!`, `sk-ant-*`, `stepup-krakow-2026`, SSH private key headers — all clean in the current tree after the `cards.json` extraction.
- `uploader.env` on the box (contains the Basic Auth password) is gitignored; stays on the server only.
- Deploy keys and Actions secrets from the workshop-period repos were already revoked in the earlier consolidation pass; no workshop-period credentials remain attached to this repo.

### Administrative

- Repository visibility: **public** from day one (consistent with the seven Day-3 repos).
- Discussions enabled.
- Production box (`wic-krakow-web`) re-tethered to this repo: `/home/ubuntu/uploader/` is now a git checkout of `main`; future updates propagate via `git fetch && git reset --hard origin/main && sudo systemctl restart wic-uploader`.

---

## [0.3.0] — 2026-04-23 (live during workshop — final iteration)

This is the state at workshop close. Four iteration rounds during the week built up to this.

### Added (Day 3)

- `/day3` and `/day3/uk` — Day-3 exercise pages with six-team table (codename / Lightsail / GitHub repo), checkpoints, golden rules, shortcut links. Dark "tactical HMI" theme. Includes a `★ Розвідник ★` (and eventually all non-Analyst teams) sparkle treatment added mid-day.
- `/wic-access-ghosttrace` — access cards page migrated from `hmi-stepup3.sanctumsec.com:8080` with a redirect left in place on the old server. Six team cards (Team 6 added for Inspector). Adds a "Git & Push" section explaining the deploy-key workflow.
- Landing-page header nav adds CTAs for Day 3 exercise + Access Cards.
- Language toggle (`EN / UK`) on the sub-nav of both tactical pages.
- `static/day3.css` + additions to `static/styles.css` for the "Today — Day 3" banner + team chips.
- Static CSS assets for the tactical theme: `static/hmi.css`, `static/wic_access.css`, `static/day3.css`.

### Fixed

- Day-3 schedule compressed from the original 8-hour window to the real 10:45 – 16:30 on the exercise page (kickoff 45 min, phased checkpoints at ~12:30 / ~14:45 / 15:45, demo 16:10, retro 16:30).
- `stepup-krakow-2026` Basic-Auth hint removed from pages that would become visible to the open internet (the PLAN docs in the team repos went public; these pages stayed auth-gated).

---

## [0.2.0] — 2026-04-22 (Day 2 — portal + landing)

- Re-theme of the original simple uploader into a full landing page.
- New routes: artifact browser at `/artifacts/<session>/<filename>`, with HTMX-lit session cards on `/`.
- Session-artifact layout pulled from `/home/ubuntu/artifacts/` at request time — discovered and listed via session-folder README metadata.
- Upload zone preserved from the earlier uploader; kept as the secondary section of the landing.
- "Recent drops" table queries S3 at render time; shows last 20 uploads.
- Migrated deploy onto the `wic-krakow-web` Lightsail with nginx + Let's Encrypt.

---

## [0.1.0] — 2026-04-21 (initial upload endpoint)

- First iteration: a minimal Flask app that provided an authenticated drag-drop form plus a recent-drops table.
- Intended as the Day-1 "show-up" asset — a neutral way for participants to hand files to the instructor when terminal sharing didn't work.

---

## Future work

- **Bootstrap script** to re-create the runtime state (`cards.json`, `uploader.env`) from a template + sensitive-values prompts. Right now those live only on the server; if the server is rebuilt, they'd need to be re-created manually.
- **Deploy workflow** (GitHub Actions) that SSHes in and runs `git pull + systemctl restart` on push to `main`. Deferred because the workshop is over; redeploying by hand is fine at this point.
- **Health metrics** beyond the binary `/healthz` — upload rate, latest drop, service uptime. Not worth adding unless the site starts getting real post-workshop use.
