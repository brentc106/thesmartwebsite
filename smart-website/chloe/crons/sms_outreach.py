#!/usr/bin/env python3
"""
sms_outreach.py — Chloe's Mobile Message SMS sender
Fires SMS to hot leads (score 8+) after email sent, using AU Numbers.

CRON: 9:30 AM daily (30 min after email_outreach)
Input: leads with status=OUTREACH_SENT, no sms_sent
Output: SMS sent via Mobile Message API, status updated

API confirmed working 2026-05-10:
  - Auth: Basic auth (username, api_key)
  - Endpoint: POST /v1/messages with body {"messages": [{"to": "+61...", "message": "...", "sender": "614..."}]}
  - Sender IDs: 61485900155 (shared), 61421332071 (own)
  - Cost: 1 credit per SMS
  - Balance: 50 credits remaining
"""
import os, json, time, re, urllib.request
from datetime import datetime

MOBILE_MESSAGE_API_KEY = os.environ.get("MOBILE_MESSAGE_API_KEY", "l8HNoED2ct0mEQUmYgbD3tF61uJml7WyAmdBvOn3dWq")
MOBILE_MESSAGE_USERNAME = os.environ.get("MOBILE_MESSAGE_USERNAME", "OF5fzx")
# Default sender: shared number (61485900155) — can switch to own number 61421332071
MOBILE_MESSAGE_SENDER = os.environ.get("MOBILE_MESSAGE_SENDER", "61485900155")
TELEGRAM_BOT_TOKEN = "8685067366:AAHQht4DvrqFkM99rwMfhExdrkY8nks78Iw"
TELEGRAM_CHAT_ID = "7356494332"
CRM_FILE = "/Users/brentext/.openclaw/workspace/smart-website/data/leads.jsonl"

SMS_SEQUENCE = [
    # SMS 1: Day 0 — same morning as email
    {
        "body": "Hey {first_name}, this is Chloe from The Smart Website Co. — sent you an email about your website. Take a look when you get a sec 👍",
        "delay_hours": 0,
    },
    # SMS 2: Day 3 — follow up
    {
        "body": "Hey {first_name}, just following up — did you get a chance to look at the mockup? Happy to send the link again if helpful 👍",
        "delay_days": 3,
    },
    # SMS 3: Day 10 — pattern interrupt
    {
        "body": "Hey {first_name}, quick question — should I send that mockup through or leave it? Takes 2 min to look at 👍",
        "delay_days": 10,
    },
]

def ts(): return datetime.now().strftime("%H:%M")
def log(msg): print(f"[{ts()}] {msg}", flush=True)

def telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = json.dumps({"chat_id": TELEGRAM_CHAT_ID, "text": msg}).encode()
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=10)
    except: pass

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

def get_sms_pending():
    return [l for l in load_crm()
            if l.get("status") == "OUTREACH_SENT"
            and not l.get("sms_sent")]

def format_au_phone(phone):
    if not phone: return None
    digits = re.sub(r"\D", "", str(phone))
    if digits.startswith("61"): digits = "0" + digits[2:]
    elif digits.startswith("+61"): digits = "0" + digits[3:]
    elif len(digits) == 9 and digits.startswith("4"): digits = "0" + digits
    if not digits.startswith("0") or len(digits) < 10: return None
    return digits

def send_sms(phone, message_text, api_key, username):
    """Send SMS via Mobile Message v1 API."""
    if not api_key or not username: return False
    if not phone: return False
    try:
        import urllib.request, json
        # Format phone: must start with +61 for API
        to_number = phone
        if to_number.startswith("0"): to_number = "+61" + to_number[1:]
        url = "https://api.mobilemessage.com.au/v1/messages"
        payload = json.dumps({
            "messages": [{
                "to": to_number,
                "message": message_text,
                "sender": MOBILE_MESSAGE_SENDER
            }]
        }).encode()
        
        # Basic auth: username:api_key
        import base64
        creds = base64.b64encode(f"{username}:{api_key}".encode()).decode()
        
        req = urllib.request.Request(url, data=payload, method="POST", headers={
            "Content-Type": "application/json",
            "Authorization": f"Basic {creds}"
        })
        with urllib.request.urlopen(req, timeout=15) as r:
            resp = json.loads(r.read())
            if resp.get("status") == "complete" and resp.get("results"):
                result = resp["results"][0]
                return result.get("status") == "success"
            return False
    except Exception as e:
        log(f"SMS error: {e}")
        return False

def run():
    log("SMS outreach starting")
    if not MOBILE_MESSAGE_API_KEY:
        log("WARNING: MOBILE_MESSAGE_API_KEY not set"); return

    leads = get_sms_pending()
    log(f"Sending SMS to {len(leads)} leads")
    sent = 0
    for lead in leads:
        phone = format_au_phone(lead.get("phone",""))
        if not phone:
            log(f"No valid AU phone for {lead.get('email','?')}")
            update_lead(lead.get("email",""), {"sms_sent": False, "sms_error": "no_phone"})
            continue
        first = lead.get("first_name","there")
        biz = lead.get("business_name","")
        msg = SMS_SEQUENCE[0]["body"].format(first_name=first, business_name=biz)
        success = send_sms(phone, msg, MOBILE_MESSAGE_API_KEY, MOBILE_MESSAGE_USERNAME)
        if success:
            update_lead(lead.get("email",""), {
                "sms_sent": True,
                "sms_sent_at": datetime.now().isoformat(),
                "sms_phone": phone,
            })
            sent += 1
            log(f"SMS sent to {phone[:8]}...")
        else:
            update_lead(lead.get("email",""), {"sms_sent": False, "sms_error": "api_error"})
        time.sleep(1.5)  # rate limit
    log(f"Done — {sent} SMS sent")
    if sent > 0:
        telegram(f"SMS outreach: {sent} messages sent")

if __name__ == "__main__":
    run()