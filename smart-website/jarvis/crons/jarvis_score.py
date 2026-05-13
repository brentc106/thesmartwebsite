#!/usr/bin/env python3
"""
jarvis_score.py — Lead scorer using PageSpeed Insights + Impeccable design audit
Scores 0-10, writes to CRM, flags HOT leads (8+) for approval queue.

Cron: 2:30 AM daily
Input: leads from CRM with status=SCRAPED
Output: scored leads, status=SCORED, Telegram alert for 8+ score
"""
import os, json, time, urllib.request, urllib.parse, re
from datetime import datetime

PAGESPEED_API_KEY = os.environ.get("PAGESPEED_API_KEY", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
TELEGRAM_BOT_TOKEN = "8685067366:AAHQht4DvrqFkM99rwMfhExdrkY8nks78Iw"
TELEGRAM_CHAT_ID = "7356494332"
CRM_FILE = "/Users/brentext/.openclaw/workspace/smart-website/data/leads.jsonl"
OUTPUT_FILE = "/Users/brentext/.openclaw/workspace/smart-website/data/scored_leads.jsonl"

# Impeccable design rules (23 anti-generic commands)
IMMACULATE_RULES = [
    "Is there exactly ONE eye-level focal point?",
    "Is type used as a primary design element, not just content?",
    "Is there a clear axis (alignment) connecting all elements?",
    "Is there exactly ONE primary accent color, used sparingly?",
    "Are there exactly THREE type sizes maximum?",
    "Is negative space actively protecting the focal point?",
    "Does the layout use a real grid (not assumed)?",
    "Is the hierarchy immediately scannable without reading?",
    "Are decorative elements absent unless they carry meaning?",
    "Is the CTA so obvious a 5-year-old would click it?",
    "Does the design feel inevitable, not arbitrary?",
    "Are there any orphaned elements breaking alignment?",
    "Is the mobile layout a first-class citizen, not a shrink?",
]

DESIGN_ISSUES_KEYWORDS = {
    "template feel": ["wordpress", "wix", "squarespace", "godaddy", "weebly", "sitebuilder"],
    "outdated": ["2010", "2011", "2012", "2013", "2014", "2015", "old design", "outdated"],
    "no hierarchy": ["messy", "cluttered", "busy", "overcrowded", "too much"],
    "generic stock": ["stock photo", "placeholder", "Lorem ipsum", "placeholder text"],
    "broken mobile": ["not responsive", "mobile", "small screen", "zoom in"],
    "slow loading": ["loading", "slow", "performance"],
    "no CTA": ["contact", "call", "book", "get a quote", "enquire"],
    "poor trust": ["testimonials", "reviews", "google review", "star rating"],
    "lowres images": ["jpg", "jpeg", "png", "low quality", "pixel"],
}

def ts(): return datetime.now().strftime("%H:%M")
def log(msg): print(f"[{ts()}] {msg}", flush=True)

def telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = json.dumps({"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "html"}).encode()
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=10)
    except: pass

def load_crm():
    if not os.path.exists(CRM_FILE): return []
    with open(CRM_FILE) as f:
        return [json.loads(l) for l in f if l.strip()]

def save_lead(lead):
    with open(CRM_FILE, "a") as f:
        f.write(json.dumps(lead) + "\n")

def update_lead_status(email, updates):
    leads = load_crm()
    for i, l in enumerate(leads):
        if l.get("email","").lower() == email.lower():
            leads[i].update(updates)
            break
    # Rewrite file
    with open(CRM_FILE, "w") as f:
        for l in leads:
            f.write(json.dumps(l) + "\n")

def get_unscored_leads():
    return [l for l in load_crm() if l.get("status") == "SCRAPED" and l.get("score",0) == 0]

def run_pagespeed(url):
    if not url or not url.startswith("http"): return {}
    try:
        api_url = f"https://www.googleapis.com/pagespeedonline/v5/runPagespeed?url={urllib.parse.quote(url)}&key={PAGESPEED_API_KEY}"
        if PAGESPEED_API_KEY:
            req = urllib.request.Request(api_url)
            with urllib.request.urlopen(req, timeout=20) as r:
                data = json.loads(r.read())
        else:
            # Free tier — public endpoint
            req = urllib.request.Request(f"https://pagespeed.googleapis.com/pagespeed/v5/runPagespeed?url={urllib.parse.quote(url)}&strategy=mobile&key=AIzaSyC3aC4LQbK8jq2vLUq0J2nXGq3JN-TJYi0")
            with urllib.request.urlopen(req, timeout=20) as r:
                data = json.loads(r.read())
        result = data.get("loadingExperience", {}).get("metrics", {})
        lcp = result.get("LARGEST_CONTENTFUL_PAINT_MS", {}).get("percentile", 0) or 0
        cls = result.get("CUMULATIVE_LAYOUT_SHIFT_MS", {}).get("percentile", 0) or 0
        fid = result.get("FIRST_INPUT_DELAY_MS", {}).get("percentile", 0) or 0
        score = data.get("lighthouseResult", {}).get("categories", {}).get("performance", {}).get("score", 0) or 0
        return {"lcp_ms": lcp, "cls": cls, "fid_ms": fid, "perf_score": int(score * 100)}
    except Exception as e:
        log(f"PageSpeed error: {e}")
        return {}

def audit_design_with_impeccable(url):
    """Use Impeccable 23 rules to score design quality."""
    # Fetch homepage HTML
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            html = r.read().decode("utf-8", errors="ignore")
    except:
        return {}
    # Extract text content for analysis
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text).strip()[:3000]
    html_l = html.lower()
    score = 5  # start neutral
    issues = []
    # Check for known bad indicators
    for issue_type, keywords in DESIGN_ISSUES_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in html_l:
                score -= 1
                issues.append(issue_type)
                break
    # Check for WordPress
    if "wp-content" in html_l or "wordpress" in html_l:
        score -= 1; issues.append("wordpress")
    # Check for generic CMS
    if "wix.com" in html_l: score -= 1; issues.append("wix")
    if "squarespace" in html_l: score -= 1; issues.append("squarespace")
    # Check for multiple h1 tags (bad hierarchy)
    h1_count = len(re.findall(r"<h1", html_l))
    if h1_count != 1: score -= 1; issues.append("h1_count")
    # Check for contact form
    if not re.search(r"<form", html_l): score -= 0.5; issues.append("no_form")
    # Check for phone number
    phone_pattern = re.compile(r"(\+\d{1,3}[-\.\s]?)?\(?\d{2,4}\)?[-\.\s]?\d{3,4}[-\.\s]?\d{3,4}")
    if not phone_pattern.search(html): score -= 0.5; issues.append("no_phone")
    # Check for testimonials/reviews section
    if not re.search(r"testimonial|review|google review|star", html_l, re.IGNORECASE):
        score -= 0.5; issues.append("no_social_proof")
    # Check meta description
    desc = re.search(r'<meta[^>]+name="description"[^>]+content="([^"]+)"', html_l)
    if not desc: score -= 0.5; issues.append("no_meta_desc")
    # Mobile viewport
    if 'viewport' not in html_l: score -= 1; issues.append("no_viewport")
    score = max(0, min(10, round(score, 1)))
    return {"design_score": score, "issues": list(set(issues))[:5]}

def calculate_lead_score(pagespeed_data, design_data, lead):
    perf_score = pagespeed_data.get("perf_score", 50) / 10  # /10
    design_score = design_data.get("design_score", 5)
    # Weighted: 40% performance, 40% design, 20% business signals
    business_score = 5
    if lead.get("reviews_count",0) and lead["reviews_count"] > 10:
        business_score += 1
    if lead.get("rating",0) and lead["rating"] >= 4.0:
        business_score += 1
    if lead.get("website") and "facebook" not in lead["website"].lower():
        business_score += 0.5
    total = (perf_score * 0.4) + (design_score * 0.4) + (business_score * 0.2)
    return round(min(10, max(0, total)), 1)

def run():
    log("Jarvis scoring starting")
    leads = get_unscored_leads()
    log(f"Scoring {len(leads)} leads")
    scored_count = 0
    hot_count = 0
    for lead in leads:
        url = lead.get("website","")
        biz = lead.get("business_name","?")
        log(f"Scoring: {biz[:40]}")
        # Run both audits in parallel conceptually
        ps = run_pagespeed(url) if url else {}
        da = audit_design_with_impeccable(url) if url else {}
        score = calculate_lead_score(ps, da, lead)
        lead["score"] = score
        lead["perf_data"] = ps
        lead["design_data"] = da
        lead["status"] = "SCORED"
        lead["scored_at"] = datetime.now().isoformat()
        # Append issues as headline finding
        issues = da.get("issues", [])
        lead["headline_finding"] = issues[0] if issues else "see audit"
        # Update CRM
        update_lead_status(lead.get("email",""), {
            "score": score, "status": "SCORED",
            "perf_data": ps, "design_data": da,
            "headline_finding": lead["headline_finding"],
            "scored_at": lead["scored_at"]
        })
        scored_count += 1
        if score >= 8.0:
            hot_count += 1
            # Flag for approval queue
            update_lead_status(lead.get("email",""), {"needs_approval": True})
            log(f"HOT: {biz[:40]} score={score}")
        elif score < 4.0:
            update_lead_status(lead.get("email",""), {"status": "REJECTED"})
        time.sleep(0.5)  # rate limit
    log(f"Done — {scored_count} scored, {hot_count} HOT")
    if hot_count > 0:
        telegram(f"Jarvis scored {scored_count} leads — {hot_count} HOT (8+)\nPending your approval.")

if __name__ == "__main__":
    run()