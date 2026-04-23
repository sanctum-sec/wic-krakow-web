"""WIC Kraków 2026 — landing page + access cards + Day 3 exercise + course materials."""
from __future__ import annotations

import hmac
import os
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path

from flask import (
    Flask,
    Response,
    abort,
    render_template,
    request,
    send_from_directory,
)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
ARTIFACTS_DIR = Path(os.environ.get("ARTIFACTS_DIR", "/home/ubuntu/artifacts"))
MATERIALS_DIR = Path(os.environ.get("MATERIALS_DIR", "/home/ubuntu/materials"))
WORKSHOP_TITLE = "STEP UP 3! · Women's Cyber Defense Workshop"
WORKSHOP_SUBTITLE = "Kraków · 21–23 April 2026"

# ----- Course-materials index -----------------------------------------------
# Layout on disk (under MATERIALS_DIR):
#   modules/     ins_ukraine_stepUP_moduleNN_rev0(_ukr)?.pptx
#   exercises/   player books (EN+UK), 03a xlsx/blanks
#   answer-keys/ exercise0N answer-key group docs, json, xlsx
#   printer/     master concatenated PDFs (EN + UK)
#   sources/     CyOTE TRITON case study
#
# Titles are the facilitator's best reconstruction of each module's topic;
# correct by editing this list. These are not hard-coded anywhere else.
MODULE_META = [
    {"num": "01", "title_en": "Informed Defensive Strategies — CTI foundations",
     "title_uk": "Інформовані оборонні стратегії — основи CTI"},
    {"num": "02", "title_en": "Attack Lifecycle & TTP Mapping",
     "title_uk": "Життєвий цикл атаки та мапінг TTP"},
    {"num": "03", "title_en": "Defending TTPs",
     "title_uk": "Захист проти TTP"},
    {"num": "04", "title_en": "AI-Augmented CTI",
     "title_uk": "AI-підсилене CTI"},
    {"num": "05", "title_en": "AI-Enhanced Attack Patterns",
     "title_uk": "AI-підсилені патерни атак"},
    {"num": "06", "title_en": "AI Social Engineering Defense",
     "title_uk": "Захист від AI-соціальної інженерії"},
]

EXERCISE_META = [
    {"num": "01", "title_en": "Case Study — TRITON / TRISIS",
     "title_uk": "Кейс — TRITON / TRISIS",
     "player_en": "ins_ukraine_stepUP_exercise01_playerBook_rev0.docx",
     "player_uk": "ins_ukraine_stepUP_exercise01_playerBook_rev0_ukr.docx",
     "answer_keys": [
         "ins_ukraine_stepUP_exercise01_answerKey_group01_rev0.docx",
         "ins_ukraine_stepUP_exercise01_answerKey_group02_rev0.docx",
         "ins_ukraine_stepUP_exercise01_answerKey_group03_rev0.docx",
         "ins_ukraine_stepUP_exercise01_answerKey_group04_rev0.docx",
         "ins_ukraine_stepUP_exercise01_answerKey_group05_rev0.docx",
     ]},
    {"num": "02", "title_en": "Mapping TTPs with ATT&CK Navigator",
     "title_uk": "Мапінг TTP у ATT&CK Navigator",
     "player_en": "ins_ukraine_stepUP_exercise02_playerBook_rev1.docx",
     "player_uk": "ins_ukraine_stepUP_exercise02_playerBook_rev1_ukr.docx",
     "answer_keys": [
         "ins_ukraine_stepUP_exercise02_answerKey_group01_rev0.docx",
         "ins_ukraine_stepUP_exercise02_answerKey_group02_rev0.docx",
         "ins_ukraine_stepUP_exercise02_answerKey_group03_rev0.docx",
         "ins_ukraine_stepUP_exercise02_answerKey_group04_rev0.docx",
         "ins_ukraine_stepUP_exercise02_answerKey_group05_rev0.docx",
         "ins_ukraine_stepUP_exercise02_answerKey_part1+2.docx",
         "ins_ukraine_stepUP_exercise02_answerKey_part1+2.xlsx",
         "ins_ukraine_stepUP_exercise02_answerKey_part1+2.json",
         "ins_ukraine_stepUP_exercise02_answerKey_part2.docx",
     ]},
    {"num": "03", "title_en": "Defending TTPs",
     "title_uk": "Захист проти TTP",
     "player_en": "ins_ukraine_stepUP_exercise03_playerBook_rev3.docx",
     "player_uk": None,
     "answer_keys": [
         "ins_ukraine_stepUP_exercise03a_answerKey_class_rev0.docx",
         "ins_ukraine_stepUP_exercise03b_answerKey_class_rev0.docx",
         "ins_ukraine_stepUp_exercise3a_answer.xlsx",
         "ins_ukraine_stepUp_exercise3a_blank.xlsx",
         "ins_ukraine_stepUP_exercse3a.json",
     ]},
]

PRINTER_BUNDLES = [
    {"name": "Master presentations (EN, all 6 modules concatenated)",
     "file": "ukraine_stepUP_master_presentations_01-06_rev0.pdf", "lang": "en"},
    {"name": "Master player book (EN)",
     "file": "ins_ukraine_stepUP_master_playerBook_rev0.pdf",      "lang": "en"},
    {"name": "Зведений набір презентацій (UA, усі 6 модулів)",
     "file": "ins_ukraine_stepUP_master_presentation_rev0_ukr.pdf", "lang": "uk"},
    {"name": "Зведений player book (UA)",
     "file": "ins_ukraine_stepUP_master_playerBook_rev0_ukr.pdf",  "lang": "uk"},
]

SOURCES = [
    {"name": "CyOTE — TRITON / TRISIS case study",
     "file": "CyOTE-Case-Study_TRITON.pdf",
     "note_en": "Background reading for Exercise 01. Public DOE/CyOTE publication.",
     "note_uk": "Додаткове читання до Вправи 01. Публічна публікація DOE/CyOTE."},
]

# Day-2 Jupyter-notebook bundles — not on disk here; already hosted in S3 public/.
DAY2_BUNDLES = [
    {"num": "00", "file": "00_Day_2_base.zip",
     "size": "2.5 KB",
     "purpose": "README + requirements + .vscode settings. EXTRACT FIRST.", "is_base": True},
    {"num": "01", "file": "01_CTI_Module_1_-_Introduction_to_Threat_Intelligence.zip",
     "size": "113 MB",
     "purpose": "Module 1 — Introduction to Threat Intelligence"},
    {"num": "02", "file": "02_CTI_Module_2_-_Cybersecurity_Frameworks_for_Threat_Intelligence.zip",
     "size": "128 MB",
     "purpose": "Module 2 — Cybersecurity Frameworks for Threat Intelligence"},
    {"num": "03", "file": "03_CTI_Module_3_-_Threat_Actor_Tactics_Techniques_and_Procedures_TTPs.zip",
     "size": "137 MB",
     "purpose": "Module 3 — Threat Actor Tactics, Techniques, and Procedures (TTPs)"},
    {"num": "04", "file": "04_CTI_Module_4_-_Identify_Actors_and_Techniques.zip",
     "size": "133 MB",
     "purpose": "Module 4 — Identify Actors and Techniques"},
    {"num": "05", "file": "05_CTI_Module_5_-_Threat_Intelligence_Lifecycle.zip",
     "size": "131 MB",
     "purpose": "Module 5 — Threat Intelligence Lifecycle"},
    {"num": "06", "file": "06_CTI_Module_6_-_Key_Threat_Intelligence_Sources.zip",
     "size": "132 MB",
     "purpose": "Module 6 — Key Threat Intelligence Sources"},
    {"num": "07", "file": "07_CTI_Module_7_-_Understanding_Indicators_of_Compromise.zip",
     "size": "126 MB",
     "purpose": "Module 7 — Understanding Indicators of Compromise (IOCs)"},
    {"num": "08", "file": "08_CTI_Module_8_-_Analyzing_Threat_Intelligence.zip",
     "size": "134 MB",
     "purpose": "Module 8 — Analyzing Threat Intelligence"},
]
DAY2_BUNDLES_S3_PREFIX = "https://wic-krakow-2026.s3.eu-central-1.amazonaws.com/public/day2-bundles/"

AUTH_USER = "wic"
AUTH_PASS = os.environ["UPLOADER_PASSWORD"]

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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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


def _material_file(subdir: str, filename: str | None) -> dict | None:
    """Look up one material file on disk; return display metadata or None if missing."""
    if not filename:
        return None
    fp = MATERIALS_DIR / subdir / filename
    try:
        size = fp.stat().st_size
    except OSError:
        return None
    return {
        "filename": filename,
        "url": f"/materials/{subdir}/{filename}",
        "size_h": fmt_size(size),
        "kind": kind_label(filename),
    }


def discover_modules():
    out = []
    for m in MODULE_META:
        en = _material_file("modules", f"ins_ukraine_stepUP_module{m['num']}_rev0.pptx")
        uk = _material_file("modules", f"ins_ukraine_stepUP_module{m['num']}_rev0_ukr.pptx")
        out.append({**m, "en": en, "uk": uk})
    return out


def discover_exercises():
    out = []
    for e in EXERCISE_META:
        player_en = _material_file("exercises", e.get("player_en"))
        player_uk = _material_file("exercises", e.get("player_uk"))
        answer_keys = [f for f in (_material_file("answer-keys", k) for k in e.get("answer_keys", [])) if f]
        # Some Ex03 files live under exercises/ — try that path as a fallback
        supplementary = [f for f in (_material_file("exercises", k) for k in e.get("answer_keys", [])) if f]
        out.append({
            **e,
            "player_en_meta": player_en,
            "player_uk_meta": player_uk,
            "answer_keys_meta": answer_keys,
            "supplementary_meta": supplementary,
        })
    return out


def discover_printer():
    return [dict(b, meta=_material_file("printer", b["file"])) for b in PRINTER_BUNDLES]


def discover_sources():
    return [dict(s, meta=_material_file("sources", s["file"])) for s in SOURCES]


@app.get("/materials")
@auth_required
def materials():
    return render_template(
        "materials.html",
        title=WORKSHOP_TITLE,
        modules=discover_modules(),
        exercises=discover_exercises(),
        printer=discover_printer(),
        sources=discover_sources(),
        day2_bundles=DAY2_BUNDLES,
        day2_s3_prefix=DAY2_BUNDLES_S3_PREFIX,
    )


@app.get("/materials/uk")
@auth_required
def materials_uk():
    return render_template(
        "materials.uk.html",
        title=WORKSHOP_TITLE,
        modules=discover_modules(),
        exercises=discover_exercises(),
        printer=discover_printer(),
        sources=discover_sources(),
        day2_bundles=DAY2_BUNDLES,
        day2_s3_prefix=DAY2_BUNDLES_S3_PREFIX,
    )


@app.get("/day2-bundles")
@auth_required
def day2_bundles_page():
    # Faithful replica of the hmi-stepup3 /day-2-bundles page — same URLs, same structure,
    # just served from wic-krakow-web so it survives the hmi-stepup3 tear-down.
    return render_template(
        "day2_bundles.html",
        title=WORKSHOP_TITLE,
        bundles=DAY2_BUNDLES,
        s3_prefix=DAY2_BUNDLES_S3_PREFIX,
    )


@app.get("/materials/<subdir>/<path:filename>")
@auth_required
def material_download(subdir: str, filename: str):
    if subdir.startswith(".") or ".." in subdir or subdir not in {"modules", "exercises", "answer-keys", "printer", "sources"}:
        abort(404)
    base = (MATERIALS_DIR / subdir).resolve()
    if not base.is_dir():
        abort(404)
    as_attachment = request.args.get("download") == "1"
    return send_from_directory(base, filename, as_attachment=as_attachment)


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


@app.get("/healthz")
def health():
    return "ok\n"
