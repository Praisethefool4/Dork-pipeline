#!/usr/bin/env python3
"""
headless_runner.py - Headless background scraper for GitHub Actions.
Supports parallel partition execution, anti-ban rotations, and multi-branch live sync.
"""
import os
import re
import sys
import json
import time
import random
import hashlib
import threading
import subprocess
from pathlib import Path
import requests
from bs4 import BeautifulSoup

# ==============================================================================
# 50+ Realistic, modern User-Agents to mimic organic traffic across browsers
# ==============================================================================
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (X11; Linux x86_64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (X11; Linux x86_64; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3.1 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0",
    "Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 OPR/108.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 OPR/108.0.0.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/119.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/120.0.0.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (X11; Linux x86_64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
]

# ==============================================================================
# Runner Settings Configuration
# ==============================================================================
SEARXNG_URL = os.environ.get("SEARXNG_URL", "http://localhost:8080").strip()
GOOGLE_ENGINE = "google cse"

DORK_FILE = Path("dorks_runner.txt")
RESULTS_FILE = Path("results.txt")
STATE_FILE = Path("worker_state.json")
PROXY_FILE = Path("proxies.txt")

DEFAULT_PAGES = 1
DEFAULT_PAGE_GAP = 35
DEFAULT_QUERY_MIN = 60
DEFAULT_QUERY_MAX = 120
MAX_LOGS = 100

RUNNER_ID = os.environ.get("RUNNER_ID", "1")
GITHUB_REPOSITORY = os.environ.get("GITHUB_REPOSITORY")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")

# ==============================================================================
# Live Git Syncer Thread
# ==============================================================================
class GitSyncer(threading.Thread):
    def __init__(self, interval=180):
        super().__init__()
        self.interval = interval
        self.daemon = True
        self.running = True
        self.branch_name = f"state/runner-{RUNNER_ID}"

    def run(self):
        print(f"[Syncer] Live Syncer initiated. Sync cycle: {self.interval}s")
        # Sync initial status
        self.sync()
        
        while self.running:
            time.sleep(self.interval)
            self.sync()

    def sync(self):
        if not GITHUB_REPOSITORY or not GITHUB_TOKEN:
            print("[Syncer] Git Sync ignored - Running locally outside GitHub Actions environment.")
            return

        try:
            if not STATE_FILE.exists():
                return

            # Capture current running stats
            state_data = STATE_FILE.read_text(encoding="utf-8")
            results_data = RESULTS_FILE.read_text(encoding="utf-8", errors="ignore") if RESULTS_FILE.exists() else ""

            # Use separate temporary folder to ensure parallel file-locks are never triggered
            temp_git_dir = f"/tmp/git_sync_{RUNNER_ID}"
            import shutil
            if os.path.exists(temp_git_dir):
                shutil.rmtree(temp_git_dir)
            os.makedirs(temp_git_dir)

            cwd = temp_git_dir
            subprocess.run(["git", "init"], cwd=cwd, stdout=subprocess.DEVNULL)
            subprocess.run(["git", "config", "user.name", "GitHub Action Scraper"], cwd=cwd, stdout=subprocess.DEVNULL)
            subprocess.run(["git", "config", "user.email", "action@github.com"], cwd=cwd, stdout=subprocess.DEVNULL)

            remote_url = f"https://x-access-token:{GITHUB_TOKEN}@github.com/{GITHUB_REPOSITORY}.git"
            subprocess.run(["git", "remote", "add", "origin", remote_url], cwd=cwd, stdout=subprocess.DEVNULL)

            # Check if remote branch exists to check out, otherwise start clean orphan branch
            res = subprocess.run(["git", "fetch", "origin", self.branch_name], cwd=cwd, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
            if res.returncode == 0:
                subprocess.run(["git", "checkout", self.branch_name], cwd=cwd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                subprocess.run(["git", "checkout", "--orphan", self.branch_name], cwd=cwd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                subprocess.run(["git", "rm", "-rf", "."], cwd=cwd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            # Write synced files
            with open(os.path.join(temp_git_dir, "status.json"), "w", encoding="utf-8") as f:
                f.write(state_data)
            with open(os.path.join(temp_git_dir, "urls.txt"), "w", encoding="utf-8") as f:
                f.write(results_data)

            # Stage, commit and force push
            subprocess.run(["git", "add", "status.json", "urls.txt"], cwd=cwd, stdout=subprocess.DEVNULL)
            subprocess.run(["git", "commit", "-m", f"Sync state for runner {RUNNER_ID} - {int(time.time())}"], cwd=cwd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            push_res = subprocess.run(["git", "push", "-f", "origin", self.branch_name], cwd=cwd, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
            if push_res.returncode == 0:
                print(f"[Syncer] Live sync successfully pushed to branch: {self.branch_name}")
            else:
                print(f"[Syncer] Git push failed for branch {self.branch_name}")

            shutil.rmtree(temp_git_dir)
        except Exception as e:
            print(f"[Syncer] Git live sync run failed: {e}")

# ==============================================================================
# State Manager
# ==============================================================================
state = {
    "index": 0,
    "page": 1,
    "status": "RUNNING",
    "action": "STARTING",
    "last_query": "",
    "last_error": "",
    "last_page_urls": 0,
    "pages": DEFAULT_PAGES,
    "urls": 0,
    "session_new_urls": 0,
    "consecutive_empty": 0,
    "runner_id": RUNNER_ID,
    "logs": []
}

def save_state():
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")

def add_log(index, query, page, urls, new_urls, total_urls, status, detail=""):
    entry = {
        "time": time.strftime("%H:%M:%S"),
        "index": index,
        "query": query,
        "page": page,
        "urls": urls,
        "new_urls": new_urls,
        "total_urls": total_urls,
        "status": status
    }
    if detail:
        entry["detail"] = detail
    state["logs"].append(entry)
    state["logs"] = state["logs"][-MAX_LOGS:]
    save_state()

def load_dorks():
    if not DORK_FILE.exists():
        return []
    return [x.strip() for x in DORK_FILE.read_text(encoding="utf-8", errors="ignore").splitlines() if x.strip()]

def existing_urls():
    if not RESULTS_FILE.exists():
        return set()
    res = set()
    with RESULTS_FILE.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            u = line.strip()
            if u.startswith(("http://", "https://")):
                res.add(u)
    return res

# ==============================================================================
# Core Scraper Functions
# ==============================================================================
def load_proxies():
    if not PROXY_FILE.exists():
        return []
    out = []
    for line in PROXY_FILE.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "://" not in line:
            line = "http://" + line
        out.append(line)
    return list(dict.fromkeys(out))

def apply_proxy(session, proxies):
    if not proxies:
        session.proxies.clear()
        return None
    # Pick a random proxy for this search
    proxy = random.choice(proxies)
    session.proxies.update({"http": proxy, "https": proxy})
    return proxy

def extract_urls(html):
    soup = BeautifulSoup(html, "html.parser")
    urls = []
    for article in soup.select("article.result"):
        a = article.select_one("h3 a[href]") or article.select_one("a.url_header[href]")
        if a:
            u = a.get("href", "").strip()
            if u.startswith(("http://", "https://")):
                urls.append(u)
    if not urls:
        for a in soup.select("h3 a[href]"):
            u = a.get("href", "").strip()
            if u.startswith(("http://", "https://")):
                urls.append(u)
    return list(dict.fromkeys(urls))

def search_page(session, query, page):
    params = {
        "q": query,
        "categories": "general",
        "engines": GOOGLE_ENGINE,
        "pageno": page,
        "language": "en",
        "safesearch": "0",
        "format": "html"
    }
    response = session.get(
        f"{SEARXNG_URL}/search",
        params=params,
        headers={"User-Agent": random.choice(USER_AGENTS)},
        timeout=30
    )
    if response.status_code in (403, 429, 503):
        raise RuntimeError(f"HTTP {response.status_code}")
    response.raise_for_status()
    return extract_urls(response.text), response.elapsed.total_seconds()

def google_cse_status():
    try:
        r = requests.get(f"{SEARXNG_URL}/stats", headers={"User-Agent": random.choice(USER_AGENTS)}, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        for row in soup.find_all("tr"):
            text = " ".join(row.get_text(" ", strip=True).split())
            low = text.lower()
            if "google cse" in low:
                if any(x in low for x in ("suspended", "captcha", "access denied", "too many requests", "timeout")):
                    return "SUSPENDED / BLOCKED", text
                return "OK", text
        return "NOT FOUND", "google cse row not found"
    except Exception as e:
        return "UNKNOWN", str(e)

# ==============================================================================
# Headless Scraper Execution Engine
# ==============================================================================
def main():
    print(f"==========================================================")
    print(f"🚀 HEADLESS SCRAPER ENGINE RUNNER #{RUNNER_ID} ACTIVATED")
    print(f"==========================================================")
    print(f"Target SearXNG instance: {SEARXNG_URL}")

    dorks = load_dorks()
    if not dorks:
        print("❌ Error: No partition dorks loaded inside dorks_runner.txt.")
        state["status"] = "FINISHED"
        state["action"] = "IDLE - Empty dork list"
        save_state()
        return

    print(f"Loaded partition: {len(dorks)} assigned dork(s).")
    
    # Active proxies
    proxies = load_proxies()
    if proxies:
        print(f"Loaded {len(proxies)} static proxies from proxies.txt.")
    else:
        print("Running in DIRECT connection mode (No proxies loaded).")

    session = requests.Session()
    urls_seen = existing_urls()

    # Track state initially
    state["urls"] = len(urls_seen)
    state["total_dorks"] = len(dorks)
    save_state()

    # Start live background Git Syncing Thread (pushes every 3 mins / 180s)
    syncer = GitSyncer(interval=180)
    syncer.start()

    while state["index"] < len(dorks):
        query_number = state["index"] + 1
        query = dorks[state["index"]]
        query_hash = hashlib.sha256(query.encode("utf-8")).hexdigest()

        state["status"] = "RUNNING"
        state["last_query"] = query
        state["page"] = 1
        state["last_error"] = ""
        save_state()

        query_total = 0
        query_new = 0
        pages_done = 0

        # Run page search pagination
        for page in range(1, int(state["pages"]) + 1):
            state["page"] = page
            state["action"] = f"REQUESTING PAGE {page}/{state['pages']}"
            save_state()

            # Pre-check endpoint health status
            health, detail = google_cse_status()
            if health != "OK":
                state["last_error"] = detail
                state["status"] = "COOLDOWN"
                state["action"] = "ENDPOINT HEALTH CHECK FAILED"
                add_log(query_number, query, page, 0, 0, query_total, "GOOGLE CSE SUSPENDED", detail)
                save_state()
                
                # Active Dynamic Cooldown sleep to avoid spamming Google while banned
                cooldown_time = random.uniform(100.0, 150.0)
                print(f"[Cooldown] SearXNG engine reports suspension. Resting for {cooldown_time:.1f}s...")
                time.sleep(cooldown_time)
                continue

            current_proxy = apply_proxy(session, proxies)
            
            try:
                # Retrieve URLs
                urls, elapsed = search_page(session, query, page)
            except Exception as e:
                state["last_error"] = str(e)
                add_log(query_number, query, page, 0, 0, query_total, "REQUEST ERROR", str(e))
                print(f"[Error] Request failed: {e}")
                time.sleep(15.0)  # Safe buffer error pause
                continue

            if not urls:
                # No URLs returned: inspect if it's a silent ban or simply a dry page
                health, detail = google_cse_status()
                state["last_page_urls"] = 0
                pages_done += 1

                add_log(query_number, query, page, 0, 0, query_total, "NO RESULTS", f"Response {detail}")
                
                # Track silent consecutive empties
                state["consecutive_empty"] = state.get("consecutive_empty", 0) + 1
                save_state()

                if state["consecutive_empty"] >= 2:
                    cooldown_time = random.uniform(100.0, 150.0)
                    state["status"] = "COOLDOWN"
                    state["action"] = f"SOFT SUSPENSION COOLING ({cooldown_time:.1f}s)"
                    add_log(query_number, query, page, 0, 0, query_total, "SOFT SUSPENSION", 
                            f"Google rate-limiting suspected (2 consecutive empty results). cooling {cooldown_time:.1f}s")
                    save_state()
                    
                    print(f"[Ban Detected] 2 consecutive 0 URL pages. Initiating suspension cooldown of {cooldown_time:.1f}s...")
                    time.sleep(cooldown_time)
                    state["consecutive_empty"] = 0
                    save_state()
                else:
                    # Single page empty delay jitter
                    page_delay = random.uniform(float(DEFAULT_PAGE_GAP), float(DEFAULT_PAGE_GAP + 10)) + random.uniform(5.0, 15.0)
                    print(f"[Empty result] Jittering for {page_delay:.1f}s...")
                    time.sleep(page_delay)
                continue

            # Successful harvest! Reset consecutive empty counters
            state["consecutive_empty"] = 0
            
            new_urls = 0
            with RESULTS_FILE.open("a", encoding="utf-8") as f:
                for u in urls:
                    if u not in urls_seen:
                        f.write(u + "\n")
                        urls_seen.add(u)
                        new_urls += 1

            query_total += len(urls)
            query_new += new_urls
            pages_done += 1

            state["urls"] = len(urls_seen)
            state["session_new_urls"] += new_urls
            state["last_page_urls"] = len(urls)
            save_state()

            add_log(query_number, query, page, len(urls), new_urls, query_total, "OK", f"Response {elapsed:.1f}s")
            print(f"[Harvest] Page {page} fetched successfully: {len(urls)} found, {new_urls} new URLs.")

            # Page-to-page random transition jitter sleep
            if page < int(state["pages"]):
                page_delay = random.uniform(float(DEFAULT_PAGE_GAP), float(DEFAULT_PAGE_GAP + 10)) + random.uniform(5.0, 15.0)
                time.sleep(page_delay)

        # Log total completed stats for this dork
        add_log(query_number, query, 0, query_total, query_new, query_total, "TOTAL", f"Processed pages for dork")
        
        state["index"] += 1
        state["page"] = 1
        save_state()

        # Query-to-Query random transition jitter sleep
        delay = random.uniform(float(DEFAULT_QUERY_MIN), float(DEFAULT_QUERY_MAX)) + random.uniform(10.0, 30.0)
        print(f"[Dork Finished] Completed dork query {query_number}. Waiting {delay:.1f}s jitter before next...")
        time.sleep(delay)

    # Scrape run finished
    state["status"] = "FINISHED"
    state["action"] = "All assigned queries fully harvested"
    save_state()
    print("🎉 Worker partition fully processed!")

    # Push final sync run to GitHub
    syncer.sync()

if __name__ == "__main__":
    main()
