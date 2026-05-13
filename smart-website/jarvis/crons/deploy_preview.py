#!/usr/bin/env python3
"""
deploy_preview.py — Deploy client preview to audit.thesmartwebsite.co/preview/{slug}

Usage:
  python3 deploy_preview.py --slug vibe-garage

Requires:
  - Vercel CLI authenticated (brentc106)
  - Preview HTML at: smart-website/preview/{slug}/index.html
  - TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID (Brent), TELEGRAM_MASON_CHAT_ID env vars

Output:
  Live URL: https://audit.thesmartwebsite.co/preview/{slug}
  Telegram alerts to both Brent and Mason on completion
"""
import os, sys, json, time, subprocess

SLUG = None
for i, arg in enumerate(sys.argv):
    if arg == '--slug' and i + 1 < len(sys.argv):
        SLUG = sys.argv[i + 1]
        break

if not SLUG:
    print("Usage: python3 deploy_preview.py --slug <slug>")
    sys.exit(1)

PREVIEW_DIR = f"/Users/brentext/.openclaw/workspace/smart-website/dist/preview/{SLUG}"
VERCEL_PROJECT = "smart-website-audits"
LIVE_URL = f"https://audit.thesmartwebsite.co/preview/{SLUG}"

BRENT_CHAT_ID = "7356494332"
BRENT_BOT_TOKEN = "8861024946:AAEVy23QjH1puYzlzKz1McQ6LP7dp-cM9Js"
BOT_TOKEN = BRENT_BOT_TOKEN

def log(msg): print(f"[deploy] {msg}", flush=True)

def send_telegram(chat_id, text):
    if not BOT_TOKEN or not chat_id:
        log(f"Skipping Telegram (missing token or chat_id)")
        return False
    try:
        import urllib.request
        data = json.dumps({"chat_id": chat_id, "text": text}).encode()
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data=data,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=10):
            return True
    except Exception as e:
        log(f"Telegram error for {chat_id}: {e}")
        return False

def deploy():
    if not os.path.exists(PREVIEW_DIR):
        log(f"ERROR: Preview dir not found: {PREVIEW_DIR}")
        log(f"Mason must place preview HTML at: {PREVIEW_DIR}/index.html")
        return False

    log(f"Deploying {SLUG} → {LIVE_URL}")

    result = subprocess.run(
        ["npx", "vercel", "--prod", "--yes", "--cwd", PREVIEW_DIR],
        capture_output=True, text=True, timeout=60
    )
    output = result.stdout + result.stderr

    if result.returncode != 0:
        log(f"Vercel deploy failed:\n{output[-500]}")
        return False

    # Find deployment URL from output
    for line in output.split('\n'):
        if 'https://' in line and 'vercel.app' in line:
            deployed_url = line.strip().split()[0]
            log(f"Deployed: {deployed_url}")
            break
    else:
        log(f"Deployed (URL parsing uncertain): {LIVE_URL}")

    return True

def notify_completion():
    msg = f"""✅ Preview deployed

Business: {SLUG.replace('-', ' ').title()}
Preview: {LIVE_URL}

Review it → {LIVE_URL}
Approve or request changes.

— Jarvis, Smart Website Co."""

    # Send to Brent
    sent_brent = send_telegram(BRENT_CHAT_ID, msg)
    log(f"Brent notified: {'OK' if sent_brent else 'FAILED'}")

def main():
    log(f"Starting deploy for: {SLUG}")
    ok = deploy()
    if ok:
        notify_completion()
        log(f"✅ DONE: {LIVE_URL}")
    else:
        log("❌ Deploy failed — check above")

if __name__ == "__main__":
    main()