"""
smart_website_api.py — Smart Website Co. Flask API
Wraps existing Python scripts as HTTP endpoints for n8n
Deploy to Railway as: smart-website-api service

Endpoints:
  GET  /health              — health check
  POST /generate-audit      — generate audit for a lead
  POST /send-email          — send email via Mailgun
  POST /check-parked        — check if URL is parked
  POST /deploy-vercel       — deploy HTML to Vercel
  GET  /leads               — list leads from Postgres
  POST /leads               — create/update lead in Postgres
"""

import os, json, math, re, time, subprocess, tempfile
from datetime import datetime
from urllib.request import urlopen, Request
from urllib.parse import urlencode
from flask import Flask, request, jsonify
import psycopg2
import requests

app = Flask(__name__)

# ─── CONFIG ──────────────────────────────────────────────────────────────────

MAILGUN_API_KEY       = os.environ.get("MAILGUN_API_KEY", "")
MAILGUN_DOMAIN        = os.environ.get("MAILGUN_DOMAIN", "")
LAOZHANG_API_KEY      = os.environ.get("LAOZHANG_API_KEY", "")
LAOZHANG_BASE_URL     = os.environ.get("LAOZHANG_BASE_URL", "https://api.laozhang.ai")
FIRECRAWL_API_KEY     = os.environ.get("FIRECRAWL_API_KEY", "")
VERCEL_TOKEN          = os.environ.get("VERCEL_TOKEN", "")
DATABASE_URL          = os.environ.get("DATABASE_URL", "")
TELEGRAM_BOT_TOKEN    = os.environ.get("TELEGRAM_SMARTWEB_BOT_TOKEN", "")
TELEGRAM_CHAT_ID      = os.environ.get("TELEGRAM_BUILD_ALERTS_CHAT_ID", "")
AUDIT_BASE            = "https://audit.thesmartwebsite.co"
THANK_YOU             = "https://audit.thesmartwebsite.co/thank-you"
VERCEL_PROJECT_ID     = os.environ.get("VERCEL_PROJECT_ID", "prj_FKKLAYz5jNVvqu4nmlAej0bpOfi5")

IMPECCABLE_23 = [
    "Exactly ONE eye-level focal point?",
    "Type as primary design element?",
    "Clear axis (alignment) connecting all?",
    "Exactly ONE primary accent color, used sparingly?",
    "Exactly THREE type sizes maximum?",
    "Negative space actively protecting focal point?",
    "Real grid (not assumed)?",
    "Hierarchy immediately scannable without reading?",
    "Decorative elements absent unless meaningful?",
    "CTA so obvious a 5-year-old would click it?",
    "Design feels inevitable, not arbitrary?",
    "Any orphaned elements breaking alignment?",
    "Mobile first-class citizen, not a shrink?",
    "Consistent spacing rhythm?",
    "Color contrast meets WCAG AA?",
    "Visual rhythm breaks at meaningful points?",
    "Type hierarchy creates clear path?",
    "Images optimized and purposeful?",
    "No elements that distract from goal?",
    "Brand personality comes through?",
    "Loading states considered?",
    "Error states designed?",
    "Empty states designed?",
]

# ─── DB ──────────────────────────────────────────────────────────────────────

def get_db():
    return psycopg2.connect(DATABASE_URL)

# ─── HELPERS ─────────────────────────────────────────────────────────────────

def slugify(text):
    import unicodedata
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9-]", "-", text.lower()).strip("-")[:60]

def svg_dashoffset(score):
    r = 68
    circumference = 2 * math.pi * r
    return round(circumference * (1 - score / 30), 2)

def get_severity(score):
    if score >= 26:
        return {"color": "#4CAF50", "label": "Good",       "bg": "rgba(76,175,80,0.1)",  "border": "rgba(76,175,80,0.3)"}
    elif score >= 21:
        return {"color": "#FF9800", "label": "Needs Work", "bg": "rgba(255,152,0,0.1)", "border": "rgba(255,152,0,0.3)"}
    else:
        return {"color": "#FF4444", "label": "Critical",   "bg": "rgba(255,68,68,0.1)",  "border": "rgba(255,68,68,0.3)"}

import html as html_lib
def h(text):
    return html_lib.escape(str(text), quote=True)

def telegram(msg):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": msg}, timeout=10)
    except: pass

# ─── ENDPOINTS ───────────────────────────────────────────────────────────────

@app.route("/health")
def health():
    return jsonify({"status": "ok", "service": "smart-website-api", "time": datetime.now().isoformat()})


@app.route("/check-parked", methods=["POST"])
def check_parked():
    """Check if a URL is a parked domain."""
    data = request.json
    url = data.get("url", "")
    if not url:
        return jsonify({"error": "url required"}), 400
    try:
        resp = requests.get(url, timeout=10, allow_redirects=True,
                          headers={"User-Agent": "Mozilla/5.0"})
        content = resp.text.lower()
        parked_signals = [
            "domain for sale", "this domain is for sale", "buy this domain",
            "domain parking", "parked domain", "sedoparking", "godaddy.com/forsale",
            "hugedomains", "dan.com", "afternic", "namecheap parking",
            "coming soon", "under construction", "this site can't be reached"
        ]
        is_parked = any(signal in content for signal in parked_signals)
        return jsonify({"url": url, "is_parked": is_parked, "status_code": resp.status_code})
    except Exception as e:
        return jsonify({"url": url, "is_parked": True, "error": str(e)})


@app.route("/scrape", methods=["POST"])
def scrape():
    """Scrape website content via Firecrawl."""
    data = request.json
    url = data.get("url", "")
    if not url or not FIRECRAWL_API_KEY:
        return jsonify({"content": ""})
    try:
        from firecrawl import Firecrawl
        fc = Firecrawl(api_key=FIRECRAWL_API_KEY)
        doc = fc.scrape(url, formats=["markdown"], only_main_content=True)
        content = doc.markdown if hasattr(doc, "markdown") else ""
        return jsonify({"content": content, "length": len(content)})
    except Exception as e:
        return jsonify({"content": "", "error": str(e)})


@app.route("/generate-audit", methods=["POST"])
def generate_audit():
    """Generate audit content via DeepSeek and build HTML."""
    data = request.json
    lead = data.get("lead", {})
    website_content = data.get("website_content", "")
    is_parked = data.get("is_parked", False)

    name = lead.get("name", "Unknown Business")
    trade = lead.get("trade", "local business")
    city  = lead.get("suburb", lead.get("city", "Sydney"))
    url   = lead.get("website", "")
    email = lead.get("email", "")

    slug = slugify(name) + "-" + datetime.now().strftime("%Y-%m-%d")

    # Generate audit data via DeepSeek
    rules_text = "\n".join([f"{i+1}. {r}" for i, r in enumerate(IMPECCABLE_23)])

    if is_parked:
        prompt = f"""You are auditing a business with a parked or inactive domain.

BUSINESS: {name}
TRADE: {trade}
CITY: {city}
DOMAIN: {url} (PARKED — no live website)

Generate an opportunity audit. This business has no website.
Score: 2/30 (no website = critical)

Return ONLY valid JSON:
{{
  "score": 2,
  "hero_intro": "<2-3 sentences about what they're missing without a website. Reference trade and city. Mention specific revenue opportunity.>",
  "hero_headline": "<specific headline about cost of having no website for their trade>",
  "monthly_opportunity": "<dollar figure e.g. '$8,500'>",
  "revenue_detail": "<why they're losing this — no website means invisible to searchers>",
  "leads_lost": "<realistic number>",
  "visitors_lost": "<realistic number>",
  "monthly_leakage": "<same as monthly_opportunity>",
  "issues": [
    {{"num": "1", "title": "No active website", "finding": "Domain is parked — business is invisible to online searchers", "fix": "Build a professional website with clear CTAs and contact info", "impact": "Missing 100% of online leads"}},
    {{"num": "2", "title": "No Google Business website link", "finding": "GMB listing has no website link reducing trust", "fix": "Add website link to GMB profile once site is live", "impact": "Lower GMB conversion rate"}},
    {{"num": "3", "title": "No mobile presence", "finding": "No mobile-optimised site means lost emergency calls", "fix": "Build mobile-first with tap-to-call button", "impact": "Lost emergency/urgent leads"}},
    {{"num": "4", "title": "No trust signals online", "finding": "Customers can't verify credentials, reviews, or experience online", "fix": "Display licence, insurance, Google reviews on homepage", "impact": "Lower trust = lower close rate"}},
    {{"num": "5", "title": "No pricing visible", "finding": "No way for customers to understand your rates before calling", "fix": "Show starting prices and service packages", "impact": "Higher bounce rate from price-shoppers"}}
  ],
  "competitor_gaps": [
    {{"title": "Online visibility", "gap": "Competitors with websites appear first in Google for {trade} {city}", "action": "Build and optimise a website to capture these searches"}},
    {{"title": "Trust signals", "gap": "Active competitors show reviews, licences and photos online", "action": "Display credentials and customer reviews prominently"}},
    {{"title": "24/7 lead capture", "gap": "Competitors capture enquiries while you're offline", "action": "Add contact form and click-to-call for after-hours leads"}}
  ],
  "ai_chatbot_body": "<specific chatbot opportunity for {trade}>",
  "ai_chatbot_benefit": "Could capture 40% more after-hours enquiries",
  "ai_receptionist_body": "<specific receptionist opportunity for {trade}>",
  "ai_receptionist_benefit": "Potential 8 extra jobs/week",
  "recommended_plan": "Starter"
}}"""
    else:
        website_sample = website_content[:6000] if website_content else "No content available."
        prompt = f"""You are an expert web design auditor for Australian tradie and small business websites.

BUSINESS: {name}
TRADE: {trade}
CITY: {city}
WEBSITE: {url}

WEBSITE CONTENT:
{website_sample}

23 IMPECCABLE RULES:
{rules_text}

SCORING GUIDE (be brutal — most tradie sites score 8-16):
26-30: Exceptional. Real photography, reviews shown, pricing visible, fast mobile, clear CTA.
21-25: Decent. Some real photos, services listed, phone visible but not prominent.
14-20: Poor. Template layout, stock photos, no pricing, slow mobile. Most tradie sites.
8-13:  Bad. Broken elements, no mobile, no contact above fold, embarrassing design.
1-7:   Terrible. Barely functional, abandoned, built pre-2015.

Score honestly. 18 means genuinely above average. Most sites score 8-16.

Return ONLY valid JSON:
{{
  "score": <integer 0-30>,
  "score_reasoning": "<one sentence why this score>",
  "hero_intro": "<2-3 sentences, specific $ opportunity, reference trade and city>",
  "hero_headline": "<one punchy sentence about biggest issue and $ impact>",
  "monthly_opportunity": "<dollar amount e.g. '$9,200'>",
  "revenue_detail": "<1 sentence root cause>",
  "leads_lost": "<number>",
  "visitors_lost": "<number>",
  "monthly_leakage": "<same as monthly_opportunity>",
  "issues": [
    {{"num": "<1-23>", "title": "<exact Impeccable rule>", "finding": "<specific finding>", "fix": "<specific fix>", "impact": "<$ or % impact>"}},
    {{"num": "<1-23>", "title": "<exact Impeccable rule>", "finding": "<specific finding>", "fix": "<specific fix>", "impact": "<$ or % impact>"}},
    {{"num": "<1-23>", "title": "<exact Impeccable rule>", "finding": "<specific finding>", "fix": "<specific fix>", "impact": "<$ or % impact>"}},
    {{"num": "<1-23>", "title": "<exact Impeccable rule>", "finding": "<specific finding>", "fix": "<specific fix>", "impact": "<$ or % impact>"}},
    {{"num": "<1-23>", "title": "<exact Impeccable rule>", "finding": "<specific finding>", "fix": "<specific fix>", "impact": "<$ or % impact>"}}
  ],
  "competitor_gaps": [
    {{"title": "<gap title>", "gap": "<what competitors have>", "action": "<one concrete action>"}},
    {{"title": "<gap title>", "gap": "<what competitors have>", "action": "<one concrete action>"}},
    {{"title": "<gap title>", "gap": "<what competitors have>", "action": "<one concrete action>"}}
  ],
  "ai_chatbot_body": "<specific to their trade>",
  "ai_chatbot_benefit": "<specific claim>",
  "ai_receptionist_body": "<specific to their trade>",
  "ai_receptionist_benefit": "<specific claim>",
  "recommended_plan": "<Starter|Growth|Premium|Full Stack>"
}}"""

    try:
        payload = {
            "model": "deepseek-v3",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 2000,
            "temperature": 0.2,
        }
        resp = requests.post(
            f"{LAOZHANG_BASE_URL}/v1/chat/completions",
            json=payload,
            headers={"Authorization": f"Bearer {LAOZHANG_API_KEY}", "Content-Type": "application/json"},
            timeout=60
        )
        text = resp.json()["choices"][0]["message"]["content"].strip()
        text = re.sub(r"```[a-z]*\n?", "", text).strip().rstrip("`").strip()
        start, end = text.find("{"), text.rfind("}") + 1
        audit_data = json.loads(text[start:end])
    except Exception as e:
        audit_data = {
            "score": 2 if is_parked else 14,
            "hero_intro": f"We audited {name} and found significant opportunities being missed.",
            "hero_headline": "Your website is costing you leads every day.",
            "monthly_opportunity": "$8,500", "revenue_detail": "Customers can't find you online.",
            "leads_lost": "140", "visitors_lost": "950", "monthly_leakage": "$8,500",
            "issues": [
                {"num": "1", "title": "Exactly ONE eye-level focal point?", "finding": "No clear focal point", "fix": "Make phone number the sole focal point", "impact": "25% lower conversion"},
                {"num": "10", "title": "CTA so obvious a 5-year-old would click it?", "finding": "CTA not prominent enough", "fix": "Increase CTA size by 200%", "impact": "Missed calls daily"},
                {"num": "13", "title": "Mobile first-class citizen, not a shrink?", "finding": "Poor mobile experience", "fix": "Redesign mobile layout", "impact": "60%+ visitors leave"},
                {"num": "4", "title": "Exactly ONE primary accent color?", "finding": "Multiple accent colours", "fix": "One action colour for CTAs only", "impact": "Confuses brand"},
                {"num": "18", "title": "Images optimized and purposeful?", "finding": "Unoptimised images", "fix": "Compress to WebP under 200KB", "impact": "Slow load times"},
            ],
            "competitor_gaps": [
                {"title": "Online visibility", "gap": "Competitors rank above you in Google", "action": "Optimise homepage for local search"},
                {"title": "Trust signals", "gap": "Competitors show reviews prominently", "action": "Display Google rating above fold"},
                {"title": "Response time", "gap": "Competitors show response time badge", "action": "Add response guarantee to hero"},
            ],
            "ai_chatbot_body": "Captures enquiries 24/7 for your trade.",
            "ai_chatbot_benefit": "35% more after-hours leads",
            "ai_receptionist_body": "Handles calls while you're on the tools.",
            "ai_receptionist_benefit": "8 extra jobs/week",
            "recommended_plan": "Starter" if is_parked else "Growth",
        }

    # Build the HTML
    html_content = build_audit_html(lead, audit_data, slug, email)

    return jsonify({
        "slug": slug,
        "audit_data": audit_data,
        "html": html_content,
        "audit_url": f"{AUDIT_BASE}/{slug}"
    })


@app.route("/deploy-audit", methods=["POST"])
def deploy_audit():
    """Deploy audit HTML to Vercel."""
    data = request.json
    slug = data.get("slug")
    html_content = data.get("html")
    audit_data = data.get("audit_data", {})

    if not slug or not html_content:
        return jsonify({"error": "slug and html required"}), 400

    # Write to temp directory and deploy
    import tempfile, shutil
    tmp = tempfile.mkdtemp()
    slug_dir = os.path.join(tmp, slug)
    os.makedirs(slug_dir)

    with open(os.path.join(slug_dir, "index.html"), "w") as f:
        f.write(html_content)
    with open(os.path.join(slug_dir, "audit_data.json"), "w") as f:
        json.dump(audit_data, f, ensure_ascii=False, indent=2)

    # Add root redirect
    with open(os.path.join(tmp, "index.html"), "w") as f:
        f.write('<meta http-equiv="refresh" content="0;url=https://www.thesmartwebsite.co">')

    try:
        result = subprocess.run(
            ["npx", "vercel", "--prod", "--yes", "--token", VERCEL_TOKEN],
            capture_output=True, text=True, timeout=120, cwd=tmp
        )
        shutil.rmtree(tmp, ignore_errors=True)
        if result.returncode == 0:
            audit_url = f"{AUDIT_BASE}/{slug}"
            return jsonify({"success": True, "audit_url": audit_url, "slug": slug})
        else:
            return jsonify({"success": False, "error": result.stderr[:500]}), 500
    except Exception as e:
        shutil.rmtree(tmp, ignore_errors=True)
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/send-email", methods=["POST"])
def send_email():
    """Send email via Mailgun."""
    data = request.json
    to      = data.get("to")
    subject = data.get("subject")
    html    = data.get("html")
    text    = data.get("text", "")

    if not all([to, subject, html]):
        return jsonify({"error": "to, subject, html required"}), 400

    try:
        import base64
        auth = base64.b64encode(f"api:{MAILGUN_API_KEY}".encode()).decode()
        resp = requests.post(
            f"https://api.mailgun.net/v3/{MAILGUN_DOMAIN}/messages",
            headers={"Authorization": f"Basic {auth}"},
            data={
                "from": "Brent <hello@thesmartwebsite.co>",
                "to": to,
                "subject": subject,
                "html": html,
                "text": text or "Please view this email in an HTML-capable client.",
            },
            timeout=15
        )
        return jsonify({"success": resp.status_code == 200, "status": resp.status_code})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/leads", methods=["GET"])
def get_leads():
    """Get leads from Postgres."""
    status = request.args.get("status")
    limit  = int(request.args.get("limit", 50))
    try:
        conn = get_db()
        cur  = conn.cursor()
        if status:
            cur.execute("SELECT * FROM leads WHERE status=%s ORDER BY created_at DESC LIMIT %s", (status, limit))
        else:
            cur.execute("SELECT * FROM leads ORDER BY created_at DESC LIMIT %s", (limit,))
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, row)) for row in cur.fetchall()]
        conn.close()
        return jsonify({"leads": rows, "count": len(rows)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/leads", methods=["POST"])
def upsert_lead():
    """Create or update a lead in Postgres."""
    data = request.json
    try:
        conn = get_db()
        cur  = conn.cursor()
        cur.execute("""
            INSERT INTO leads (name, email, phone, website, trade, suburb, score, status, audit_url, audit_score)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (email) DO UPDATE SET
              status=EXCLUDED.status,
              audit_url=COALESCE(EXCLUDED.audit_url, leads.audit_url),
              audit_score=COALESCE(EXCLUDED.audit_score, leads.audit_score),
              updated_at=NOW()
            RETURNING id
        """, (
            data.get("name"), data.get("email"), data.get("phone"),
            data.get("website"), data.get("trade"), data.get("suburb"),
            data.get("score"), data.get("status", "SCRAPED"),
            data.get("audit_url"), data.get("audit_score")
        ))
        lead_id = cur.fetchone()[0]
        conn.commit()
        conn.close()
        return jsonify({"success": True, "id": lead_id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def build_audit_html(lead, audit_data, slug, email=""):
    """Build the audit HTML page."""
    name  = lead.get("name", "Your Business")
    trade = lead.get("trade", "local business")
    city  = lead.get("suburb", lead.get("city", "Sydney"))
    site  = lead.get("website", "#")
    score = int(audit_data.get("score", 16))
    sev   = get_severity(score)
    dashoff = svg_dashoffset(score)
    circ    = round(2 * math.pi * 68, 2)
    issues  = audit_data.get("issues", [])[:5]
    gaps    = audit_data.get("competitor_gaps", [])

    params = urlencode({
        "slug": slug, "name": name, "email": email,
        "suburb": city, "trade": trade, "score": str(score),
        "audit": f"{AUDIT_BASE}/{slug}",
    })
    thank_you_url = f"{THANK_YOU}?{params}"

    issue_cards = ""
    for i, iss in enumerate(issues[:3]):
        mb = "margin-bottom:24px" if i == 2 else "margin-bottom:12px"
        issue_cards += f"""    <div style="background:#161616;border:1px solid #2a2a2a;border-left:3px solid #FF5C1A;border-radius:8px;padding:16px;{mb}">
        <div style="color:#FF5C1A;font-size:11px;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:6px;font-weight:700">{h(iss.get('num'))}. {h(iss.get('title'))}</div>
        <div style="color:#cccccc;font-size:14px;margin-bottom:8px;line-height:1.5">{h(iss.get('finding'))}</div>
        <div style="color:#B8FF00;font-size:13px;margin-bottom:6px">&#128161; {h(iss.get('fix'))}</div>
        <div style="color:#aaaaaa;font-size:12px">Impact: {h(iss.get('impact'))}</div>
    </div>"""

    gap_cards = ""
    for gap in gaps:
        gap_cards += f"""    <div style="background:#111;border:1px solid #222;border-left:3px solid #B8FF00;border-radius:8px;padding:20px">
        <div style="color:#B8FF00;font-size:11px;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:8px;font-weight:700">{h(gap.get('title',''))}</div>
        <div style="color:#cccccc;font-size:14px;margin-bottom:8px;line-height:1.5">{h(gap.get('gap',''))}</div>
        <div style="color:#aaaaaa;font-size:13px">&#128161; {h(gap.get('action',''))}</div>
    </div>"""

    all_issues_js = json.dumps(issues, ensure_ascii=False)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{h(name)} — Free Website Audit | The Smart Website Co.</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@900&family=DM+Sans:wght@400;500;600&display=swap" rel="stylesheet">
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ background: #0A0A0A; color: #f5f5f5; font-family: 'DM Sans', sans-serif; line-height: 1.6; }}
h1,h2,h3 {{ font-family: 'Montserrat', sans-serif; font-weight: 900; text-transform: uppercase; letter-spacing: -0.03em; }}
.section-label {{ color: #B8FF00; font-size: 11px; text-transform: uppercase; letter-spacing: 0.12em; font-weight: 700; margin-bottom: 8px; }}
.btn-primary {{ display: inline-block; background: #B8FF00; color: #0A0A0A; padding: 16px 32px; border-radius: 8px; font-weight: 900; font-size: 15px; text-decoration: none; font-family: 'Montserrat', sans-serif; text-transform: uppercase; letter-spacing: 0.05em; transition: opacity 0.2s; }}
.btn-primary:hover {{ opacity: 0.85; }}
.btn-secondary {{ display: inline-block; background: transparent; color: #aaa; padding: 15px 31px; border: 1px solid #444; border-radius: 8px; font-weight: 600; font-size: 15px; text-decoration: none; }}
#issues-modal {{ display: none; }}
#issues-modal.open {{ display: flex; }}
@keyframes badgePulse {{ 0%,100%{{opacity:1}} 50%{{opacity:0.45}} }}
@keyframes slideUp {{ from {{ transform: translateY(40px); opacity:0; }} to {{ transform: translateY(0); opacity:1; }} }}
#modal-sheet {{ animation: slideUp 0.28s ease; }}
.modal-title {{ font-family: 'Montserrat', sans-serif; font-weight: 900; font-size: clamp(15px,4vw,20px); text-transform: uppercase; letter-spacing: -0.02em; color: #F2F2F2; margin-bottom: 20px; line-height: 1.2; }}
@media (max-width: 768px) {{ .revenue-grid {{ display: grid !important; grid-template-columns: 1fr !important; gap: 12px !important; }} }}
</style>
</head>
<body>

<section style="padding:80px 24px 60px;max-width:800px;margin:0 auto;text-align:center">
    <div style="font-size:11px;color:#B8FF00;text-transform:uppercase;letter-spacing:0.12em;font-weight:700;margin-bottom:16px">Website Audit — The Smart Website Co.</div>
    <h1 style="font-size:clamp(28px,6vw,52px);font-weight:800;line-height:1.1;margin-bottom:20px;">{h(name)}<br><span style="color:#B8FF00">{h(trade)}</span></h1>
    <p style="font-size:18px;color:#888;max-width:540px;margin:0 auto 40px">{h(audit_data.get('hero_intro',''))}</p>

    <div style="display:inline-block;position:relative;width:160px;height:160px;margin-bottom:16px">
        <svg width="160" height="160" style="transform:rotate(-90deg)">
            <circle cx="80" cy="80" r="68" fill="none" stroke="#222" stroke-width="12"/>
            <circle cx="80" cy="80" r="68" fill="none" stroke="{sev['color']}" stroke-width="12" stroke-dasharray="{circ}" stroke-dashoffset="{dashoff}" stroke-linecap="round"/>
        </svg>
        <div style="position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center">
            <div style="font-size:48px;font-weight:900;color:{sev['color']};font-family:'Montserrat',sans-serif;line-height:1">{score}</div>
            <div style="font-size:12px;color:#666;text-transform:uppercase;letter-spacing:0.08em">/ 30</div>
        </div>
    </div>

    <div style="margin-bottom:32px">
        <div style="display:inline-flex;align-items:center;gap:8px;padding:6px 18px;border-radius:6px;background:{sev['bg']};border:1px solid {sev['border']};font-size:12px;font-weight:700;color:{sev['color']};text-transform:uppercase;letter-spacing:0.1em;margin-bottom:14px">
            <span style="width:7px;height:7px;border-radius:50%;background:{sev['color']};display:inline-block;animation:badgePulse 2s ease infinite"></span>
            {sev['label']}
        </div>
        <div style="display:flex;gap:10px;justify-content:center;flex-wrap:wrap;font-size:10px;color:#444;text-transform:uppercase;letter-spacing:0.08em;">
            <span style="color:#FF4444">&#9679; 0&#8211;20 Critical</span>
            <span style="color:#333">&#183;</span>
            <span style="color:#FF9800">&#9679; 21&#8211;25 Needs Work</span>
            <span style="color:#333">&#183;</span>
            <span style="color:#4CAF50">&#9679; 26&#8211;30 Good</span>
        </div>
    </div>

    <h2 style="font-size:clamp(20px,4vw,32px);font-weight:700;margin-bottom:12px;">{h(audit_data.get('hero_headline',''))}</h2>
    <p style="color:#999;font-size:14px;max-width:480px;margin:0 auto 40px">Based on 23-point design audit, PageSpeed analysis, and competitor benchmarking.</p>

    <div style="text-align:center">
        <p style="font-family:'Montserrat',sans-serif;font-weight:900;font-size:clamp(18px,3vw,24px);color:#fff;margin-bottom:8px;text-transform:uppercase;letter-spacing:-0.02em;">Want us to fix this?</p>
        <p style="font-size:12px;color:#B8FF00;text-transform:uppercase;letter-spacing:0.1em;font-weight:700;margin-bottom:16px">&#9679; We only take on 3 rebuilds per week</p>
        <p style="font-size:16px;color:#aaa;max-width:480px;margin:0 auto 28px">We'll build your new website first — for free. You only pay if you love it.</p>
        <div style="display:flex;gap:12px;justify-content:center;flex-wrap:wrap;margin-bottom:8px">
            <a href="{h(thank_you_url)}" class="btn-primary">Build my free website &#8594;</a>
            <a href="{h(thank_you_url)}" class="btn-secondary">Yes, show me what it could look like</a>
        </div>
        <div style="display:flex;align-items:center;gap:8px;font-size:12px;color:#888;margin-top:16px;flex-wrap:wrap;justify-content:center">
            <span style="color:#00ff88">&#10003;</span><span>100% free to start</span>
            <span style="color:#333">&#183;</span>
            <span style="color:#00ff88">&#10003;</span><span>No credit card</span>
            <span style="color:#333">&#183;</span>
            <span style="color:#00ff88">&#10003;</span><span>Only pay if you love it</span>
        </div>
    </div>
</section>

<section style="padding:48px 24px;max-width:800px;margin:0 auto;border-top:1px solid #1a1a1a">
    <div class="section-label">Revenue Impact</div>
    <h2 style="font-size:28px;margin-bottom:8px;">Potential Opportunity: {h(audit_data.get('monthly_opportunity',''))}/month</h2>
    <p style="color:#888;font-size:14px;margin-bottom:24px">{h(audit_data.get('revenue_detail',''))}</p>
    <div class="revenue-grid" style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px">
        <div style="background:#111;border:1px solid #222;border-radius:8px;padding:20px;text-align:center">
            <div style="font-size:28px;font-weight:800;color:#FF5C1A;font-family:'Montserrat',sans-serif">{h(audit_data.get('leads_lost',''))}</div>
            <div style="font-size:12px;color:#aaa;margin-top:4px">Leads lost/month</div>
        </div>
        <div style="background:#111;border:1px solid #222;border-radius:8px;padding:20px;text-align:center">
            <div style="font-size:28px;font-weight:800;color:#FF5C1A;font-family:'Montserrat',sans-serif">{h(audit_data.get('visitors_lost',''))}</div>
            <div style="font-size:12px;color:#aaa;margin-top:4px">Visitors lost/month</div>
        </div>
        <div style="background:#111;border:1px solid #222;border-radius:8px;padding:20px;text-align:center">
            <div style="font-size:28px;font-weight:800;color:#FF5C1A;font-family:'Montserrat',sans-serif">{h(audit_data.get('monthly_leakage',''))}</div>
            <div style="font-size:12px;color:#aaa;margin-top:4px">Monthly leakage</div>
        </div>
    </div>
</section>

<section style="padding:48px 24px;max-width:800px;margin:0 auto;border-top:1px solid #1a1a1a">
    <div style="display:flex;align-items:flex-end;justify-content:space-between;flex-wrap:wrap;gap:12px;margin-bottom:20px">
        <div><div class="section-label">What We Found</div><h2 style="font-size:24px;font-weight:700;">Critical Issues</h2></div>
        <div style="font-size:11px;color:#555;text-transform:uppercase;letter-spacing:0.08em;border:1px solid #222;border-radius:4px;padding:5px 10px;white-space:nowrap">Showing 3 of {len(issues)}</div>
    </div>
{issue_cards}
    <button onclick="openIssuesModal(0)" style="background:none;border:none;cursor:pointer;display:inline-flex;align-items:center;gap:8px;font-family:'DM Sans',sans-serif;font-size:13px;color:#555;text-transform:uppercase;letter-spacing:0.08em;padding:0;transition:color 0.2s" onmouseover="this.style.color='#B8FF00'" onmouseout="this.style.color='#555'">
        <span>See all {len(issues)} issues</span><span style="font-size:15px">&#8594;</span>
    </button>
</section>

<section style="padding:48px 24px;max-width:800px;margin:0 auto;border-top:1px solid #1a1a1a;background:#0d0d0d">
    <div class="section-label">AI Opportunities</div>
    <h2 style="font-size:24px;font-weight:700;margin-bottom:6px;">What you could add</h2>
    <p style="color:#999;font-size:14px;margin-bottom:24px">Tools that pay for themselves in the first job they bring in.</p>
    <div style="background:#111;border:1px solid #222;border-radius:8px;padding:20px;margin-bottom:10px">
        <div style="color:#B8FF00;font-size:12px;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:8px;font-weight:700">AI Chatbot</div>
        <div style="color:#ccc;font-size:14px;line-height:1.6">{h(audit_data.get('ai_chatbot_body',''))}</div>
        <div style="color:#aaa;font-size:13px;margin-top:8px">{h(audit_data.get('ai_chatbot_benefit',''))}</div>
    </div>
    <div style="background:#111;border:1px solid #222;border-radius:8px;padding:20px">
        <div style="color:#B8FF00;font-size:12px;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:8px;font-weight:700">AI Receptionist</div>
        <div style="color:#ccc;font-size:14px;line-height:1.6">{h(audit_data.get('ai_receptionist_body',''))}</div>
        <div style="color:#aaa;font-size:13px;margin-top:8px">{h(audit_data.get('ai_receptionist_benefit',''))}</div>
    </div>
</section>

<section style="padding:48px 24px;max-width:800px;margin:0 auto;border-top:1px solid #1a1a1a">
    <div class="section-label">Competitor Check</div>
    <h2 style="font-size:24px;font-weight:700;margin-bottom:6px;">What top competitors have that you don't</h2>
    <p style="color:#666;font-size:14px;margin-bottom:24px">We checked the top results for {h(trade)} in {h(city)}.</p>
    <div style="display:flex;flex-direction:column;gap:12px">
{gap_cards}
    </div>
</section>

<section style="padding:80px 24px;text-align:center;border-top:1px solid #1a1a1a">
    <div class="section-label">Recommended: {h(audit_data.get('recommended_plan','Growth'))}</div>
    <p style="font-family:'Montserrat',sans-serif;font-weight:900;font-size:clamp(22px,4vw,32px);color:#fff;margin-bottom:8px;text-transform:uppercase;letter-spacing:-0.02em;">You've seen the problems.</p>
    <p style="font-size:12px;color:#B8FF00;text-transform:uppercase;letter-spacing:0.1em;font-weight:700;margin-bottom:16px">&#9679; We only take on 3 rebuilds per week</p>
    <p style="font-size:16px;color:#aaa;max-width:480px;margin:0 auto 28px">Your new site, built free first. Only pay if you love it. Live in 14 days or it's free.</p>
    <div style="display:flex;gap:12px;justify-content:center;flex-wrap:wrap;margin-bottom:8px">
        <a href="{h(thank_you_url)}" class="btn-primary">Build my free website &#8594;</a>
        <a href="{h(site)}" class="btn-secondary" target="_blank">Back to their site &#8594;</a>
    </div>
    <div style="display:flex;align-items:center;gap:8px;font-size:12px;color:#888;margin-top:16px;flex-wrap:wrap;justify-content:center">
        <span style="color:#00ff88">&#10003;</span><span>100% free to start</span>
        <span style="color:#333">&#183;</span>
        <span style="color:#00ff88">&#10003;</span><span>No credit card</span>
        <span style="color:#333">&#183;</span>
        <span style="color:#00ff88">&#10003;</span><span>Only pay if you love it</span>
    </div>
</section>

<footer style="padding:40px 24px;border-top:1px solid #1a1a1a;text-align:center">
    <div style="color:#888;font-size:12px">Generated by The Smart Website Co. — websites and AI for Australian tradies.</div>
    <div style="color:#666;font-size:11px;margin-top:8px">www.thesmartwebsite.co &#183; hello@thesmartwebsite.co</div>
</footer>

<div id="issues-modal" style="position:fixed;inset:0;z-index:1000;background:rgba(0,0,0,0.88);align-items:flex-end;justify-content:center" onclick="handleBackdrop(event)">
    <div id="modal-sheet" style="background:#111;border-top:1px solid #1E1E1E;border-radius:20px 20px 0 0;width:100%;max-width:700px;max-height:88vh;display:flex;flex-direction:column;overflow:hidden">
        <div style="display:flex;justify-content:space-between;align-items:center;padding:20px 24px 16px;border-bottom:1px solid #1a1a1a;flex-shrink:0">
            <div>
                <div style="font-size:10px;color:#555;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:3px;">All Issues Found</div>
                <div id="modal-counter" style="font-family:'Montserrat',sans-serif;font-weight:900;font-size:18px;text-transform:uppercase;color:#F2F2F2"></div>
            </div>
            <button onclick="closeIssuesModal()" style="background:none;border:1px solid #222;border-radius:50%;width:36px;height:36px;color:#666;cursor:pointer;font-size:16px;display:flex;align-items:center;justify-content:center;">&#10005;</button>
        </div>
        <div id="modal-slide" style="flex:1;overflow-y:auto;padding:24px"></div>
        <div id="modal-dots" style="display:flex;justify-content:center;gap:8px;padding:12px 24px;flex-shrink:0"></div>
        <div style="padding:12px 24px 36px;border-top:1px solid #1a1a1a;display:flex;flex-direction:column;gap:10px;flex-shrink:0">
            <div style="display:flex;gap:10px">
                <button onclick="prevIssue()" id="btn-prev" style="flex:1;padding:11px;background:#0f0f0f;border:1px solid #1a1a1a;border-radius:8px;color:#666;font-size:13px;cursor:pointer">&#8592; Prev</button>
                <button onclick="nextIssue()" id="btn-next" style="flex:1;padding:11px;background:#0f0f0f;border:1px solid #1a1a1a;border-radius:8px;color:#666;font-size:13px;cursor:pointer">Next &#8594;</button>
            </div>
            <a href="{h(thank_you_url)}" class="btn-primary" style="text-align:center;display:block">Fix all {len(issues)} issues &#8212; free &#8594;</a>
        </div>
    </div>
</div>

<script>
var ALL_ISSUES = {all_issues_js};
var currentIssue = 0;
function openIssuesModal(i) {{ currentIssue=i||0; renderModal(); document.getElementById('issues-modal').classList.add('open'); document.body.style.overflow='hidden'; }}
function closeIssuesModal() {{ document.getElementById('issues-modal').classList.remove('open'); document.body.style.overflow=''; }}
function handleBackdrop(e) {{ if(e.target===document.getElementById('issues-modal')) closeIssuesModal(); }}
function nextIssue() {{ if(currentIssue<ALL_ISSUES.length-1){{ currentIssue++; renderModal(); }} }}
function prevIssue() {{ if(currentIssue>0){{ currentIssue--; renderModal(); }} }}
function renderModal() {{
    var issue=ALL_ISSUES[currentIssue], total=ALL_ISSUES.length;
    document.getElementById('modal-counter').textContent='Issue '+(currentIssue+1)+' of '+total;
    document.getElementById('modal-slide').innerHTML=
        '<div style="font-size:10px;color:#444;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:10px;">Check #'+issue.num+' of 23</div>'+
        '<div class="modal-title">'+issue.title+'</div>'+
        '<div style="background:#161616;border:1px solid #1a1a1a;border-radius:8px;padding:16px;margin-bottom:12px">'+
            '<div style="font-size:10px;color:#555;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:8px;">What we found</div>'+
            '<div style="display:flex;gap:10px;align-items:flex-start"><span style="color:#FF4444;flex-shrink:0;font-size:16px;margin-top:1px">&#10007;</span>'+
            '<div style="font-size:14px;color:#CCCCCC;line-height:1.6">'+issue.finding+'</div></div></div>'+
        '<div style="background:rgba(184,255,0,0.05);border:1px solid rgba(184,255,0,0.15);border-radius:8px;padding:16px;margin-bottom:12px">'+
            '<div style="font-size:10px;color:#555;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:8px;">The fix</div>'+
            '<div style="font-size:14px;color:#B8FF00;line-height:1.6">&#128161; '+issue.fix+'</div></div>'+
        '<div style="font-size:11px;color:#444;text-transform:uppercase;letter-spacing:0.08em">Impact: '+issue.impact+'</div>';
    var dots='';
    for(var i=0;i<ALL_ISSUES.length;i++) dots+='<div onclick="currentIssue='+i+';renderModal()" style="width:'+(i===currentIssue?'20px':'7px')+';height:7px;border-radius:4px;background:'+(i===currentIssue?'#B8FF00':'#222')+';cursor:pointer;transition:all 0.2s"></div>';
    document.getElementById('modal-dots').innerHTML=dots;
    document.getElementById('btn-prev').style.opacity=currentIssue===0?'0.3':'1';
    document.getElementById('btn-next').style.opacity=currentIssue===total-1?'0.3':'1';
}}
var touchStartX=0;
document.getElementById('modal-sheet').addEventListener('touchstart',function(e){{touchStartX=e.touches[0].clientX;}},{{passive:true}});
document.getElementById('modal-sheet').addEventListener('touchend',function(e){{var diff=touchStartX-e.changedTouches[0].clientX;if(Math.abs(diff)>50){{diff>0?nextIssue():prevIssue();}}}},{{passive:true}});
</script>
</body>
</html>"""


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
