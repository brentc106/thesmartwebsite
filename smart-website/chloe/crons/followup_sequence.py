#!/usr/bin/env python3
"""
followup_sequence.py — Chloe's Days 5/10 SMS follow-up + deal closer
Handles the SMS follow-up sequence (Days 5 and 10) that Instantly doesn't manage.
Also fires the final "pattern interrupt" email if no reply after Day 10.

Cron: 10 AM daily
Input: leads with status=CONTACTED, no positive reply after initial outreach
Output: SMS2 at Day 5, SMS3 at Day 10, status updated
"""
import os, json, time, re, urllib.request
from datetime import datetime, timedelta

MOBILE_MESSAGE_API_KEY = os.environ.get("MOBILE_MESSAGE_API_KEY", "l8HNoED2ct0mEQUmYgbD3tF61uJml7WyAmdBvOn3dWq")
MOBILE_MESSAGE_USERNAME = os.environ.get("MOBILE_MESSAGE_USERNAME", "OF5fzx")
MOBILE_MESSAGE_SENDER = os.environ.get("MOBILE_MESSAGE_SENDER", "61485900155")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
TELEGRAM_BOT_TOKEN = "8685067366:AAHQht4DvrqFkM99rwMfhExdrkY8nks78Iw"
TELEGRAM_CHAT_ID = "7356494332"
CRM_FILE = "/Users/brentext/.openclaw/workspace/smart-website/data/leads.jsonl"

SMS_STEP_2 = "Hey {first_name}, did you get a chance to look at the mockup? No pressure — but I think you'd be surprised by what's possible for {business_name}. Happy to send it again 👍"
SMS_STEP_3 = "Hey {first_name}, real talk — should I send that mockup or leave it? Takes 2 min to look at. Either way, no hard feelings 👍"

EMAIL_FINAL = """Hey {first_name},

I've been thinking about your {trade} business and how your website could be doing more for you.

Here's what I see a lot: businesses spend thousands on a website that doesn't convert visitors into enquiries. Meanwhile, their competitors with better-looking sites are getting the calls.

I put together a mockup specifically for {business_name}. It's not theory — it's what your site would actually look like if we rebuilt it today.

{if price_mention}

Either way — just reply and I'll send the link. No obligation.

{first_name}
The Smart Website Co."""

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

def format_au_phone(phone):
    if not phone: return None
    digits = re.sub(r"\D", "", str(phone))
    if digits.startswith("61"): digits = "0" + digits[2:]
    elif digits.startswith("+61"): digits = "0" + digits[3:]
    if not digits.startswith("0") or len(digits) < 10: return None
    return digits

def send_sms(phone, message, api_key, username):
    if not api_key or not username or not phone: return False
    try:
        import urllib.request, json, base64
        to_number = phone
        if to_number.startswith("0"): to_number = "+61" + to_number[1:]
        url = "https://api.mobilemessage.com.au/v1/messages"
        payload = json.dumps({
            "messages": [{"to": to_number, "message": message, "sender": MOBILE_MESSAGE_SENDER}]
        }).encode()
        creds = base64.b64encode(f"{username}:{api_key}".encode()).decode()
        req = urllib.request.Request(url, data=payload, method="POST", headers={
            "Content-Type": "application/json",
            "Authorization": f"Basic {creds}"
        })
        with urllib.request.urlopen(req, timeout=15) as r:
            resp = json.loads(r.read())
            if resp.get("status") == "complete" and resp.get("results"):
                return resp["results"][0].get("status") == "success"
            return False
    except Exception as e:
        log(f"SMS error: {e}"); return False

def get_day5_leads():
    """Leads that had first SMS 5 days ago and haven't replied."""
    cutoff = (datetime.now() - timedelta(days=5)).isoformat()
    return [l for l in load_crm()
            if l.get("status") in ("OUTREACH_SENT","CONTACTED")
            and l.get("sms_sent")
            and l.get("sms_sent_at","") < cutoff
            and not l.get("sms_step2_sent")
            and l.get("last_intent","") != "POSITIVE"]

def get_day10_leads():
    """Leads that had SMS2 5 days ago and haven't replied."""
    cutoff = (datetime.now() - timedelta(days=10)).isoformat()
    return [l for l in load_crm()
            if l.get("status") in ("OUTREACH_SENT","CONTACTED")
            and l.get("sms_step2_sent_at","") < cutoff
            and not l.get("sms_step3_sent")
            and l.get("last_intent","") != "POSITIVE"]

def get_day10_no_reply_email_leads():
    """Day 10 leads without any positive signal — fire pattern interrupt email."""
    cutoff = (datetime.now() - timedelta(days=10)).isoformat()
    return [l for l in load_crm()
            if l.get("status") in ("OUTREACH_SENT","CONTACTED")
            and l.get("outreach_sent_at","") < cutoff
            and not l.get("final_email_sent")
            and l.get("last_intent","") not in ("POSITIVE","OPT_OUT")]

def send_email(to, subject, body):
    try:
        import smtplib
        from email.mime.text import MIMEText
        msg = MIMEText(body, "plain", "utf-8")
        msg["From"] = "Chloe <hello@thesmartwebsite.co>"
        msg["To"] = to; msg["Subject"] = subject; msg["Reply-To"] = "hello@thesmartwebsite.co"
        with smtplib.SMTP("smtp.gmail.com", 587) as s:
            s.starttls()
            s.login("hello@thesmartwebsite.co", "oaaapqzzvbcfikji")
            s.sendmail("hello@thesmartwebsite.co", [to], msg.as_string())
        return True
    except Exception as e:
        log(f"Email error: {e}"); return False

def run():
    log("Followup sequence starting")
    if not MOBILE_MESSAGE_API_KEY:
        log("WARNING: MOBILE_MESSAGE_API_KEY not set"); return

    # Day 5 SMS
    day5 = get_day5_leads()
    log(f"Day 5 SMS: {len(day5)} leads")
    for lead in day5:
        phone = format_au_phone(lead.get("phone",""))
        if not phone: continue
        first = lead.get("first_name","there")
        biz = lead.get("business_name","")
        msg = SMS_STEP_2.format(first_name=first, business_name=biz)
        if send_sms(phone, msg, MOBILE_MESSAGE_API_KEY, MOBILE_MESSAGE_USERNAME):
            update_lead(lead.get("email",""), {
                "sms_step2_sent": True,
                "sms_step2_sent_at": datetime.now().isoformat(),
            })
            log(f"Day5 SMS sent to {biz[:30]}")
        time.sleep(1.5)

    # Day 10 SMS + email
    day10 = get_day10_leads()
    log(f"Day 10 SMS: {len(day10)} leads")
    for lead in day10:
        phone = format_au_phone(lead.get("phone",""))
        if not phone: continue
        first = lead.get("first_name","there")
        biz = lead.get("business_name","")
        msg = SMS_STEP_3.format(first_name=first, business_name=biz)
        if send_sms(phone, msg, MOBILE_MESSAGE_API_KEY, MOBILE_MESSAGE_USERNAME):
            update_lead(lead.get("email",""), {
                "sms_step3_sent": True,
                "sms_step3_sent_at": datetime.now().isoformat(),
            })
            log(f"Day10 SMS sent to {biz[:30]}")
        time.sleep(1.5)

    # Day 10 pattern interrupt email
    day10_email = get_day10_no_reply_email_leads()
    log(f"Day 10 email: {len(day10_email)} leads")
    for lead in day10_email:
        first = lead.get("first_name","there")
        biz = lead.get("business_name","")
        trade = lead.get("trade","tradie")
        email = lead.get("email","")
        body = EMAIL_FINAL.format(
            first_name=first, business_name=biz,
            trade=trade, price_mention="Starter: $497 + $99/mo.")
        if send_email(email, f"Re: Quick question — {biz}", body):
            update_lead(email, {"final_email_sent": True, "final_email_sent_at": datetime.now().isoformat()})
            log(f"Final email sent to {biz[:30]}")
        time.sleep(1)

    log("Followup sequence complete")

if __name__ == "__main__":
    run()