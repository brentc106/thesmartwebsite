#!/usr/bin/env python3
"""
approval_queue.py — Brent's one-tap HOT lead approval system
Sends Telegram message with top pending HOT leads, waits for reply, fires the build.

Brent replies with the lead # to approve (e.g. "1" or "approve 1")
Or "skip" to skip to next.

Cron: 7 AM daily — only fires if there are pending HOT leads.
"""
import os, json, re, time
from datetime import datetime

TELEGRAM_BOT_TOKEN = "8685067366:AAHQht4DvrqFkM99rwMfhExdrkY8nks78Iw"
TELEGRAM_CHAT_ID = "7356494332"
CRM_FILE = "/Users/brentext/.openclaw/workspace/smart-website/data/leads.jsonl"
QUEUE_FILE = "/Users/brentext/.openclaw/workspace/smart-website/data/approval_queue.json"

def ts(): return datetime.now().strftime("%H:%M")
def log(msg): print(f"[{ts()}] {msg}", flush=True)

def telegram(msg):
    try:
        from urllib.request import urlopen, Request
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = json.dumps({"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "html"}).encode()
        req = Request(url, data=data, headers={"Content-Type": "application/json"})
        urlopen(req, timeout=10)
    except Exception as e:
        log(f"Telegram error: {e}")

def load_crm():
    if not os.path.exists(CRM_FILE): return []
    with open(CRM_FILE) as f:
        return [json.loads(l) for l in f if l.strip()]

def update_lead(email, updates):
    leads = load_crm()
    for i, l in enumerate(leads):
        if l.get("email","").lower() == email.lower():
            leads[i].update(updates); break
    with open(CRM_FILE, "w") as f:
        for l in leads: f.write(json.dumps(l) + "\n")

def get_pending_approvals():
    """Get HOT leads (score 8+) awaiting approval."""
    return [l for l in load_crm()
            if l.get("needs_approval") == True
            and l.get("score", 0) >= 8.0
            and l.get("status") in ("SCORED","APPROVED")
            and not l.get("mockup_url")]

def build_approval_message(leads):
    if not leads:
        return None
    lines = [
        "🔥 <b>SMART WEBSITE — HOT LEAD APPROVAL QUEUE</b>\n",
        f"<i>{len(leads)} lead(s) awaiting your approval</i>\n",
    ]
    for i, lead in enumerate(leads[:10], 1):
        biz = lead.get("business_name","Unknown")
        trade = lead.get("trade","tradie")
        city = lead.get("city","")
        score = lead.get("score", 0)
        url = lead.get("website","no website")
        email = lead.get("email","no email")
        phone = lead.get("phone","no phone")
        rating = lead.get("rating", 0)
        reviews = lead.get("reviews_count", 0)
        headline = lead.get("headline_finding","")
        lines.append(f"<b>{i}. {biz}</b>")
        lines.append(f"   {trade.title()} | {city} | Score: {score}/10")
        if rating: lines.append(f"   Google: {rating}★ ({reviews} reviews)")
        lines.append(f"   📎 {url[:60]}")
        if email and email != "no email": lines.append(f"   ✉️ {email}")
        if phone and phone != "no phone": lines.append(f"   📱 {phone}")
        if headline: lines.append(f"   ⚠️ {headline}")
        lines.append(" ")
    lines.append("Replies to this message are monitored.")
    lines.append("Reply with the number to approve (e.g. <code>1</code> to approve lead #1)")
    return "\n".join(lines)

def save_queue_state(leads, message_id=None):
    state = {
        "pending": [l.get("email") for l in leads if not l.get("approved")],
        "message_id": message_id,
        "updated_at": datetime.now().isoformat(),
    }
    with open(QUEUE_FILE, "w") as f:
        json.dump(state, f, indent=2)

def handle_reply(text):
    """Handle Brent's reply to the approval message."""
    text = text.strip().lower()
    # Match "1", "approve 1", "yes 1", "a1" etc.
    m = re.search(r"(\d+)", text)
    if not m:
        if "skip" in text or "next" in text:
            return "SKIP"
        return None
    idx = int(m.group(1)) - 1
    leads = get_pending_approvals()
    if idx < 0 or idx >= len(leads):
        return "INVALID_INDEX"
    lead = leads[idx]
    email = lead.get("email","")
    biz = lead.get("business_name","")
    # Approve it
    update_lead(email, {
        "status": "APPROVED",
        "approved_at": datetime.now().isoformat(),
        "needs_approval": False,
        "approved_by": "brent",
    })
    log(f"APPROVED by Brent: {biz}")
    telegram(f"✅ Approved: {biz}\n\nMason is now building the mockup. You'll get the link shortly.")
    return "APPROVED"

def run():
    log("Approval queue check starting")
    leads = get_pending_approvals()
    if not leads:
        log("No pending approvals"); return
    log(f"Pending approvals: {len(leads)}")
    msg = build_approval_message(leads)
    if msg:
        telegram(msg)
        save_queue_state(leads)
        log(f"Sent approval queue to Brent ({len(leads)} leads)")
    else:
        log("No message to send")

if __name__ == "__main__":
    run()