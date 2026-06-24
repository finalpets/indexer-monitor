# NZB Spanish Monitor

Monitors one or more Newznab-compatible NZB indexers for new movie releases in Spanish and sends Discord webhook notifications.

Supports **NZBGeek**, **NinjaCentral**, and any other Newznab-compatible indexer. Runs as a Docker container (ideal for UNRAID) or directly with Python on Windows/Linux.

---

## How it works

1. Every N hours, queries each enabled indexer via their Newznab API
2. Filters releases that match Spanish language indicators
3. Sends Discord notifications for releases not seen before
4. Tracks already-notified releases in `seen.json` (auto-cleaned after 30 days)

**Spanish detection** uses two strategies (configurable per indexer):
- `api_and_title` — checks API language attributes first, then falls back to title regex
- `title_only` — regex on the release title only (for indexers without language metadata)

Title keywords matched: `SPANISH`, `CASTELLANO`, `CAST`, `LATINO`, `.ES.`

---

## Prerequisites

- A Newznab API key from each indexer (found in your account settings)
- A Discord webhook URL ([how to create one](https://support.discord.com/hc/en-us/articles/228383668))

---

## Method 1 — UNRAID (Docker)

1. Go to **Docker → Add Container** in your UNRAID dashboard
2. Set the image to `ghcr.io/YOUR_GITHUB_USERNAME/nzbgeek-monitor:latest` (after pushing to GitHub)
   - Or build locally: clone the repo on UNRAID and use **docker compose**
3. Add a **Path** mapping:
   - Container path: `/app/data`
   - Host path: `/mnt/user/appdata/nzbgeek-monitor/`
4. Create `/mnt/user/appdata/nzbgeek-monitor/config.json` based on `config.example.json`
5. Start the container — check logs to confirm it's running

---

## Method 2 — Docker (any OS)

```bash
git clone https://github.com/YOUR_USERNAME/nzbgeek-monitor.git
cd nzbgeek-monitor

# Create your config
mkdir -p data
cp config.example.json data/config.json
# Edit data/config.json with your API keys and Discord webhook

docker compose up -d
docker compose logs -f
```

---

## Method 3 — Windows without Docker

Requirements: Python 3.10+

```bat
git clone https://github.com/YOUR_USERNAME/nzbgeek-monitor.git
cd nzbgeek-monitor

pip install -r requirements.txt

mkdir data
copy config.example.json data\config.json
REM Edit data\config.json with your values

python monitor.py
```

To run automatically, create a Windows Task Scheduler task that runs `python monitor.py` on startup or on a schedule. Set the working directory to the project folder.

---

## Configuration reference (`data/config.json`)

| Field | Type | Description |
|-------|------|-------------|
| `discord_webhook_url` | string | Full Discord webhook URL |
| `check_interval_hours` | number | How often to check (default: `2`) |
| `indexers` | array | List of indexer configs (see below) |

**Per-indexer fields:**

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Display name (shown in Discord notifications) |
| `enabled` | boolean | Set to `false` to skip without removing |
| `api_url` | string | Newznab API base URL |
| `api_key` | string | Your API key |
| `categories` | string | Newznab category codes (default: `"2000"` = Movies) |
| `result_limit` | number | Max results per query (default: `100`) |
| `language_detection` | string | `"api_and_title"` or `"title_only"` |

**`language_detection` values:**

| Value | When to use |
|-------|-------------|
| `api_and_title` | Indexer exposes language in API metadata (e.g. NZBGeek) |
| `title_only` | No language metadata in API — relies on title regex only (e.g. NinjaCentral) |

---

## Adding a new indexer

Add another entry to the `indexers` array in your `config.json`. No code changes needed as long as the indexer is Newznab-compatible.

```json
{
  "name": "MyNewIndexer",
  "enabled": true,
  "api_url": "https://mynewindexer.com/api",
  "api_key": "YOUR_API_KEY",
  "categories": "2000",
  "result_limit": 100,
  "language_detection": "title_only"
}
```

---

## Rate limiting

Most free-tier accounts on NZB indexers have API request limits. Setting `check_interval_hours` to `2` or higher is recommended. Check your indexer's terms of service for exact limits.

---

## License

MIT
