#!/usr/bin/env python3
"""
email_outreach.py — Chloe's Instantly.ai email campaign pusher
Pulls approved leads from CRM, creates Instantly campaign, adds leads, fires.

CRON: 9 AM daily
Input: leads with status=APPROVED (score 7+) and audit_url ready
Output: Instantly campaign created + leads added, status=OUTREACH_SENT

API: Instantly v2 — confirmed working:
  - Auth: Bearer <base64(api_key:api_secret)>
  - Create: POST /api/v2/campaigns
  - Add leads: POST /api/v2/leads/add (with campaign_id)
  - Launch: PATCH /api/v2/campaigns/{id} status=1 (trial may block — check)
  - Timezone: Australia/Melbourne for AEST
  - Schedule format: campaign_schedule.schedules[0] with timing + days
"""
import os, json, time, urllib.request
from datetime import datetime

INSTANTLY_API_KEY = os.environ.get("INSTANTLY_API_KEY", "")
# base64(api_key:api_secret) — used as Bearer token
INSTANTLY_AUTH = os.environ.get("INSTANTLY_AUTH", "OWVmZTY1ZTEtNGM3My00ZmRkLTg5YTAtNjQ3OTNlMzUyOTRiOnJyTHdqa25tTnRFTw==")
INSTANTLY_BASE_URL = "https://api.instantly.ai/api/v2"
TELEGRAM_BOT_TOKEN = "8685067366:AAHQht4DvrqFkM99rwMfhExdrkY8nks78Iw"
TELEGRAM_CHAT_ID = "7356494332"
CRM_FILE = "/Users/brentext/.openclaw/workspace/smart-website/data/leads.jsonl"
STRIPE_LINKS = {
    "starter": "https://buy.stripe.com/9B69AT8CKa977ZRbYTgbm00",
    "growth": "https://buy.stripe.com/9B66oH4mu80Zbc3d2Xgbm01",
    "premium": "https://buy.stripe.com/5kQ9ATcT080ZfsjaUPgbm02",
    "trial": "https://buy.stripe.com/fZu28rdX45SR4NFgf9gbm03",
}
SENDER_EMAIL = "hello@thesmartwebsite.co"
SENDER_NAME = "Chloe / The Smart Website Co."

SEQUENCE = [
    {
        "step": 1,
        "subject": "Quick question — {business_name}",
        "body": """Hey {first_name},

I came across {business_name} and had a quick look at your site.

Honestly — it's probably costing you leads. Most business websites in {trade} aren't set up to actually convert visitors into enquiries.

I put together a mockup showing what your homepage could look like if it was built to bring in more business.

Happy to send it through? No obligation — just wanted to show you.

{first_name}""",
    },
    {
        "step": 2,
        "subject": "Re: Quick question — {business_name}",
        "delay_days": 3,
        "body": """Hey {first_name},

Just wanted to follow up on this — I actually built a version of your homepage that looks significantly better and is built to convert.

It takes 2 min to look at and you'll immediately see what's possible.

Still happy to send it through?

{first_name}""",
    },
    {
        "step": 3,
        "subject": "Re: Quick question — {business_name}",
        "delay_days": 7,
        "body": """Hey {first_name},

Quick one — should I send the mockup through or leave it?

No stress either way. Just figured it'd be worth 2 min of your time to see what's possible.

{first_name}""",
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

def get_ready_leads():
    return [l for l in load_crm()
            if l.get("status") == "APPROVED"
            and l.get("email")
            and l.get("audit_url")]

def instantly_request(method, path, body=None):
    """Make Instantly v2 API request."""
    auth = INSTANTLY_AUTH or INSTANTLY_API_KEY
    if not auth: return None
    try:
        url = f"{INSTANTLY_BASE_URL}{path}"
        payload = json.dumps(body).encode() if body else None
        req = urllib.request.Request(url, data=payload, method=method, headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth}",
        })
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read()) if r.status not in (204,) else {}
    except Exception as e:
        log(f"Instantly API error on {method} {path}: {e}")
        return None

def create_campaign(lead):
    """Create 3-step email sequence campaign."""
    biz = lead.get("business_name","")
    first = lead.get("first_name","there")
    trade = lead.get("trade","your industry")
    subject = f"Quick question — {biz}"
    body = SEQUENCE[0]["body"].format(business_name=biz, first_name=first, trade=trade)
    # Instantly v2: requires campaign_schedule with schedules
    data = instantly_request("POST", "/campaigns", {
        "name": f"Outreach — {biz}",
        "subject": subject,
        "body": body,
        "campaign_schedule": {
            "type": "scheduled",
            "schedules": [{
                "name": "Weekday mornings",
                "timezone": "Australia/Melbourne",
                "timing": {
                    "timeZone": "Australia/Melbourne",
                    "hour": 9,
                    "minute": 0,
                    "from": "09:00",
                    "to": "17:00"
                },
                "days": {"type": "weekly", "days": [1, 2, 3, 4, 5]}
            }]
        }
    })
    if not data or "id" not in data:
        log(f"Failed to create campaign for {biz}: {data}")
        return None
    campaign_id = data.get("id")
    log(f"Campaign created: {campaign_id}")
    return campaign_id

def add_leads_to_campaign(campaign_id, lead):
    """Add lead to Instantly campaign."""
    first = lead.get("first_name","")
    last = lead.get("last_name","")
    email = lead.get("email","")
    phone = lead.get("phone","")
    biz = lead.get("business_name","")
    url = lead.get("website","")
    result = instantly_request("POST", "/leads/add", {
        "campaign_id": campaign_id,
        "leads": [{
            "email": email,
            "first_name": first,
            "last_name": last,
            "company_name": biz,
            "phone": phone,
            "website": url,
        }]
    })
    return result

def launch_campaign(campaign_id):
    """Set campaign status=1 (active/sending)."""
    # Note: trial accounts may get 500 on activation — Instantly may require paid plan
    result = instantly_request("PATCH", f"/campaigns/{campaign_id}", {"status": 1})
    return result

def run():
    log("Email outreach starting")
    if not INSTANTLY_AUTH:
        log("ERROR: INSTANTLY_AUTH not set"); return

    leads = get_ready_leads()
    log(f"Processing {len(leads)} leads")
    sent = 0
    for lead in leads:
        email = lead.get("email","")
        biz = lead.get("business_name","")
        log(f"Creating campaign for: {biz[:40]}")
        cid = create_campaign(lead)
        if not cid:
            log(f"Failed: {email}")
            continue
        add_result = add_leads_to_campaign(cid, lead)
        log(f"Leads added: {add_result}")
        launched = launch_campaign(cid)
        if launched:
            log(f"Campaign launched: {cid}")
        else:
            log(f"Campaign created (not launched - may need paid plan): {cid}")
        update_lead(email, {
            "status": "OUTREACH_SENT",
            "campaign_id": cid,
            "outreach_sent_at": datetime.now().isoformat(),
        })
        sent += 1
        time.sleep(1)
    log(f"Done — {sent} campaigns created")
    telegram(f"Email outreach: {sent} campaigns created (check Instantly dashboard to activate if on trial)")

if __name__ == "__main__":
    run()