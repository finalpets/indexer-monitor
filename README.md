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

### Managing the monitor on Windows (PowerShell)

**Run in background (terminal can be closed):**
```powershell
Start-Process python -ArgumentList "c:\path\to\nzbgeek-monitor\monitor.py" -WindowStyle Hidden
```

**Check if it's running:**
```powershell
Get-Process python -ErrorAction SilentlyContinue
```

**See running instance with its full command:**
```powershell
Get-WmiObject Win32_Process -Filter "Name='python.exe'" | Select-Object ProcessId, CommandLine
```

**Stop the monitor:**
```powershell
Stop-Process -Name python -Force
```

> **Note:** `Stop-Process -Name python -Force` will kill **all** Python processes. If you're running other Python scripts, stop by ProcessId instead:
> ```powershell
> Stop-Process -Id <PID> -Force
> ```

### Auto-start on Windows boot (Task Scheduler)

1. Open **Task Scheduler** → Create Basic Task
2. Trigger: **When the computer starts**
3. Action: **Start a program**
   - Program: `python`
   - Arguments: `c:\path\to\nzbgeek-monitor\monitor.py`
   - Start in: `c:\path\to\nzbgeek-monitor`
4. In **Properties → General**, check **Run whether user is logged on or not**

---

## Method 4 — UNRAID (Python directly, no Docker)

If you prefer not to use Docker, you can run the script directly from the UNRAID terminal.

```bash
# Install pip if needed
python3 -m ensurepip --upgrade

# Clone and set up
git clone https://github.com/YOUR_USERNAME/nzbgeek-monitor.git /mnt/user/appdata/nzbgeek-monitor
cd /mnt/user/appdata/nzbgeek-monitor

pip3 install -r requirements.txt

mkdir -p data
cp config.example.json data/config.json
# Edit data/config.json with your values
nano data/config.json

python3 monitor.py
```

### Managing the monitor on UNRAID / Linux

**Run in background (survives closing the terminal):**
```bash
nohup python3 /mnt/user/appdata/nzbgeek-monitor/monitor.py > /mnt/user/appdata/nzbgeek-monitor/monitor.log 2>&1 &
echo "PID: $!"
```

**Check if it's running:**
```bash
pgrep -a python3
```

**Watch the log in real time:**
```bash
tail -f /mnt/user/appdata/nzbgeek-monitor/monitor.log
```

**Stop the monitor:**
```bash
# Find the PID first
pgrep -a python3

# Then kill it
kill <PID>
```

**Auto-start on UNRAID boot** — add a User Script (via the **User Scripts** plugin) set to run **At Startup of Array**:
```bash
#!/bin/bash
nohup python3 /mnt/user/appdata/nzbgeek-monitor/monitor.py > /mnt/user/appdata/nzbgeek-monitor/monitor.log 2>&1 &
```

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
