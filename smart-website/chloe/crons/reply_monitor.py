#!/usr/bin/env python3
"""
reply_monitor.py — Chloe reply classifier + auto-responder
INBOUND: reads from Mailgun webhook queue (inbound_emails.jsonl)
OUTBOUND: sends via Mailgun API (no Google OAuth dependency)
"""
import os, smtplib, re, json, time
from datetime import datetime
from email.mime.text import MIMEText

OUTBOUND_EMAIL = "hello@thesmartwebsite.co"
FROM_NAME = "The Smart Website Co."
TELEGRAM_BOT_TOKEN = "8685067366:AAHQht4DvrqFkM99rwMfhExdrkY8nks78Iw"
TELEGRAM_CHAT_ID = "7356494332"
INBOUND_QUEUE = "/Users/brentext/.openclaw/workspace/smart-website/data/inbound_emails.jsonl"
CRM_FILE = "/Users/brentext/.openclaw/workspace/smart-website/data/leads.jsonl"

# ── Mailgun env ──────────────────────────────────────────────────────────────
def load_mailgun():
    env = {}
    for line in open(os.path.expanduser("~/.openclaw/workspace/.mailgun.env")):
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env

# ── Outbound via Mailgun ───────────────────────────────────────────────────────
def send_mailgun(to_email, subject, html_body, text_body=""):
    env = load_mailgun()
    api_key = env.get("MAILGUN_API_KEY")
    domain = env.get("MAILGUN_DOMAIN")
    if not api_key or not domain:
        log(f"Mailgun credentials missing — cannot send to {to_email}")
        return None

    from_addr = f"{FROM_NAME} <{OUTBOUND_EMAIL}>"
    data = json.dumps({
        "from": from_addr,
        "to": [to_email],
        "subject": subject,
        "html": html_body,
        "text": text_body or re.sub(r"<[^>]+>", "", html_body),
    }).encode()

    import urllib.request
    auth = (f"api:{api_key}").encode()
    import base64
    req = urllib.request.Request(
        f"https://api.mailgun.net/v3/{domain}/messages",
        data=data,
        headers={"Authorization": f"Basic {base64.b64encode(auth).decode()}"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read()).get("id", "")

# ── Templates ───────────────────────────────────────────────────────────────────
TEMPLATES = {
    "positive_ack": (
        "Hey {first_name},\n\nGot your reply — on it.\n"
        "Mason's building your mockup now.\n"
        "Your audit: {audit_url}\n\nReply with any changes before we build.\n\n{first_name}"
    ),
    "objection_cost": (
        "Hey {first_name},\n\nPricing is simple:\n\n"
        "Starter $497 + $99/mo\n"
        "Growth $797 + $197/mo\n"
        "Premium $1,497 + $397/mo\n\n"
        "Happy to send mockup first — no commitment.\n\n{first_name}"
    ),
    "objection_existing": (
        "Hey {first_name},\n\nI checked your site when I ran the audit.\n\n"
        "Main finding: {headline}\n\n"
        "Happy to show you exactly what we'd fix. Free mockup, no obligation.\n\n{first_name}"
    ),
    "objection_not_interested": (
        "No worries.\n\nAudit stays live at {audit_url}\n\nGood luck with the {trade}\n\n"
        "— The Smart Website Co."
    ),
    "objection_examples": (
        "Hey {first_name},\n\nRecent builds:\n{build1}\n{build2}\n{build3}\n\n"
        "Happy to add {business} to the list. Just reply.\n\n{first_name}"
    ),
    "objection_guarantee": (
        "Hey {first_name},\n\n14-day delivery guarantee or full refund.\n\n"
        "We build the mockup first so you see exactly what you're getting.\n\n{first_name}"
    ),
    "ooo_auto": (
        "Hey {first_name},\n\nGot your message — out of office til Monday. Back then.\n\n{first_name}"
    ),
    "opt_out": (
        "Removed from list. Good luck with {trade}\n\n— The Smart Website Co."
    ),
}

BUILDS = [
    "Fitness Centre — Gold Coast, QLD",
    "Electrical — Newcastle, NSW",
    "Cafe — Melbourne, VIC",
]

# ── Helpers ────────────────────────────────────────────────────────────────────────
def ts(): return datetime.now().strftime("%H:%M")
def log(msg): print(f"[{ts()}] {msg}", flush=True)

def telegram(msg):
    try:
        from urllib.request import urlopen, Request
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = json.dumps({"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "html"}).encode()
        req = Request(url, data=payload, headers={"Content-Type": "application/json"})
        urlopen(req, timeout=10)
    except Exception as e:
        log(f"Telegram error: {e}")

def load_crm():
    if not os.path.exists(CRM_FILE): return []
    with open(CRM_FILE) as f:
        return [json.loads(l) for l in f if l.strip()]

def save_lead(lead):
    leads = load_crm()
    for i, l in enumerate(leads):
        if l.get("email","").lower() == lead.get("email","").lower():
            leads[i].update(lead); break
    else:
        leads.append(lead)
    with open(CRM_FILE, "w") as f:
        for l in leads: f.write(json.dumps(l) + "\n")

def get_lead(email):
    for l in load_crm():
        if l.get("email","").lower() == email.lower(): return l
    return None

def classify(subject, body):
    text = (subject + " " + body).lower()
    pos = ["yes","send it","interested","sounds good","let's do","booked","love it","amazing","let's go","do it","count me in","build it","get started","i want","take a look"]
    neg = ["stop","unsubscribe","remove me","don't contact","opt out","take me off"]
    ooo = ["out of office","back on","away til","return date","in the office"]
    cost_kw = ["how much","cost","price","expensive","warrant","overpriced","too much","budget"]
    exist_kw = ["already have a website","already have site","already have one"]
    if any(k in text for k in pos): return "POSITIVE"
    if any(k in text for k in neg): return "OPT_OUT"
    if any(k in text for k in ooo): return "OOO"
    if any(k in text for k in cost_kw): return "OBJECTION_COST"
    if any(k in text for k in exist_kw): return "OBJECTION_EXISTING"
    return "OBJECTION_NOT_INTERESTED"

def send_reply(to_email, subject, body_text, lead, intent):
    """Send reply via Mailgun API — no Google OAuth needed."""
    biz = lead.get("business_name", "")
    first = lead.get("first_name", biz.split()[0] if biz else "there")
    trade = lead.get("trade", "your business")
    audit_url = lead.get("audit_url", "https://thesmartwebsite.co")
    headline = lead.get("headline_finding", "see audit")

    tpl = TEMPLATES.get(intent, TEMPLATES["objection_not_interested"])
    body_text = tpl.format(
        first_name=first, trade=trade, headline=headline,
        business=biz, audit_url=audit_url,
        build1=BUILDS[0], build2=BUILDS[1], build3=BUILDS[2]
    )
    html = f"<pre style='font-family:sans-serif'>{body_text}</pre>"
    msg_id = send_mailgun(to_email, f"Re: {subject}" if subject else "Re: your website audit", html, body_text)
    log(f"Sent {intent} reply to {to_email} — msg_id: {msg_id}")
    return msg_id

def route_reply(from_email, subject, body, lead):
    biz = lead.get("business_name", "")
    first = lead.get("first_name", biz.split()[0] if biz else "there")
    trade = lead.get("trade", "tradie")
    audit_url = lead.get("audit_url", "https://thesmartwebsite.co")
    headline = lead.get("headline_finding", "see audit")
    intent = classify(subject, body)

    if intent == "POSITIVE":
        save_lead({"email": from_email, "status": "INTERESTED"})
        telegram(f"✅ POSITIVE: {biz} ({from_email}) — mockup incoming")
        send_reply(from_email, subject, "", lead, "positive_ack")
    elif intent.startswith("OBJECTION"):
        save_lead({"email": from_email, "last_intent": intent})
        send_reply(from_email, subject, "", lead, intent)
    elif intent == "OPT_OUT":
        save_lead({"email": from_email, "status": "OPT_OUT"})
        send_reply(from_email, subject, "", lead, "opt_out")
    elif intent == "OOO":
        save_lead({"email": from_email, "ooo": True})
        send_reply(from_email, subject, "", lead, "ooo_auto")

    log(f"{biz[:30]} intent={intent}")

def run():
    log("Reply monitor starting — reading Mailgun inbound queue")
    if not os.path.exists(INBOUND_QUEUE):
        log(f"Inbound queue not found at {INBOUND_QUEUE} — waiting for Mailgun webhook")
        return

    new_events = []
    with open(INBOUND_QUEUE) as f:
        lines = f.readlines()

    if not lines:
        log("No new inbound emails")
        return

    log(f"Processing {len(lines)} inbound email(s)")
    for line in lines:
        try:
            event = json.loads(line)
            if event.get("processed"):
                continue

            from_email = event.get("from", "")
            subject = event.get("subject", "")
            body = event.get("body", "")
            to_email = event.get("to", "")

            # Extract plain email address
            m = re.search(r"<(.+?)>", from_email)
            from_email = m.group(1) if m else from_email.strip()
            if not from_email or from_email == "unknown":
                continue

            log(f"Inbound: {from_email[:40]} | {subject[:60]}")

            lead = get_lead(from_email)
            if not lead:
                log(f"Unknown sender: {from_email[:50]} — skipping")
                event["processed"] = True
                new_events.append(event)
                continue

            route_reply(from_email, subject, body, lead)
            event["processed"] = True

        except Exception as e:
            log(f"Error processing event: {e}")
            try:
                event = json.loads(line)
                event["error"] = str(e)
                event["processed"] = True
            except:
                pass
        finally:
            try:
                new_events.append(event)
            except:
                pass

    # Rewrite queue keeping unprocessed
    with open(INBOUND_QUEUE, "w") as f:
        for event in new_events:
            if not event.get("processed"):
                f.write(json.dumps(event) + "\n")

    log("Done")

if __name__ == "__main__":
    run()
