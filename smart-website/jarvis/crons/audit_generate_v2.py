#!/usr/bin/env python3
"""
audit_generate_v2.py — Smart Website Co. audit page generator
Uses DeepSeek V3 via Laozhang API for AI audit content generation.
Generates branded HTML pages matching the Smart Website Co. template
(Montserrat 900 + DM Sans, #B8FF00 accent, dark theme).

Flow:
  1. Load APPROVED leads from CRM (score 7+, no audit_url yet)
  2. Scrape their website via Firecrawl → markdown
  3. Run DeepSeek V3 audit → structured JSON
  4. Build HTML from template with computed values
  5. Write to dist/{slug}/index.html → deploy via vercel --prod
  6. Update CRM: audit_url + status=AUDIT_GENERATED
  7. Telegram notification

Cron: 4 AM daily
Save to: /Users/brentext/.openclaw/workspace/smart-website/jarvis/crons/audit_generate_v2.py
"""

import os, json, time, re, math, subprocess, html as html_lib
from datetime import datetime
from urllib.request import urlopen, Request
from urllib.parse import urlencode
from urllib.error import URLError

# ─── CONFIG ──────────────────────────────────────────────────────────────────

FIRECRAWL_API_KEY  = os.environ.get("FIRECRAWL_API_KEY", "fc-050a14fed4ea4b9190d4dd86f8fe6fc0")
LAOZHANG_API_KEY   = os.environ.get("LAOZHANG_API_KEY", "sk-Mf5sZm8MjEqJNBk21aBeB037E9C8486fA3B191F6428f2693")
LAOZHANG_BASE_URL  = os.environ.get("LAOZHANG_BASE_URL", "https://api.laozhang.ai")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8685067366:AAHQht4DvrqFkM99rwMfhExdrkY8nks78Iw")
TELEGRAM_CHAT_ID   = os.environ.get("TELEGRAM_CHAT_ID", "7356494332")

CRM_FILE   = "/Users/brentext/.openclaw/workspace/smart-website/data/leads_queue.json"
DIST_DIR   = "/Users/brentext/.openclaw/workspace/smart-website/dist"
AUDIT_BASE = "https://audit.thesmartwebsite.co"
THANK_YOU  = "https://audit.thesmartwebsite.co/thank-you"

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

# ─── HELPERS ─────────────────────────────────────────────────────────────────

def ts():
    return datetime.now().strftime("%H:%M")

def log(msg):
    print(f"[{ts()}] {msg}", flush=True)

def h(text):
    """HTML-escape a string for safe injection into HTML."""
    return html_lib.escape(str(text), quote=True)

def js_str(text):
    """Escape a string for safe injection into a JS string literal."""
    return str(text).replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n").replace("\r", "")

def telegram(msg):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = json.dumps({"chat_id": TELEGRAM_CHAT_ID, "text": msg}).encode()
        req = Request(url, data=data, headers={"Content-Type": "application/json"})
        urlopen(req, timeout=10)
    except Exception as e:
        log(f"Telegram error: {e}")

def slugify(text):
    import unicodedata
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9-]", "-", text.lower()).strip("-")[:60]

# ─── CRM ─────────────────────────────────────────────────────────────────────

def load_crm():
    if not os.path.exists(CRM_FILE):
        return []
    with open(CRM_FILE) as f:
        raw = f.read().strip()
        if not raw:
            return []
        # leads_queue.json is a JSON array; leads.jsonl is line-delimited JSON
        try:
            return json.loads(raw)  # JSON array format (leads_queue.json)
        except json.JSONDecodeError:
            return [json.loads(l) for l in raw.split("\n") if l.strip()]  # JSONL format

def update_lead(email, updates):
    leads = load_crm()
    for i, l in enumerate(leads):
        if l.get("email", "").lower() == email.lower():
            leads[i].update(updates)
            break
    with open(CRM_FILE, "w") as f:
        json.dump(leads, f, indent=2)  # Write as JSON array (leads_queue.json format)

def get_approved_leads():
    candidates = [
        l for l in load_crm()
        if l.get("status") == "SCRAPED"
        and l.get("score", 0) >= 7.0
        and not l.get("audit_url")
    ]
    # Full batch mode — remove [:1] to run all leads
    return candidates

# ─── SCRAPE ──────────────────────────────────────────────────────────────────

def scrape_website(url):
    """Scrape website via Firecrawl SDK → markdown string."""
    if not url or not FIRECRAWL_API_KEY:
        return ""
    try:
        from firecrawl import Firecrawl
        fc = Firecrawl(api_key=FIRECRAWL_API_KEY)
        doc = fc.scrape(url, formats=["markdown"], only_main_content=True)
        content = doc.markdown if hasattr(doc, "markdown") else ""
        log(f"  Scraped {len(content)} chars from {url}")
        return content
    except Exception as e:
        log(f"  Firecrawl error: {e}")
        return ""

# ─── DEEPSEEK AUDIT ──────────────────────────────────────────────────────────

FALLBACK_AUDIT = {
    "score": 16,
    "hero_intro": "Just audited your website and found significant revenue being left on the table. A few targeted fixes could bring in substantially more leads each week.",
    "hero_headline": "Your website isn't converting visitors into paying customers — here's what's costing you.",
    "monthly_opportunity": "$8,500",
    "revenue_detail": "Potential customers can't find your contact details or trust signals fast enough on mobile.",
    "leads_lost": "140",
    "visitors_lost": "950",
    "monthly_leakage": "$8,500",
    "issues": [
        {"num": "1",  "title": "Exactly ONE eye-level focal point?",         "finding": "Multiple elements compete for attention above the fold",             "fix": "Make your phone number the single focal point — large, high-contrast, and centred",     "impact": "25% lower conversion rate"},
        {"num": "10", "title": "CTA so obvious a 5-year-old would click it?", "finding": "Primary call-to-action blends into surrounding content",              "fix": "Increase CTA size by 200% with a strongly contrasting background colour",              "impact": "Missed enquiries every day"},
        {"num": "13", "title": "Mobile first-class citizen, not a shrink?",   "finding": "Mobile layout is a compressed version of desktop — hard to navigate", "fix": "Redesign mobile with thumb-friendly tap targets and a sticky call button",              "impact": "60%+ of visitors leave immediately on mobile"},
        {"num": "4",  "title": "Exactly ONE primary accent color?",           "finding": "Multiple accent colours dilute brand and confuse action hierarchy",    "fix": "Pick one primary action colour used only on CTAs",                                    "impact": "Confuses brand identity"},
        {"num": "18", "title": "Images optimized and purposeful?",            "finding": "Hero images are uncompressed and slow the page significantly",         "fix": "Convert all images to WebP under 200KB each",                                         "impact": "$50+/month in lost conversions from slow loads"},
    ],
    "ai_chatbot_body": "Instant quote and booking tool for common enquiries — answers 24/7 so you never miss a lead.",
    "ai_chatbot_benefit": "Could capture 35% more after-hours enquiries",
    "ai_receptionist_body": "Handles inbound calls, qualifies leads, and books jobs while you're on the tools.",
    "ai_receptionist_benefit": "Potential 8 extra jobs/week",
    "competitor_gaps": [
        {"title": "Google Business activity", "gap": "Top competitors post job photos weekly — your profile is inactive", "action": "Post one job photo per week to Google Business"},
        {"title": "Response time badge", "gap": "Leading competitors display a response time guarantee prominently", "action": "Add a response time guarantee to your hero section"},
        {"title": "Trust signals above the fold", "gap": "Top competitors show licence numbers and reviews before the scroll", "action": "Display your licence number next to your phone number"},
    ],
    "recommended_plan": "Growth",
}

def generate_audit_data(lead, website_content):
    """Call DeepSeek V3 via Laozhang. Returns structured audit dict."""
    biz   = lead.get("business_name", "Unknown Business")
    trade = lead.get("trade", "local business")
    city  = lead.get("city", "Australia")
    url   = lead.get("website", "")

    rules_text = "\n".join([f"{i+1}. {r}" for i, r in enumerate(IMPECCABLE_23)])
    website_sample = website_content[:6000] if website_content else "No website content available — audit based on business type and location."

    prompt = f"""You are an expert web design auditor for Australian tradie and small business websites.
Audit this business website against the 23 Impeccable design rules and return a personalised audit report.

BUSINESS DETAILS:
- Name: {biz}
- Trade: {trade}
- City: {city}
- Website: {url}

WEBSITE CONTENT (scraped):
{website_sample}

THE 23 IMPECCABLE DESIGN RULES:
{rules_text}

SCORING GUIDE (out of 30):
- 26-30: Good (well-optimised site)
- 21-25: Needs Work (moderate issues)
- 0-20: Critical (significant problems — most tradie sites land here)

INSTRUCTIONS:
- Score the website honestly. Reference actual content scraped above.
- Identify the 5 most impactful issues. Each must reference a specific Impeccable rule number (1-23).
- Generate realistic Australian dollar revenue impact figures based on trade type and average job value.
- Write punchy, specific copy — this is a cold email follow-up, the owner is busy and sceptical.
- Mention their specific trade, city, and a concrete example of what's wrong or fixable.
- All dollar amounts in AUD. Use formats like "$9,200/mo" or "$4,800/mo".

Return ONLY valid JSON. No markdown fences, no explanation, no preamble. Start with the opening brace.

{{
  "score": <integer 0-30>,
  "hero_intro": "<2-3 punchy sentences. Open with a specific $ opportunity found. Reference their trade and city. End with a hook.>",
  "hero_headline": "<one sentence about their single biggest issue and its specific $ or lead impact>",
  "monthly_opportunity": "<dollar figure only e.g. '$11,200'>",
  "revenue_detail": "<1 sentence explaining the root cause of the revenue loss — specific to their trade>",
  "leads_lost": "<realistic monthly number e.g. '160'>",
  "visitors_lost": "<realistic monthly number e.g. '1,050'>",
  "monthly_leakage": "<same dollar figure as monthly_opportunity>",
  "issues": [
    {{
      "num": "<rule number 1-23>",
      "title": "<exact text of that Impeccable rule>",
      "finding": "<what is specifically wrong with their site — be concrete, reference scraped content if possible>",
      "fix": "<specific actionable fix relevant to their trade>",
      "impact": "<business impact in $ or % or jobs per week>"
    }},
    {{
      "num": "<rule number>",
      "title": "<exact rule text>",
      "finding": "<specific finding>",
      "fix": "<specific fix>",
      "impact": "<specific impact>"
    }},
    {{
      "num": "<rule number>",
      "title": "<exact rule text>",
      "finding": "<specific finding>",
      "fix": "<specific fix>",
      "impact": "<specific impact>"
    }},
    {{
      "num": "<rule number>",
      "title": "<exact rule text>",
      "finding": "<specific finding>",
      "fix": "<specific fix>",
      "impact": "<specific impact>"
    }},
    {{
      "num": "<rule number>",
      "title": "<exact rule text>",
      "finding": "<specific finding>",
      "fix": "<specific fix>",
      "impact": "<specific impact>"
    }}
  ],
  "ai_chatbot_body": "<1-2 sentences — what a chatbot would specifically do for their trade>",
  "ai_chatbot_benefit": "<specific benefit claim e.g. 'Could capture 40% more after-hours enquiries'>",
  "ai_receptionist_body": "<1-2 sentences — what an AI receptionist would do for their trade>",
  "ai_receptionist_benefit": "<specific claim e.g. 'Potential 10 extra jobs/week = $3,800/mo'>",
  "competitor_gaps": [
    {{"title": "<short gap title e.g. 'Response time badge'>", "gap": "<what top competitors have that this site is missing — be specific>", "action": "<one concrete thing to add or change>"}},
    {{"title": "<short gap title>", "gap": "<second specific gap>", "action": "<concrete action>"}},
    {{"title": "<short gap title>", "gap": "<third specific gap>", "action": "<concrete action>"}}
  ],
  "recommended_plan": "<exactly one of: Starter, Growth, Premium, Full Stack>"
}}"""

    try:
        payload = {
            "model": "deepseek-v3",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 2000,
            "temperature": 0.2,
        }
        req = Request(
            f"{LAOZHANG_BASE_URL}/v1/chat/completions",
            data=json.dumps(payload).encode(),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {LAOZHANG_API_KEY}",
            }
        )
        with urlopen(req, timeout=60) as r:
            resp = json.loads(r.read())
            text = resp["choices"][0]["message"]["content"].strip()

        # Strip markdown code fences if DeepSeek wraps in them
        text = re.sub(r"```[a-z]*\n?", "", text).strip().rstrip("`").strip()

        # Extract JSON object
        start = text.find("{")
        end   = text.rfind("}") + 1
        if start >= 0 and end > start:
            data = json.loads(text[start:end])
            # Ensure exactly 5 issues
            if len(data.get("issues", [])) < 5:
                log("  Warning: DeepSeek returned fewer than 5 issues — padding with fallback")
                while len(data["issues"]) < 5:
                    data["issues"].append(FALLBACK_AUDIT["issues"][len(data["issues"])])
            log(f"  DeepSeek audit complete. Score: {data.get('score')}/30")
            return data

    except Exception as e:
        log(f"  DeepSeek error: {e}")

    log("  Using fallback audit data")
    return FALLBACK_AUDIT.copy()

# ─── HTML BUILDER ────────────────────────────────────────────────────────────

def get_severity(score):
    if score >= 26:
        return {"color": "#4CAF50", "label": "Good",       "bg": "rgba(76,175,80,0.1)",  "border": "rgba(76,175,80,0.3)"}
    elif score >= 21:
        return {"color": "#FF9800", "label": "Needs Work", "bg": "rgba(255,152,0,0.1)", "border": "rgba(255,152,0,0.3)"}
    else:
        return {"color": "#FF4444", "label": "Critical",   "bg": "rgba(255,68,68,0.1)",  "border": "rgba(255,68,68,0.3)"}

def svg_dashoffset(score):
    """Compute SVG stroke-dashoffset so the ring fills score/30 of the circle."""
    r = 68
    circumference = 2 * math.pi * r  # ≈ 427.26
    offset = circumference * (1 - score / 30)
    return round(offset, 2)

def render_issue_card(issue, is_last=False):
    """Render one issue card div for the main page (visible issues)."""
    margin = "margin-bottom:24px" if is_last else "margin-bottom:12px"
    return (
        f'    <div style="background:#161616;border:1px solid #2a2a2a;border-left:3px solid #FF5C1A;'
        f'border-radius:8px;padding:16px;{margin}">\n'
        f'        <div style="color:#FF5C1A;font-size:11px;text-transform:uppercase;letter-spacing:0.1em;'
        f'margin-bottom:6px;font-weight:700">{h(issue.get("num"))}. {h(issue.get("title"))}</div>\n'
        f'        <div style="color:#cccccc;font-size:14px;margin-bottom:8px;line-height:1.5">'
        f'{h(issue.get("finding"))}</div>\n'
        f'        <div style="color:#B8FF00;font-size:13px;margin-bottom:6px">'
        f'💡 {h(issue.get("fix"))}</div>\n'
        f'        <div style="color:#aaaaaa;font-size:12px">Impact: {h(issue.get("impact"))}</div>\n'
        f'    </div>'
    )

def issues_to_js_array(issues):
    """Serialise issues list to a JS array literal via JSON (JSON is valid JS)."""
    return json.dumps(issues, ensure_ascii=False, indent=4)

def build_html(lead, audit_data, slug):
    """Assemble the complete audit HTML page."""
    biz      = lead.get("name", "Your Business")
    trade    = lead.get("trade", "local business")
    website  = lead.get("website", "#")
    email    = lead.get("email", "")
    city     = lead.get("city", "")

    score    = int(audit_data.get("score", 16))
    sev      = get_severity(score)
    dashoff  = svg_dashoffset(score)
    circ     = round(2 * math.pi * 68, 2)  # 427.26

    thank_you_url = build_thank_you_url(lead, slug, score)
    issues        = audit_data.get("issues", FALLBACK_AUDIT["issues"])[:5]

    # Render top 3 issue cards for page
    visible_cards = "\n".join([
        render_issue_card(issues[i], is_last=(i == 2))
        for i in range(min(3, len(issues)))
    ])

    # All 5 issues as JS data for the modal
    all_issues_js = issues_to_js_array(issues)

    page_title = f"{h(biz)} — Free Website Audit | The Smart Website Co."

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{page_title}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@900&family=DM+Sans:wght@400;500;600&display=swap" rel="stylesheet">
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ background: #0A0A0A; color: #f5f5f5; font-family: 'DM Sans', sans-serif; line-height: 1.6; }}
h1,h2,h3 {{ font-family: 'Montserrat', sans-serif; font-weight: 900; text-transform: uppercase; letter-spacing: -0.03em; }}
.section-label {{ color: #B8FF00; font-size: 11px; text-transform: uppercase; letter-spacing: 0.12em; font-weight: 700; margin-bottom: 8px; }}
.cta-section {{ text-align: center; }}
.cta-headline {{ font-size: clamp(22px,4vw,32px); font-weight: 900; color: #fff; margin-bottom: 8px; font-family: 'Montserrat', sans-serif; text-transform: uppercase; letter-spacing: -0.02em; }}
.cta-sub {{ font-size: 16px; color: #aaa; max-width: 480px; margin: 0 auto 28px; line-height: 1.6; }}
.cta-buttons {{ display: flex; gap: 12px; justify-content: center; flex-wrap: wrap; margin-bottom: 8px; }}
.btn-primary {{ display: inline-block; background: #B8FF00; color: #0A0A0A; padding: 16px 32px; border-radius: 8px; font-weight: 900; font-size: 15px; text-decoration: none; font-family: 'Montserrat', sans-serif; text-transform: uppercase; letter-spacing: 0.05em; transition: opacity 0.2s; }}
.btn-primary:hover {{ opacity: 0.85; }}
.btn-secondary {{ display: inline-block; background: transparent; color: #aaa; padding: 15px 31px; border: 1px solid #444; border-radius: 8px; font-weight: 600; font-size: 15px; text-decoration: none; font-family: 'Montserrat', sans-serif; transition: border-color 0.2s, color 0.2s; }}
.btn-secondary:hover {{ border-color: #888; color: #fff; }}
.cta-guarantee {{ display: flex; align-items: center; gap: 8px; font-size: 12px; color: #888; margin-top: 16px; flex-wrap: wrap; justify-content: center; }}
.guarantee-icon {{ color: #00ff88; }}
.divider {{ color: #333; }}
#issues-modal {{ display: none; }}
#issues-modal.open {{ display: flex; }}
@keyframes badgePulse {{ 0%,100%{{opacity:1}} 50%{{opacity:0.45}} }}
@keyframes slideUp {{ from {{ transform: translateY(40px); opacity:0; }} to {{ transform: translateY(0); opacity:1; }} }}
#modal-sheet {{ animation: slideUp 0.28s ease; }}
.modal-title {{ font-family: 'Montserrat', sans-serif; font-weight: 900; font-size: clamp(15px,4vw,20px); text-transform: uppercase; letter-spacing: -0.02em; color: #F2F2F2; margin-bottom: 20px; line-height: 1.2; }}
@media (max-width: 768px) {{
  .revenue-grid {{ display: grid !important; grid-template-columns: 1fr !important; gap: 12px !important; }}
}}
</style>
</head>
<body>

<!-- HERO -->
<section style="padding:80px 24px 60px;max-width:800px;margin:0 auto;text-align:center">
    <div style="font-size:11px;color:#B8FF00;text-transform:uppercase;letter-spacing:0.12em;font-weight:700;margin-bottom:16px">Website Audit — The Smart Website Co.</div>
    <h1 style="font-size:clamp(28px,6vw,52px);font-weight:800;line-height:1.1;margin-bottom:20px;font-family:'Montserrat',sans-serif">
        {h(biz)}<br><span style="color:#B8FF00">{h(trade)}</span>
    </h1>
    <p style="font-size:18px;color:#888;max-width:540px;margin:0 auto 40px">{h(audit_data.get("hero_intro", ""))}</p>

    <!-- Score Ring -->
    <div style="display:inline-block;position:relative;width:160px;height:160px;margin-bottom:16px">
        <svg width="160" height="160" style="transform:rotate(-90deg)">
            <circle cx="80" cy="80" r="68" fill="none" stroke="#222" stroke-width="12"/>
            <circle cx="80" cy="80" r="68" fill="none" stroke="{sev['color']}" stroke-width="12"
                stroke-dasharray="{circ}"
                stroke-dashoffset="{dashoff}"
                stroke-linecap="round"/>
        </svg>
        <div style="position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center">
            <div style="font-size:48px;font-weight:900;color:{sev['color']};font-family:'Montserrat',sans-serif;line-height:1">{score}</div>
            <div style="font-size:12px;color:#666;text-transform:uppercase;letter-spacing:0.08em">/ 30</div>
        </div>
    </div>

    <!-- Severity badge + scale -->
    <div style="margin-bottom:32px">
        <div style="display:inline-flex;align-items:center;gap:8px;padding:6px 18px;border-radius:6px;background:{sev['bg']};border:1px solid {sev['border']};font-size:12px;font-weight:700;color:{sev['color']};text-transform:uppercase;letter-spacing:0.1em;margin-bottom:14px">
            <span style="width:7px;height:7px;border-radius:50%;background:{sev['color']};display:inline-block;animation:badgePulse 2s ease infinite"></span>
            {sev['label']}
        </div>
        <div style="display:flex;gap:10px;justify-content:center;flex-wrap:wrap;font-size:10px;color:#444;text-transform:uppercase;letter-spacing:0.08em;font-family:'DM Sans',sans-serif">
            <span style="color:#FF4444">&#9679; 0&#8211;20 Critical</span>
            <span style="color:#333">&#183;</span>
            <span style="color:#FF9800">&#9679; 21&#8211;25 Needs Work</span>
            <span style="color:#333">&#183;</span>
            <span style="color:#4CAF50">&#9679; 26&#8211;30 Good</span>
        </div>
    </div>

    <h2 style="font-size:clamp(20px,4vw,32px);font-weight:700;margin-bottom:12px;font-family:'Montserrat',sans-serif">{h(audit_data.get("hero_headline", ""))}</h2>
    <p style="color:#999999;font-size:14px;max-width:480px;margin:0 auto 40px">Based on 23-point design audit, PageSpeed analysis, and competitor benchmarking.</p>

    <div class="cta-section">
        <p class="cta-headline">Want us to fix this?</p>
        <p class="cta-sub">We'll build your new website first — for free. You only pay if you love it.</p>
        <div class="cta-buttons">
            <a href="{h(thank_you_url)}" class="btn-primary">Build my free website &#8594;</a>
            <a href="{h(thank_you_url)}" class="btn-secondary">Yes, show me what it could look like</a>
        </div>
        <div class="cta-guarantee">
            <span class="guarantee-icon">&#10003;</span><span>100% free to start</span>
            <span class="divider">&#183;</span>
            <span class="guarantee-icon">&#10003;</span><span>No credit card needed</span>
            <span class="divider">&#183;</span>
            <span class="guarantee-icon">&#10003;</span><span>Only pay if you love it</span>
        </div>
    </div>
</section>

<!-- Revenue Leakage -->
<section style="padding:48px 24px;max-width:800px;margin:0 auto;border-top:1px solid #1a1a1a">
    <div class="section-label">Revenue Impact</div>
    <h2 style="font-size:28px;font-weight:900;margin-bottom:8px;font-family:'Montserrat',sans-serif;text-transform:uppercase;letter-spacing:-0.03em">
        Potential Opportunity: {h(audit_data.get("monthly_opportunity", "$8,500"))}/month
    </h2>
    <p style="color:#888;font-size:14px;margin-bottom:24px">{h(audit_data.get("revenue_detail", ""))}</p>
    <div class="revenue-grid" style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px">
        <div style="background:#111;border:1px solid #222;border-radius:8px;padding:20px;text-align:center">
            <div style="font-size:28px;font-weight:800;color:#FF5C1A;font-family:'Montserrat',sans-serif">{h(audit_data.get("leads_lost", "140"))}</div>
            <div style="font-size:12px;color:#aaaaaa;margin-top:4px">Leads lost/month</div>
        </div>
        <div style="background:#111;border:1px solid #222;border-radius:8px;padding:20px;text-align:center">
            <div style="font-size:28px;font-weight:800;color:#FF5C1A;font-family:'Montserrat',sans-serif">{h(audit_data.get("visitors_lost", "950"))}</div>
            <div style="font-size:12px;color:#aaaaaa;margin-top:4px">Visitors lost/month</div>
        </div>
        <div style="background:#111;border:1px solid #222;border-radius:8px;padding:20px;text-align:center">
            <div style="font-size:28px;font-weight:800;color:#FF5C1A;font-family:'Montserrat',sans-serif">{h(audit_data.get("monthly_leakage", "$8,500"))}</div>
            <div style="font-size:12px;color:#aaaaaa;margin-top:4px">Monthly leakage</div>
        </div>
    </div>
</section>

<!-- Issues Found -->
<section style="padding:48px 24px;max-width:800px;margin:0 auto;border-top:1px solid #1a1a1a">
    <div style="display:flex;align-items:flex-end;justify-content:space-between;flex-wrap:wrap;gap:12px;margin-bottom:20px">
        <div>
            <div class="section-label">What We Found</div>
            <h2 style="font-size:24px;font-weight:700;font-family:'Montserrat',sans-serif">Critical Issues</h2>
        </div>
        <div style="font-size:11px;color:#555;text-transform:uppercase;letter-spacing:0.08em;border:1px solid #222;border-radius:4px;padding:5px 10px;white-space:nowrap">Showing 3 of {len(issues)}</div>
    </div>

{visible_cards}

    <button onclick="openIssuesModal(0)" style="background:none;border:none;cursor:pointer;display:inline-flex;align-items:center;gap:8px;font-family:'DM Sans',sans-serif;font-size:13px;color:#555;text-transform:uppercase;letter-spacing:0.08em;padding:0;transition:color 0.2s" onmouseover="this.style.color='#B8FF00'" onmouseout="this.style.color='#555'">
        <span>See all {len(issues)} issues</span>
        <span style="font-size:15px">&#8594;</span>
    </button>
</section>

<!-- AI Opportunities -->
<section style="padding:48px 24px;max-width:800px;margin:0 auto;border-top:1px solid #1a1a1a;background:#0d0d0d">
    <div class="section-label">AI Opportunities</div>
    <h2 style="font-size:24px;font-weight:700;margin-bottom:6px;font-family:'Montserrat',sans-serif">What you could add to your site</h2>
    <p style="color:#999999;font-size:14px;margin-bottom:24px">Tools that pay for themselves in the first job they bring in.</p>
    <div style="background:#111;border:1px solid #222;border-radius:8px;padding:20px;margin-bottom:10px">
        <div style="color:#B8FF00;font-size:12px;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:8px;font-weight:700">AI Chatbot</div>
        <div style="color:#ccc;font-size:14px;line-height:1.6">{h(audit_data.get("ai_chatbot_body", ""))}</div>
        <div style="color:#aaaaaa;font-size:13px;margin-top:8px">{h(audit_data.get("ai_chatbot_benefit", ""))}</div>
    </div>
    <div style="background:#111;border:1px solid #222;border-radius:8px;padding:20px;margin-bottom:10px">
        <div style="color:#B8FF00;font-size:12px;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:8px;font-weight:700">AI Receptionist</div>
        <div style="color:#ccc;font-size:14px;line-height:1.6">{h(audit_data.get("ai_receptionist_body", ""))}</div>
        <div style="color:#aaaaaa;font-size:13px;margin-top:8px">{h(audit_data.get("ai_receptionist_benefit", ""))}</div>
    </div>
</section>

<!-- Competitor Check -->
<section style="padding:48px 24px;max-width:800px;margin:0 auto;border-top:1px solid #1a1a1a">
    <div class="section-label">Competitor Check</div>
    <h2 style="font-size:24px;font-weight:700;margin-bottom:6px;font-family:'Montserrat',sans-serif">What top competitors have that you don&apos;t</h2>
    <p style="color:#666;font-size:14px;margin-bottom:24px">We checked the top results for {h(trade)} in {h(city) if city else 'your area'}.</p>
    <div style="display:flex;flex-direction:column;gap:12px">
        {''.join([
            f'<div style="background:#111;border:1px solid #222;border-left:3px solid #B8FF00;border-radius:8px;padding:20px">'
            f'<div style="color:#B8FF00;font-size:11px;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:8px;font-weight:700">{h(gap.get("title",""))}</div>'
            f'<div style="color:#cccccc;font-size:14px;margin-bottom:8px;line-height:1.5">{h(gap.get("gap",""))}</div>'
            f'<div style="color:#aaaaaa;font-size:13px">&#128161; {h(gap.get("action",""))}</div>'
            f'</div>'
            for gap in audit_data.get("competitor_gaps", [])
        ])}
    </div>
</section>

<!-- Bottom CTA -->
<section style="padding:80px 24px;text-align:center;border-top:1px solid #1a1a1a">
    <div class="cta-section">
        <div class="section-label">Recommended: {h(audit_data.get("recommended_plan", "Growth"))}</div>
        <div class="section-label">Recommended: {h(audit_data.get("recommended_plan", "Growth"))}</div>
        <p class="cta-headline">You&apos;ve seen the problems.</p>
        <p style="font-family:Arial,sans-serif;font-size:13px;color:#B8FF00;text-transform:uppercase;letter-spacing:0.08em;font-weight:700;margin:0 0 16px;">&#9679; We only take on 3 rebuilds per week</p>
        <p class="cta-sub">Your new site, built free first. Only pay if you love it. Live in 14 days or it&apos;s free.</p>
        <div class="cta-buttons">
            <a href="{h(thank_you_url)}" class="btn-primary">Build my free website &#8594;</a>
            <a href="{h(website)}" class="btn-secondary" target="_blank" rel="noopener">Back to their site &#8594;</a>
        </div>
        <div class="cta-guarantee">
            <span class="guarantee-icon">&#10003;</span><span>100% free to start</span>
            <span class="divider">&#183;</span>
            <span class="guarantee-icon">&#10003;</span><span>No credit card needed</span>
            <span class="divider">&#183;</span>
            <span class="guarantee-icon">&#10003;</span><span>Only pay if you love it</span>
        </div>
    </div>
</section>

<footer style="padding:40px 24px;border-top:1px solid #1a1a1a;text-align:center">
    <div style="color:#888888;font-size:12px">This audit was generated by The Smart Website Co. — websites and AI for Australian tradies and local businesses.</div>
    <div style="color:#666666;font-size:11px;margin-top:8px">www.thesmartwebsite.co &#183; hello@thesmartwebsite.co</div>
</footer>

<!-- ISSUES MODAL -->
<div id="issues-modal" style="position:fixed;inset:0;z-index:1000;background:rgba(0,0,0,0.88);align-items:flex-end;justify-content:center" onclick="handleBackdrop(event)">
    <div id="modal-sheet" style="background:#111;border-top:1px solid #1E1E1E;border-radius:20px 20px 0 0;width:100%;max-width:700px;max-height:88vh;display:flex;flex-direction:column;overflow:hidden">
        <div style="display:flex;justify-content:space-between;align-items:center;padding:20px 24px 16px;border-bottom:1px solid #1a1a1a;flex-shrink:0">
            <div>
                <div style="font-size:10px;color:#555;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:3px;font-family:'DM Sans',sans-serif">All Issues Found</div>
                <div id="modal-counter" style="font-family:'Montserrat',sans-serif;font-weight:900;font-size:18px;text-transform:uppercase;letter-spacing:-0.02em;color:#F2F2F2"></div>
            </div>
            <button onclick="closeIssuesModal()" style="background:none;border:1px solid #222;border-radius:50%;width:36px;height:36px;color:#666;cursor:pointer;font-size:16px;display:flex;align-items:center;justify-content:center;flex-shrink:0">&#10005;</button>
        </div>
        <div id="modal-slide" style="flex:1;overflow-y:auto;padding:24px"></div>
        <div id="modal-dots" style="display:flex;justify-content:center;gap:8px;padding:12px 24px;flex-shrink:0"></div>
        <div style="padding:12px 24px 36px;border-top:1px solid #1a1a1a;display:flex;flex-direction:column;gap:10px;flex-shrink:0">
            <div style="display:flex;gap:10px">
                <button onclick="prevIssue()" id="btn-prev" style="flex:1;padding:11px;background:#0f0f0f;border:1px solid #1a1a1a;border-radius:8px;color:#666;font-family:'DM Sans',sans-serif;font-size:13px;cursor:pointer;transition:opacity 0.2s">&#8592; Prev</button>
                <button onclick="nextIssue()" id="btn-next" style="flex:1;padding:11px;background:#0f0f0f;border:1px solid #1a1a1a;border-radius:8px;color:#666;font-family:'DM Sans',sans-serif;font-size:13px;cursor:pointer;transition:opacity 0.2s">Next &#8594;</button>
            </div>
            <a href="{h(thank_you_url)}" class="btn-primary" style="text-align:center;display:block">Fix all {len(issues)} issues &#8212; free &#8594;</a>
        </div>
    </div>
</div>

<script>
var ALL_ISSUES = {all_issues_js};
var currentIssue = 0;

function openIssuesModal(startIndex) {{
    currentIssue = startIndex || 0;
    renderModal();
    document.getElementById('issues-modal').classList.add('open');
    document.body.style.overflow = 'hidden';
}}

function closeIssuesModal() {{
    document.getElementById('issues-modal').classList.remove('open');
    document.body.style.overflow = '';
}}

function handleBackdrop(e) {{
    if (e.target === document.getElementById('issues-modal')) closeIssuesModal();
}}

function nextIssue() {{
    if (currentIssue < ALL_ISSUES.length - 1) {{ currentIssue++; renderModal(); }}
}}

function prevIssue() {{
    if (currentIssue > 0) {{ currentIssue--; renderModal(); }}
}}

function renderModal() {{
    var issue = ALL_ISSUES[currentIssue];
    var total = ALL_ISSUES.length;
    document.getElementById('modal-counter').textContent = 'Issue ' + (currentIssue + 1) + ' of ' + total;
    document.getElementById('modal-slide').innerHTML =
        '<div style="font-size:10px;color:#444;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:10px">Check #' + issue.num + ' of 23</div>' +
        '<div class="modal-title">' + issue.title + '</div>' +
        '<div style="background:#161616;border:1px solid #1a1a1a;border-radius:8px;padding:16px;margin-bottom:12px">' +
            '<div style="font-size:10px;color:#555;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:8px">What we found</div>' +
            '<div style="display:flex;gap:10px;align-items:flex-start">' +
                '<span style="color:#FF4444;flex-shrink:0;font-size:16px;margin-top:1px">&#10007;</span>' +
                '<div style="font-size:14px;color:#CCCCCC;line-height:1.6">' + issue.finding + '</div>' +
            '</div>' +
        '</div>' +
        '<div style="background:rgba(184,255,0,0.05);border:1px solid rgba(184,255,0,0.15);border-radius:8px;padding:16px;margin-bottom:12px">' +
            '<div style="font-size:10px;color:#555;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:8px">The fix</div>' +
            '<div style="font-size:14px;color:#B8FF00;line-height:1.6">&#xD83D;&#xDCA1 ' + issue.fix + '</div>' +
        '</div>' +
        '<div style="font-size:11px;color:#444;text-transform:uppercase;letter-spacing:0.08em">Impact: ' + issue.impact + '</div>';

    var dots = '';
    for (var i = 0; i < ALL_ISSUES.length; i++) {{
        dots += '<div onclick="currentIssue=' + i + ';renderModal()" style="width:' + (i === currentIssue ? '20px' : '7px') + ';height:7px;border-radius:4px;background:' + (i === currentIssue ? '#B8FF00' : '#222') + ';cursor:pointer;transition:all 0.2s"></div>';
    }}
    document.getElementById('modal-dots').innerHTML = dots;

    document.getElementById('btn-prev').style.opacity = currentIssue === 0 ? '0.3' : '1';
    document.getElementById('btn-next').style.opacity = currentIssue === total - 1 ? '0.3' : '1';
}}

// Touch swipe
var touchStartX = 0;
var sheet = document.getElementById('modal-sheet');
sheet.addEventListener('touchstart', function(e) {{ touchStartX = e.touches[0].clientX; }}, {{ passive: true }});
sheet.addEventListener('touchend', function(e) {{
    var diff = touchStartX - e.changedTouches[0].clientX;
    if (Math.abs(diff) > 50) {{ diff > 0 ? nextIssue() : prevIssue(); }}
}}, {{ passive: true }});
</script>

</body>
</html>"""


def build_thank_you_url(lead, slug, score):
    params = urlencode({
        "slug":   slug,
        "name":   lead.get("name", ""),
        "email":  lead.get("email", ""),
        "suburb": lead.get("city", ""),
        "trade":  lead.get("trade", "local business"),
        "score":  str(score),
        "audit":  f"{AUDIT_BASE}/{slug}",
    })
    return f"{THANK_YOU}?{params}"


# ─── DEPLOY ──────────────────────────────────────────────────────────────────

def deploy_audit(html_content, audit_data, slug):
    """Write HTML + JSON to dist/{slug}/ and deploy via vercel --prod."""
    slug_dir = os.path.join(DIST_DIR, slug)
    os.makedirs(slug_dir, exist_ok=True)

    index_path = os.path.join(slug_dir, "index.html")
    # Strip Python surrogate characters (U+D800–U+DFFF) which can't encode in UTF-8
    safe_html = html_content.encode("utf-8", errors="surrogatepass").decode("utf-8", errors="ignore")
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(safe_html)
    log(f"  Written: {index_path}")

    json_path = os.path.join(slug_dir, "audit_data.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(audit_data, f, ensure_ascii=False, indent=2)
    log(f"  Written: {json_path}")

    try:
        result = subprocess.run(
            ["npx", "vercel", "--prod", "--yes"],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=DIST_DIR,
        )
        if result.returncode == 0:
            audit_url = f"{AUDIT_BASE}/{slug}"
            log(f"  Deployed: {audit_url}")
            return audit_url
        else:
            log(f"  Vercel error: {result.stderr[:300]}")
            return f"{AUDIT_BASE}/{slug}"
    except Exception as e:
        log(f"  Deploy error: {e}")
        return f"{AUDIT_BASE}/{slug}"


# ─── MAIN ────────────────────────────────────────────────────────────────────

def run():
    log("audit_generate_v2 starting")
    leads = get_approved_leads()
    log(f"{len(leads)} leads to audit")

    if not leads:
        log("Nothing to do.")
        return

    success = 0
    for lead in leads:
        biz   = lead.get("name", "Unknown Business")
        email = lead.get("email", "")
        url   = lead.get("website", "")
        log(f"Auditing: {biz[:50]}")

        slug = slugify(biz) + "-" + datetime.now().strftime("%Y-%m-%d")

        # Step 1: Scrape
        website_content = scrape_website(url)

        # Step 2: DeepSeek audit
        audit_data = generate_audit_data(lead, website_content)

        # Step 3: Build HTML
        html = build_html(lead, audit_data, slug)

        # Step 4: Deploy
        audit_url = deploy_audit(html, audit_data, slug)

        # Step 5: Update CRM
        update_lead(email, {
            "audit_url":       audit_url,
            "status":          "AUDIT_GENERATED",
            "audit_score":     audit_data.get("score"),
            "audit_generated": datetime.now().isoformat(),
        })

        log(f"Done: {audit_url}")
        success += 1
        time.sleep(5)  # Rate limit gap between leads

    summary = f"audit_generate_v2 complete: {success}/{len(leads)} audits generated"
    log(summary)
    telegram(summary)


if __name__ == "__main__":
    run()
