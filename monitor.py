import json
import re
import time
import os
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

DATA_DIR = Path(os.environ.get("DATA_DIR", "./data"))
CONFIG_PATH = DATA_DIR / "config.json"
SEEN_PATH = DATA_DIR / "seen.json"

# Matches Spanish/Castellano indicators in release names (dot-separated words)
SPANISH_RE = re.compile(
    r"(?<![a-zA-Z])(spanish|castellano|cast|latino|latin)(?![a-zA-Z])|\.es\.",
    re.IGNORECASE,
)

DISCORD_COLOR = 0xE53935  # Red


def load_config():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


def load_seen():
    if SEEN_PATH.exists():
        with open(SEEN_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_seen(seen):
    with open(SEEN_PATH, "w", encoding="utf-8") as f:
        json.dump(seen, f, indent=2)


def clean_seen(seen, days=30):
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    return {
        k: v
        for k, v in seen.items()
        if datetime.fromisoformat(v) > cutoff
    }


def fetch_releases(indexer):
    params = {
        "t": "search",
        "cat": indexer.get("categories", "2000"),
        "limit": indexer.get("result_limit", 100),
        "apikey": indexer["api_key"],
        "o": "json",
        "extended": "1",
    }
    resp = requests.get(indexer["api_url"], params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    # Newznab JSON puts items under channel.item or directly under item
    channel = data.get("channel", data)
    items = channel.get("item", [])
    if isinstance(items, dict):
        items = [items]
    return items


def get_attrs(item):
    """Normalize newznab:attr across different JSON serializations."""
    raw = item.get("attr", item.get("newznab:attr", []))
    if isinstance(raw, dict):
        raw = [raw]
    result = {}
    for a in raw:
        # NZBGeek wraps name/value inside @attributes
        if "@attributes" in a:
            a = a["@attributes"]
        name = (a.get("@name") or a.get("name", "")).lower()
        value = a.get("@value") or a.get("value", "")
        if name:
            result[name] = str(value)
    return result


def get_release_group(title):
    parts = title.rsplit("-", 1)
    return parts[1].strip() if len(parts) == 2 else ""


def is_spanish(item, mode, trusted_groups=None):
    title = item.get("title", "")
    if trusted_groups:
        group = get_release_group(title)
        if any(g.lower() == group.lower() for g in trusted_groups):
            return True
    if mode == "api_and_title":
        attrs = get_attrs(item)
        lang = attrs.get("language", "").lower()
        if lang in ("es", "spa", "spanish", "castellano", "cast", "latino"):
            return True
    return bool(SPANISH_RE.search(title))


def get_guid(item):
    attrs = get_attrs(item)
    if attrs.get("guid"):
        return attrs["guid"]
    guid = item.get("guid", "")
    if isinstance(guid, dict):
        guid = guid.get("#text") or guid.get("content") or ""
    return str(guid) or item.get("link", "")


def get_imdb_id(attrs):
    imdb = attrs.get("imdb", attrs.get("imdbid", attrs.get("imdb_id", "")))
    if not imdb:
        return ""
    imdb = str(imdb).strip()
    if imdb.isdigit():
        return f"tt{imdb.zfill(7)}"
    if not imdb.startswith("tt"):
        return f"tt{imdb}"
    return imdb


def fetch_omdb_poster(imdb_id, omdb_key):
    """Return poster URL from OMDB, or empty string if unavailable."""
    if not imdb_id or not omdb_key:
        return ""
    try:
        resp = requests.get(
            "https://www.omdbapi.com/",
            params={"i": imdb_id, "apikey": omdb_key},
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            poster = data.get("Poster", "")
            if poster and poster != "N/A":
                return poster
    except Exception as e:
        log.warning("OMDB error para %s: %s", imdb_id, e)
    return ""


def format_size(raw):
    try:
        size = int(raw)
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} PB"
    except (ValueError, TypeError):
        return "—"


def time_ago(pub_date_str):
    try:
        from email.utils import parsedate_to_datetime
        pub = parsedate_to_datetime(pub_date_str)
        hours = int((datetime.now(timezone.utc) - pub).total_seconds() / 3600)
        if hours < 1:
            return "< 1 hora"
        if hours < 24:
            return f"{hours}h"
        return f"{hours // 24}d"
    except Exception:
        return pub_date_str or "—"


def build_embed(item, indexer_name, omdb_key=""):
    attrs = get_attrs(item)
    enclosure = item.get("enclosure", {})
    size_raw = attrs.get("size") or enclosure.get("@length") or enclosure.get("length", "")
    category = item.get("category") or attrs.get("category", "Movies")
    pub_date = item.get("pubDate", "")
    link = item.get("link", "") or item.get("comments", "")
    if isinstance(link, dict):
        link = link.get("#text", "")

    imdb_id = get_imdb_id(attrs)
    imdb_url = f"https://www.imdb.com/title/{imdb_id}/" if imdb_id else ""
    poster_url = fetch_omdb_poster(imdb_id, omdb_key)

    description = f"**{item.get('title', '?')}**"
    if imdb_url:
        description += f"\n[Ver en IMDb ↗]({imdb_url})"

    embed = {
        "title": f"\U0001f1ea\U0001f1f8 Nueva película — {indexer_name}",
        "description": description,
        "color": DISCORD_COLOR,
        "fields": [
            {"name": "Tamaño", "value": format_size(size_raw), "inline": True},
            {"name": "Categoría", "value": str(category), "inline": True},
            {"name": "Subido", "value": time_ago(pub_date), "inline": True},
        ],
        "footer": {"text": f"NZB Monitor • {indexer_name}"},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if link:
        embed["url"] = link
    if poster_url:
        embed["thumbnail"] = {"url": poster_url}
    return embed


def send_discord(webhook_url, embeds):
    for i in range(0, len(embeds), 10):
        chunk = embeds[i : i + 10]
        try:
            resp = requests.post(webhook_url, json={"embeds": chunk}, timeout=10)
            if resp.status_code not in (200, 204):
                log.error("Discord error %s: %s", resp.status_code, resp.text[:200])
        except Exception as e:
            log.error("Error enviando a Discord: %s", e)
        if i + 10 < len(embeds):
            time.sleep(1)


def check_indexer(indexer, seen, webhook_url, trusted_groups=None, omdb_key=""):
    name = indexer["name"]
    mode = indexer.get("language_detection", "title_only")
    log.info("[%s] Consultando API...", name)

    try:
        items = fetch_releases(indexer)
    except Exception as e:
        log.error("[%s] Error al consultar API: %s", name, e)
        return

    log.info("[%s] %d releases recibidos", name, len(items))

    new_embeds = []
    for item in items:
        if not is_spanish(item, mode, trusted_groups):
            continue
        guid = get_guid(item)
        key = f"{name}:{guid}"
        if not guid or key in seen:
            continue
        new_embeds.append(build_embed(item, name, omdb_key))
        seen[key] = datetime.now(timezone.utc).isoformat()

    if new_embeds:
        log.info("[%s] %d nuevas en español → Discord", name, len(new_embeds))
        send_discord(webhook_url, new_embeds)
    else:
        log.info("[%s] Sin novedades en español", name)


def run():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if not CONFIG_PATH.exists():
        log.error("No se encontró config.json en %s", DATA_DIR)
        log.error("Copia config.example.json a data/config.json y completa los valores.")
        raise SystemExit(1)

    config = load_config()
    webhook = config["discord_webhook_url"]
    interval_secs = config.get("check_interval_hours", 2) * 3600
    indexers = [i for i in config.get("indexers", []) if i.get("enabled", True)]
    trusted_groups = config.get("trusted_groups", [])
    omdb_key = config.get("omdb_api_key", "")

    if not indexers:
        log.error("No hay indexers habilitados en config.json")
        raise SystemExit(1)

    log.info("NZB Monitor iniciado — indexers: %s", [i["name"] for i in indexers])
    if trusted_groups:
        log.info("Grupos de confianza: %s", trusted_groups)
    if omdb_key:
        log.info("OMDB: pósters habilitados")
    else:
        log.info("OMDB: sin clave API, pósters desactivados")
    log.info("Intervalo de revisión: %.0fh", interval_secs / 3600)

    while True:
        seen = load_seen()
        for indexer in indexers:
            check_indexer(indexer, seen, webhook, trusted_groups, omdb_key)
        seen = clean_seen(seen)
        save_seen(seen)
        log.info("Próxima revisión en %.0fh", interval_secs / 3600)
        time.sleep(interval_secs)


if __name__ == "__main__":
    run()
