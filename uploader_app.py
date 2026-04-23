"""WIC Kraków 2026 — landing page + S3 uploader + access cards + Day 3 exercise page."""
from __future__ import annotations

import hmac
import os
import re
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path

import boto3
from flask import (
    Flask,
    Response,
    abort,
    jsonify,
    render_template,
    request,
    send_from_directory,
)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
ARTIFACTS_DIR = Path(os.environ.get("ARTIFACTS_DIR", "/home/ubuntu/artifacts"))
WORKSHOP_TITLE = "STEP UP 3! · Women's Cyber Defense Workshop"
WORKSHOP_SUBTITLE = "Kraków · 21–23 April 2026"

BUCKET = "wic-krakow-2026"
REGION = "eu-central-1"
DROPS_PREFIX = "drops/"
AUTH_USER = "wic"
AUTH_PASS = os.environ["UPLOADER_PASSWORD"]
MAX_BYTES = 100 * 1024 * 1024

# Access-cards data (contains instance passwords) is loaded from a sibling JSON
# file that's gitignored. See cards.json.example for the expected structure.
# If the file is missing or empty, the access-cards page renders with an empty
# list — safer default than shipping secrets in source.
import json as _json
_CARDS_PATH = BASE_DIR / "cards.json"
try:
    LIGHTSAIL_CARDS = _json.loads(_CARDS_PATH.read_text(encoding="utf-8"))
except (OSError, ValueError):
    LIGHTSAIL_CARDS = []

TEAMS = [
    {"num": 1, "codename_en": "Trap", "codename_uk": "Пастка",
     "role": "Honeypot sensor network",
     "role_uk": "Мережа honeypot-сенсорів",
     "mitre": "Sensing Architecture · Deception · Custom Analytics",
     "host": "wic01.sanctumsec.com",
     "repo": "sanctum-sec/soc-day3-trap",
     "repo_url": "https://github.com/sanctum-sec/soc-day3-trap"},
    {"num": 2, "codename_en": "Scout", "codename_uk": "Розвідник",
     "role": "Threat Intelligence aggregator",
     "role_uk": "Агрегатор Threat Intelligence",
     "mitre": "CTI Collection / Fusion · Analysis · Sharing",
     "host": "wic02.sanctumsec.com",
     "repo": "sanctum-sec/soc-day3-scout",
     "repo_url": "https://github.com/sanctum-sec/soc-day3-scout"},
    {"num": 3, "codename_en": "Analyst", "codename_uk": "Аналітик",
     "role": "Detection & correlation engine (SIEM)",
     "role_uk": "Детекційний і кореляційний движок (SIEM)",
     "mitre": "Real-Time Alert Monitoring · Custom Detection Creation",
     "host": "wic03.sanctumsec.com",
     "repo": "sanctum-sec/soc-day3-analyst",
     "repo_url": "https://github.com/sanctum-sec/soc-day3-analyst"},
    {"num": 4, "codename_en": "Hunter", "codename_uk": "Мисливець",
     "role": "Behavioral anomaly hunter",
     "role_uk": "Поведінковий anomaly hunter",
     "mitre": "Threat Hunting · Data Science / ML",
     "host": "wic04.sanctumsec.com",
     "repo": "sanctum-sec/soc-day3-hunter",
     "repo_url": "https://github.com/sanctum-sec/soc-day3-hunter"},
    {"num": 5, "codename_en": "Dispatcher", "codename_uk": "Диспетчер",
     "role": "SOAR + live SOC dashboard",
     "role_uk": "SOAR + живий SOC-дашборд",
     "mitre": "Incident Coordination · Situational Awareness · Metrics",
     "host": "wic05.sanctumsec.com",
     "repo": "sanctum-sec/soc-day3-dispatcher",
     "repo_url": "https://github.com/sanctum-sec/soc-day3-dispatcher"},
    {"num": 6, "codename_en": "Inspector", "codename_uk": "Інспектор",
     "role": "Compliance, audit & bilingual AI-methodology training",
     "role_uk": "Комплаєнс, аудит і двомовний AI-методологічний тренінг",
     "mitre": "External Training · Vulnerability Assessment · Metrics",
     "host": "wic06.sanctumsec.com",
     "repo": "sanctum-sec/soc-day3-inspector",
     "repo_url": "https://github.com/sanctum-sec/soc-day3-inspector",
     "tag": "new"},
]

PROTOCOL_REPO_URL = "https://github.com/sanctum-sec/soc-protocol"

FILE_KIND_LABELS = {
    ".md": "markdown", ".pdf": "pdf", ".pptx": "slides", ".ppt": "slides",
    ".jsonl": "transcript (jsonl)", ".json": "json", ".py": "python",
    ".sh": "shell", ".txt": "text", ".csv": "csv", ".yml": "yaml",
    ".yaml": "yaml", ".png": "image", ".jpg": "image", ".jpeg": "image",
    ".gif": "image", ".webp": "image",
}

SESSION_TITLES = {
    "air-gapped-frontier-model-workflow": "Air-gapped frontier-model workflow",
    "claude-code-resources": "Claude Code — bilingual workshop resources",
    "incident-response-policy-macos": "macOS unified logging for IR / analysts",
    "llm-behavioral-fingerprinting": "LLM behavioral fingerprinting (research reference)",
    "modbus-ot-attack-detection": "Modbus OT attack detection — Ghost Trace walkthrough",
    "shared-references": "Shared external references (reading list)",
    "terminal-toys-demo": "Terminal toys demo (bonus)",
    "ukrainian-proverbs-fortune-cowsay": "Ukrainian proverbs — fortune + cowsay Unicode case study",
}

SESSION_TAGS = {
    "air-gapped-frontier-model-workflow": "Bilingual · best practices",
    "claude-code-resources": "Bilingual · reference",
    "incident-response-policy-macos": "IR · macOS",
    "llm-behavioral-fingerprinting": "External reference",
    "modbus-ot-attack-detection": "OT · ICS · Ghost Trace",
    "shared-references": "Reading list",
    "terminal-toys-demo": "Bonus · UA handout",
    "ukrainian-proverbs-fortune-cowsay": "Teaching case · Unicode",
}

app = Flask(__name__, template_folder=str(BASE_DIR / "templates"), static_folder=str(BASE_DIR / "static"))
app.config["MAX_CONTENT_LENGTH"] = MAX_BYTES
s3 = boto3.client("s3", region_name=REGION)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def safe_name(name: str) -> str:
    name = os.path.basename(name or "")
    name = re.sub(r"[^\w.\- ]", "_", name).strip()
    return name[:200] or "file"


def auth_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        a = request.authorization
        if not a or not (
            hmac.compare_digest(a.username, AUTH_USER)
            and hmac.compare_digest(a.password, AUTH_PASS)
        ):
            return Response(
                "Authentication required",
                401,
                {"WWW-Authenticate": 'Basic realm="WIC Kraków 2026"'},
            )
        return f(*args, **kwargs)

    return wrapper


def fmt_size(b: int) -> str:
    if b < 1024:
        return f"{b} B"
    if b < 1024 ** 2:
        return f"{b / 1024:.1f} KB"
    if b < 1024 ** 3:
        return f"{b / 1024 ** 2:.2f} MB"
    return f"{b / 1024 ** 3:.2f} GB"


def kind_label(name: str) -> str:
    ext = Path(name).suffix.lower()
    return FILE_KIND_LABELS.get(ext, ext.lstrip(".") or "file")


def _first_paragraph(md_text: str) -> str:
    paras = [p.strip() for p in md_text.split("\n\n") if p.strip()]
    for p in paras:
        lines = [l for l in p.splitlines() if l.strip()]
        if not lines:
            continue
        if lines[0].startswith("#"):
            if len(lines) == 1:
                continue
            body = "\n".join(lines[1:]).strip()
            if body:
                return body
            continue
        return p
    return ""


def _clip(text: str, limit: int = 280) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rsplit(" ", 1)[0] + "…"


def discover_sessions():
    if not ARTIFACTS_DIR.is_dir():
        return []

    sessions = []
    for child in sorted(ARTIFACTS_DIR.iterdir()):
        if not child.is_dir():
            continue
        slug = child.name
        readme_path = child / "README.md"
        summary = ""
        if readme_path.is_file():
            try:
                summary = _clip(_first_paragraph(readme_path.read_text(encoding="utf-8")))
            except Exception:
                summary = ""

        files = []
        for fp in sorted(child.rglob("*")):
            if fp.is_dir() or fp.name.startswith("."):
                continue
            rel = fp.relative_to(child)
            try:
                stat = fp.stat()
            except OSError:
                continue
            files.append(
                {
                    "name": str(rel),
                    "size_h": fmt_size(stat.st_size),
                    "size_bytes": stat.st_size,
                    "kind": kind_label(fp.name),
                    "mtime": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
                }
            )

        files.sort(key=lambda f: (not f["name"].lower().endswith("readme.md"), f["name"].lower()))

        sessions.append(
            {
                "slug": slug,
                "title": SESSION_TITLES.get(slug, slug.replace("-", " ").title()),
                "tag": SESSION_TAGS.get(slug, ""),
                "summary": summary,
                "files": files,
                "file_count": len(files),
                "total_size_h": fmt_size(sum(f["size_bytes"] for f in files)),
            }
        )

    return sessions


def recent_drops(limit: int = 20):
    try:
        resp = s3.list_objects_v2(Bucket=BUCKET, Prefix=DROPS_PREFIX, MaxKeys=200)
    except Exception:
        return []
    items = []
    for o in resp.get("Contents") or []:
        items.append(
            {
                "name": o["Key"].replace(DROPS_PREFIX, "", 1),
                "size_h": fmt_size(o["Size"]),
                "when": o["LastModified"].astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
                "mtime": o["LastModified"],
            }
        )
    items.sort(key=lambda x: x["mtime"], reverse=True)
    return items[:limit]


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/")
@auth_required
def index():
    sessions = discover_sessions()
    return render_template(
        "index.html",
        title=WORKSHOP_TITLE,
        subtitle=WORKSHOP_SUBTITLE,
        sessions=sessions,
        drops=recent_drops(),
        teams=TEAMS,
    )


@app.get("/wic-access-ghosttrace")
@auth_required
def access_cards():
    return render_template(
        "access_cards.html",
        title=WORKSHOP_TITLE,
        cards=LIGHTSAIL_CARDS,
    )


@app.get("/day3")
@auth_required
def day3_exercise():
    return render_template(
        "day3_exercise.html",
        title=WORKSHOP_TITLE,
        teams=TEAMS,
        protocol_url=PROTOCOL_REPO_URL,
    )


@app.get("/day3/uk")
@auth_required
def day3_exercise_uk():
    return render_template(
        "day3_exercise.uk.html",
        title=WORKSHOP_TITLE,
        teams=TEAMS,
        protocol_url=PROTOCOL_REPO_URL,
    )


@app.get("/artifacts/<session>/<path:filename>")
@auth_required
def artifact_download(session: str, filename: str):
    if session.startswith(".") or ".." in session:
        abort(404)
    base = (ARTIFACTS_DIR / session).resolve()
    if not base.is_dir() or (ARTIFACTS_DIR.resolve() not in base.parents and base != ARTIFACTS_DIR.resolve()):
        if ARTIFACTS_DIR.resolve() not in base.parents:
            abort(404)
    as_attachment = request.args.get("download") == "1"
    return send_from_directory(base, filename, as_attachment=as_attachment)


@app.post("/upload")
@auth_required
def upload():
    f = request.files.get("file")
    if not f or not f.filename:
        return jsonify(error="no file"), 400
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    key = f"{DROPS_PREFIX}{today}/{safe_name(f.filename)}"
    try:
        s3.upload_fileobj(
            f, BUCKET, key,
            ExtraArgs={"ContentType": f.mimetype or "application/octet-stream"},
        )
    except Exception as e:
        return jsonify(error=str(e)), 500
    return jsonify(ok=True, key=key)


@app.get("/healthz")
def health():
    return "ok\n"
