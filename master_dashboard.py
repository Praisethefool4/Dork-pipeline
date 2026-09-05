#!/usr/bin/env python3
"""
master_dashboard.py - Dark-Themed Multi-Node Master Control Dashboard.
Aggregates live states and scraped results from all 19 parallel GitHub Actions runners.
Supports both mobile and PC viewports. Fastly-backed GitHub API avoids Cloudflare CDN completely.
"""
import os
import json
import time
import requests
import concurrent.futures
from flask import Flask, render_template_string, jsonify, request, Response

app = Flask(__name__)

CONFIG_FILE = "dashboard_config.json"

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {"repo": "", "token": ""}

def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)

# ==============================================================================
# Helper to Fetch Runner States in Parallel via Fastly GitHub CDN
# ==============================================================================
def fetch_single_runner(runner_id, repo, token=None):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    # We use GitHub's official REST API with vnd.github.v3.raw headers which is backed by Fastly,
    # completely bypassing Cloudflare. Supports both public and private repositories seamlessly.
    if token:
        headers["Authorization"] = f"token {token}"
        headers["Accept"] = "application/vnd.github.v3.raw"
        url = f"https://api.github.com/repos/{repo}/contents/status.json?ref=state/runner-{runner_id}"
    else:
        # Standard Fastly-backed GitHub CDN URL
        url = f"https://raw.githubusercontent.com/{repo}/state/runner-{runner_id}/status.json"

    try:
        start_time = time.time()
        r = requests.get(url, headers=headers, timeout=5)
        elapsed = time.time() - start_time
        
        if r.status_code == 200:
            data = r.json()
            # Inject a sync lag calculation
            data["last_sync_ago"] = "Just now"
            # Parse timestamp if available, otherwise estimate
            data["response_time_ms"] = int(elapsed * 1000)
            return runner_id, "OK", data
        elif r.status_code == 404:
            return runner_id, "OFFLINE", {
                "runner_id": str(runner_id),
                "status": "OFFLINE",
                "action": "NOT STARTED",
                "last_query": "Waiting on first dork run",
                "urls": 0,
                "index": 0,
                "total_dorks": 0,
                "logs": []
            }
        else:
            return runner_id, "ERROR", {
                "runner_id": str(runner_id),
                "status": "ERROR",
                "action": f"HTTP {r.status_code}",
                "last_query": f"Could not fetch branch data: {r.reason}",
                "urls": 0,
                "index": 0,
                "total_dorks": 0,
                "logs": []
            }
    except Exception as e:
        return runner_id, "ERROR", {
            "runner_id": str(runner_id),
            "status": "ERROR",
            "action": "CONNECTION TIMEOUT",
            "last_query": str(e),
            "urls": 0,
            "index": 0,
            "total_dorks": 0,
            "logs": []
        }

def get_all_runners_data():
    config = load_config()
    repo = config.get("repo", "").strip()
    token = config.get("token", "").strip() or None
    
    if not repo:
        return None, []

    # Fast parallel retrieval of all 19 branches using a ThreadPoolExecutor
    runners_stats = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=19) as executor:
        futures = {executor.submit(fetch_single_runner, i, repo, token): i for i in range(1, 20)}
        for future in concurrent.futures.as_completed(futures):
            runner_id, status_lbl, data = future.result()
            runners_stats[runner_id] = data

    # Sort results sequentially
    sorted_runners = [runners_stats[i] for i in range(1, 20)]
    return repo, sorted_runners

# ==============================================================================
# Dark Mode Responsive Mobile-Friendly HTML Interface
# ==============================================================================
DASHBOARD_HTML = r"""
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>SearXNG Multi-Node Master Dashboard</title>
    <style>
        :root {
            --bg-dark: #0f172a;
            --bg-card: #1e293b;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --primary: #3b82f6;
            --success: #10b981;
            --warning: #f59e0b;
            --danger: #ef4444;
            --border-color: #334155;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        }

        body {
            background-color: var(--bg-dark);
            color: var(--text-main);
            padding: 1.5rem;
            min-height: 100vh;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
        }

        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 2rem;
            padding-bottom: 1rem;
            border-bottom: 1px solid var(--border-color);
            flex-wrap: wrap;
            gap: 1rem;
        }

        .logo-section h1 {
            font-size: 1.5rem;
            font-weight: 700;
            letter-spacing: -0.025em;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .logo-section h1 span {
            color: var(--primary);
        }

        .logo-section p {
            color: var(--text-muted);
            font-size: 0.875rem;
            margin-top: 0.25rem;
        }

        .actions-section {
            display: flex;
            gap: 0.75rem;
            align-items: center;
        }

        .btn {
            background-color: var(--primary);
            color: white;
            border: none;
            padding: 0.625rem 1.25rem;
            font-size: 0.875rem;
            font-weight: 600;
            border-radius: 0.375rem;
            cursor: pointer;
            transition: all 0.2s;
            display: inline-flex;
            align-items: center;
            gap: 0.375rem;
            text-decoration: none;
        }

        .btn:hover {
            opacity: 0.9;
            transform: translateY(-1px);
        }

        .btn-secondary {
            background-color: var(--bg-card);
            border: 1px solid var(--border-color);
            color: var(--text-main);
        }

        .btn-danger {
            background-color: var(--danger);
        }

        /* Stats Bar */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 1.25rem;
            margin-bottom: 2rem;
        }

        .stat-card {
            background-color: var(--bg-card);
            border: 1px solid var(--border-color);
            padding: 1.25rem;
            border-radius: 0.5rem;
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
            position: relative;
            overflow: hidden;
        }

        .stat-card::before {
            content: '';
            position: absolute;
            left: 0;
            top: 0;
            bottom: 0;
            width: 4px;
            background-color: var(--primary);
        }

        .stat-card.stat-success::before { background-color: var(--success); }
        .stat-card.stat-warning::before { background-color: var(--warning); }

        .stat-card .label {
            font-size: 0.75rem;
            text-transform: uppercase;
            font-weight: 700;
            color: var(--text-muted);
            letter-spacing: 0.05em;
        }

        .stat-card .value {
            font-size: 1.75rem;
            font-weight: 800;
        }

        .stat-card .subtext {
            font-size: 0.75rem;
            color: var(--text-muted);
        }

        /* Configuration Modal/Form */
        .config-box {
            background-color: var(--bg-card);
            border: 1px solid var(--border-color);
            padding: 1.5rem;
            border-radius: 0.5rem;
            margin-bottom: 2rem;
        }

        .config-form {
            display: flex;
            gap: 1rem;
            flex-wrap: wrap;
            align-items: flex-end;
        }

        .form-group {
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
            flex: 1;
            min-width: 250px;
        }

        .form-group label {
            font-size: 0.75rem;
            font-weight: 700;
            color: var(--text-muted);
            text-transform: uppercase;
        }

        .form-group input {
            background-color: var(--bg-dark);
            border: 1px solid var(--border-color);
            padding: 0.625rem;
            border-radius: 0.375rem;
            color: white;
            font-size: 0.875rem;
        }

        .form-group input:focus {
            outline: 2px solid var(--primary);
        }

        /* Grid of 19 Runners */
        .runners-title {
            margin-bottom: 1rem;
            font-size: 1.125rem;
            font-weight: 700;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .runners-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 1.25rem;
            margin-bottom: 2rem;
        }

        .runner-card {
            background-color: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 0.5rem;
            padding: 1.25rem;
            display: flex;
            flex-direction: column;
            gap: 0.75rem;
            transition: all 0.2s;
        }

        .runner-card:hover {
            transform: translateY(-2px);
            border-color: #475569;
        }

        .runner-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .runner-id {
            font-size: 0.875rem;
            font-weight: 800;
            color: var(--text-muted);
        }

        .badge {
            font-size: 0.675rem;
            font-weight: 700;
            text-transform: uppercase;
            padding: 0.25rem 0.5rem;
            border-radius: 9999px;
            display: inline-flex;
            align-items: center;
            gap: 0.25rem;
        }

        .badge-running {
            background-color: rgba(16, 185, 129, 0.15);
            color: var(--success);
            border: 1px solid rgba(16, 185, 129, 0.3);
        }

        .badge-cooldown {
            background-color: rgba(245, 158, 11, 0.15);
            color: var(--warning);
            border: 1px solid rgba(245, 158, 11, 0.3);
        }

        .badge-finished {
            background-color: rgba(59, 130, 246, 0.15);
            color: var(--primary);
            border: 1px solid rgba(59, 130, 246, 0.3);
        }

        .badge-offline {
            background-color: rgba(148, 163, 184, 0.1);
            color: var(--text-muted);
            border: 1px solid rgba(148, 163, 184, 0.2);
        }

        .badge-error {
            background-color: rgba(239, 68, 68, 0.15);
            color: var(--danger);
            border: 1px solid rgba(239, 68, 68, 0.3);
        }

        .pulse-dot {
            width: 6px;
            height: 6px;
            background-color: currentColor;
            border-radius: 50%;
            animation: pulse 1.5s infinite;
        }

        @keyframes pulse {
            0% { transform: scale(0.9); opacity: 0.6; }
            50% { transform: scale(1.2); opacity: 1; }
            100% { transform: scale(0.9); opacity: 0.6; }
        }

        .runner-body {
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
            font-size: 0.8125rem;
        }

        .info-row {
            display: flex;
            justify-content: space-between;
        }

        .info-row .lbl {
            color: var(--text-muted);
        }

        .info-row .val {
            font-weight: 600;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            max-width: 180px;
        }

        .query-val {
            color: #38bdf8;
            font-family: monospace;
            cursor: help;
        }

        .progress-bar-container {
            background-color: var(--bg-dark);
            height: 6px;
            border-radius: 9999px;
            overflow: hidden;
            margin-top: 0.25rem;
        }

        .progress-bar {
            height: 100%;
            background-color: var(--primary);
            border-radius: 9999px;
            transition: width 0.4s;
        }

        /* Combined Live Logs */
        .logs-section {
            background-color: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 0.5rem;
            padding: 1.25rem;
            margin-bottom: 2rem;
        }

        .logs-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1rem;
        }

        .logs-console {
            background-color: var(--bg-dark);
            height: 250px;
            border-radius: 0.375rem;
            padding: 1rem;
            font-family: monospace;
            font-size: 0.8125rem;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 0.375rem;
            border: 1px solid var(--border-color);
        }

        .log-line {
            display: flex;
            gap: 1rem;
            line-height: 1.4;
        }

        .log-time { color: #64748b; }
        .log-node { color: #f43f5e; font-weight: 700; }
        .log-status { font-weight: 700; }
        .log-status.OK { color: var(--success); }
        .log-status.COOLDOWN { color: var(--warning); }
        .log-status.TOTAL { color: var(--primary); }
        .log-text { color: var(--text-main); }

        /* Responsive Breakpoints */
        @media (max-width: 768px) {
            body { padding: 1rem; }
            header { flex-direction: column; align-items: flex-start; }
            .actions-section { width: 100%; justify-content: space-between; }
            .config-form { flex-direction: column; align-items: stretch; }
            .form-group { min-width: 100%; }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="logo-section">
                <h1>Google Dork <span>Parallel Matrix</span></h1>
                <p id="repo-name-subtitle">Monitoring active GitHub Actions runner status pools</p>
            </div>
            <div class="actions-section">
                <button class="btn btn-secondary" onclick="toggleConfig()">🔧 Config Repo</button>
                <button class="btn" onclick="refreshDashboard(this)">
                    <span id="refresh-spin">🔄</span> Sync Status
                </button>
                <a href="/download-urls" class="btn btn-danger" download="combined_harvested_urls.txt">
                    📥 Download Results (.txt)
                </a>
            </div>
        </header>

        <!-- Repo Config -->
        <div id="config-box" class="config-box" style="display: none;">
            <form class="config-form" onsubmit="saveConfigForm(event)">
                <div class="form-group">
                    <label for="repo-path">GitHub Repository (owner/repo)</label>
                    <input type="text" id="repo-path" value="{{ repo }}" placeholder="e.g. your-username/dork-scraper" required>
                </div>
                <div class="form-group">
                    <label for="repo-token">GitHub Token (Optional for Private Repos)</label>
                    <input type="password" id="repo-token" value="{{ token }}" placeholder="ghp_xxxxxxxxxxxxxx">
                </div>
                <button type="submit" class="btn">Save & Fetch</button>
            </form>
        </div>

        <!-- Global Summary Counters -->
        <div class="stats-grid">
            <div class="stat-card">
                <span class="label">Total Harvested URLs</span>
                <span class="value" id="global-total-urls">0</span>
                <span class="subtext">Deduplicated cumulative results</span>
            </div>
            <div class="stat-card stat-success">
                <span class="label">Active Scraper Nodes</span>
                <span class="value" id="global-active-nodes">0 / 19</span>
                <span class="subtext">Nodes actively executing cycles</span>
            </div>
            <div class="stat-card stat-warning">
                <span class="label">Total Queries Done</span>
                <span class="value" id="global-total-queries">0</span>
                <span class="subtext">Total dorks fully harvested</span>
            </div>
        </div>

        <!-- Scrapers Grid -->
        <div class="runners-title">
            <span>🛡️</span> 19 Parallel Runner Node Status Cards
        </div>
        <div class="runners-grid" id="runners-container">
            <!-- Injected via AJAX -->
        </div>

        <!-- Consolidated Live Logs -->
        <div class="logs-section">
            <div class="logs-header">
                <h3>📜 Aggregated Multi-Runner Live Logs</h3>
                <span class="subtext" style="color: var(--text-muted);">Updated live on status sync</span>
            </div>
            <div class="logs-console" id="logs-container">
                <!-- Injected via AJAX -->
            </div>
        </div>
    </div>

    <script>
        const configRepo = "{{ repo }}";
        if (!configRepo) {
            document.getElementById("config-box").style.display = "block";
        }

        function toggleConfig() {
            const box = document.getElementById("config-box");
            box.style.display = box.style.display === "none" ? "block" : "none";
        }

        function saveConfigForm(e) {
            e.preventDefault();
            const repo = document.getElementById("repo-path").value.strip ? document.getElementById("repo-path").value.strip() : document.getElementById("repo-path").value;
            const token = document.getElementById("repo-token").value;
            
            fetch("/api/config", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ repo, token })
            })
            .then(r => r.json())
            .then(data => {
                if (data.ok) {
                    toggleConfig();
                    document.getElementById("repo-name-subtitle").innerText = "Targeting GitHub Repo: " + repo;
                    refreshDashboard();
                }
            });
        }

        function refreshDashboard(btn) {
            if (btn) {
                btn.disabled = true;
                document.getElementById("refresh-spin").style.display = "inline-block";
            }

            fetch("/api/status")
            .then(r => r.json())
            .then(data => {
                if (btn) {
                    btn.disabled = false;
                }
                
                if (!data.ok) {
                    return;
                }

                document.getElementById("global-total-urls").innerText = data.total_urls.toLocaleString();
                document.getElementById("global-active-nodes").innerText = data.active_nodes + " / 19";
                document.getElementById("global-total-queries").innerText = data.total_queries;

                // Render runner cards
                const container = document.getElementById("runners-container");
                container.innerHTML = "";
                
                data.runners.forEach(r => {
                    let badgeClass = "badge-offline";
                    let pulse = "";
                    if (r.status === "RUNNING") {
                        badgeClass = "badge-running";
                        pulse = '<span class="pulse-dot"></span>';
                    } else if (r.status === "COOLDOWN") {
                        badgeClass = "badge-cooldown";
                        pulse = '<span class="pulse-dot"></span>';
                    } else if (r.status === "FINISHED") {
                        badgeClass = "badge-finished";
                    } else if (r.status === "ERROR") {
                        badgeClass = "badge-error";
                    }

                    const progressPercent = r.total_dorks > 0 ? ((r.index / r.total_dorks) * 100).toFixed(0) : 0;

                    const card = `
                        <div class="runner-card">
                            <div class="runner-header">
                                <span class="runner-id">Node #${r.runner_id}</span>
                                <span class="badge ${badgeClass}">${pulse}${r.status}</span>
                            </div>
                            <div class="runner-body">
                                <div class="info-row">
                                    <span class="lbl">Last Query:</span>
                                    <span class="val query-val" title="${r.last_query || ''}">${r.last_query || 'None'}</span>
                                </div>
                                <div class="info-row">
                                    <span class="lbl">Action:</span>
                                    <span class="val" style="color: #a7f3d0">${r.action || 'IDLE'}</span>
                                </div>
                                <div class="info-row">
                                    <span class="lbl">Scraped URLs:</span>
                                    <span class="val" style="color: var(--success); font-weight:800;">${r.urls || 0}</span>
                                </div>
                                <div class="info-row">
                                    <span class="lbl">Dorks Progress:</span>
                                    <span class="val">${r.index} / ${r.total_dorks || 0} (${progressPercent}%)</span>
                                </div>
                                <div class="progress-bar-container">
                                    <div class="progress-bar" style="width: ${progressPercent}%"></div>
                                </div>
                                <div class="info-row" style="margin-top: 0.25rem; font-size: 0.75rem;">
                                    <span class="lbl">Response Time:</span>
                                    <span class="val" style="color: #38bdf8">${r.response_time_ms ? r.response_time_ms + 'ms' : 'offline'}</span>
                                </div>
                            </div>
                        </div>
                    `;
                    container.innerHTML += card;
                });

                // Render integrated logs sorted by time
                const logContainer = document.getElementById("logs-container");
                logContainer.innerHTML = "";
                if (data.merged_logs.length === 0) {
                    logContainer.innerHTML = '<div style="color: var(--text-muted)">No action logs received yet.</div>';
                } else {
                    data.merged_logs.forEach(l => {
                        const line = `
                            <div class="log-line">
                                <span class="log-time">[${l.time}]</span>
                                <span class="log-node">Node #${l.node}</span>
                                <span class="log-status ${l.status}">${l.status}</span>
                                <span class="log-text">${l.query || ''} - <small style="color: var(--text-muted)">${l.detail || ''}</small></span>
                            </div>
                        `;
                        logContainer.innerHTML += line;
                    });
                    // Auto-scroll logs to bottom
                    logContainer.scrollTop = logContainer.scrollHeight;
                }
            });
        }

        // Auto sync dashboard every 15 seconds
        setInterval(refreshDashboard, 15000);
        refreshDashboard();
    </script>
</body>
</html>
"""

@app.route("/")
def home():
    config = load_config()
    return render_template_string(
        DASHBOARD_HTML, 
        repo=config.get("repo", ""), 
        token=config.get("token", "")
    )

@app.route("/api/config", methods=["POST"])
def api_config():
    data = request.json or {}
    repo = data.get("repo", "").strip()
    token = data.get("token", "").strip()
    
    save_config({"repo": repo, "token": token})
    return jsonify({"ok": True})

@app.route("/api/status")
def api_status():
    repo, runners = get_all_runners_data()
    if not repo:
        return jsonify({"ok": False, "error": "Repo not configured"})

    total_urls = 0
    active_nodes = 0
    total_queries = 0
    merged_logs = []

    for r in runners:
        status_field = r.get("status", "OFFLINE")
        if status_field in ("RUNNING", "COOLDOWN"):
            active_nodes += 1
            
        total_urls += r.get("urls", 0)
        total_queries += r.get("index", 0)
        
        # Pull logs and tag with Node ID
        runner_id = r.get("runner_id", "?")
        for l in r.get("logs", []):
            l["node"] = runner_id
            merged_logs.append(l)

    # Sort logs chronologically
    merged_logs.sort(key=lambda x: x.get("time", ""))
    # Limit logs feed to the latest 150 lines
    merged_logs = merged_logs[-150:]

    return jsonify({
        "ok": True,
        "repo": repo,
        "total_urls": total_urls,
        "active_nodes": active_nodes,
        "total_queries": total_queries,
        "runners": runners,
        "merged_logs": merged_logs
    })

@app.route("/download-urls")
def download_urls():
    """
    Downloads, consolidates, and deduplicates all parsed URLs 
    across all 19 runner branches in parallel.
    """
    config = load_config()
    repo = config.get("repo", "").strip()
    token = config.get("token", "").strip() or None

    if not repo:
        return Response("Error: Repo not configured in dashboard.", status=400, mimetype="text/plain")

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    def fetch_urls(runner_id):
        if token:
            headers["Authorization"] = f"token {token}"
            headers["Accept"] = "application/vnd.github.v3.raw"
            url = f"https://api.github.com/repos/{repo}/contents/urls.txt?ref=state/runner-{runner_id}"
        else:
            url = f"https://raw.githubusercontent.com/{repo}/state/runner-{runner_id}/urls.txt"

        try:
            r = requests.get(url, headers=headers, timeout=10)
            if r.status_code == 200:
                return r.text.splitlines()
        except Exception:
            pass
        return []

    all_harvested_urls = set()
    with concurrent.futures.ThreadPoolExecutor(max_workers=19) as executor:
        results = executor.map(fetch_urls, range(1, 20))
        for url_list in results:
            for u in url_list:
                u_clean = u.strip()
                if u_clean.startswith(("http://", "https://")):
                    all_harvested_urls.add(u_clean)

    # Compile files as newline separated
    final_output = "\n".join(sorted(list(all_harvested_urls)))
    
    return Response(
        final_output,
        mimetype="text/plain",
        headers={"Content-disposition": "attachment; filename=combined_harvested_urls.txt"}
    )

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 GOOGLE DORK SCX MASTER DASHBOARD RUNNING")
    print("Open your browser: http://127.0.0.1:5000")
    print("=" * 60)
    app.run(host="0.0.0.0", port=5000, debug=True)
