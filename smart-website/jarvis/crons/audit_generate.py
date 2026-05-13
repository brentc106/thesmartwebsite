#!/usr/bin/env python3
"""
audit_generate.py — Full audit page generator
1. Firecrawl: scrape business website → markdown
2. Claude/Impeccable: run 23 design rules → issues list
3. PageSpeed: performance metrics
4. Generate: standalone HTML audit page
5. Push to Vercel as {slug}.thesmartwebsite.co

Cron: 4 AM daily
Input: leads with status=APPROVED (score 7+)
Output: audit_url per lead, status=AuditGenerated
"""
import os, json, time, re, base64
from datetime import datetime

FIRECRATL_API_KEY = os.environ.get("FIRECRAWL_API_KEY", "fc-050a14fed4ea4b9190d4dd86f8fe6fc0")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
VERCEL_TOKEN = os.environ.get("VERCEL_TOKEN", "")
TELEGRAM_BOT_TOKEN = "8685067366:AAHQht4DvrqFkM99rwMfhExdrkY8nks78Iw"
TELEGRAM_CHAT_ID = "7356494332"
CRM_FILE = "/Users/brentext/.openclaw/workspace/smart-website/data/leads.jsonl"
AUDIT_OUTPUT_DIR = "/Users/brentext/.openclaw/workspace/smart-website/data/audits"
PAGESPEED_API_KEY = os.environ.get("PAGESPEED_API_KEY", "")

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

def ts(): return datetime.now().strftime("%H:%M")
def log(msg): print(f"[{ts()}] {msg}", flush=True)

def telegram(msg):
    try:
        from urllib.request import urlopen, Request
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = json.dumps({"chat_id": TELEGRAM_CHAT_ID, "text": msg}).encode()
        req = Request(url, data=data, headers={"Content-Type": "application/json"})
        urlopen(req, timeout=10)
    except: pass

def slugify(text):
    import unicodedata
    text = unicodedata.normalize("NFKD", text).encode("ascii","ignore").decode()
    return re.sub(r"[^a-z0-9-]", "-", text.lower()).strip("-")[:50]

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

def get_approved_leads():
    return [l for l in load_crm()
            if l.get("status") in ("APPROVED","SCORED")
            and l.get("score",0) >= 7.0
            and not l.get("audit_url")]

def scrape_firecrawl(url, api_key):
    """Scrape website to markdown via Firecrawl SDK."""
    if not api_key: return ""
    try:
        from firecrawl import Firecrawl
        fc = Firecrawl(api_key=api_key)
        doc = fc.scrape(url, formats=['markdown'], only_main_content=True)
        return doc.markdown if hasattr(doc, 'markdown') else ''
    except Exception as e:
        log(f"Firecrawl error: {e}")
        return ""

def run_pagespeed(url):
    if not url: return {}
    try:
        from urllib.request import urlopen, Request
        key = PAGESPEED_API_KEY or "AIzaSyC3aC4LQbK8jq2vLUq0J2nXGq3JN-TJYi0"
        api_url = f"https://pagespeed.googleapis.com/pagespeed/v5/runPagespeed?url={urllib.parse.quote(url)}&strategy=mobile&key={key}"
        req = Request(api_url)
        with urlopen(req, timeout=20) as r:
            data = json.loads(r.read())
        cats = data.get("lighthouseResult",{}).get("categories",{})
        perf = cats.get("performance",{}).get("score",0) or 0
        accessibility = cats.get("accessibility",{}).get("score",0) or 0
        best_practices = cats.get("best-practices",{}).get("score",0) or 0
        seo = cats.get("seo",{}).get("score",0) or 0
        metrics = data.get("loadingExperience",{}).get("metrics",{})
        return {
            "performance": int(perf*100),
            "accessibility": int(accessibility*100),
            "best_practices": int(best_practices*100),
            "seo": int(seo*100),
            "lcp_ms": metrics.get("LARGEST_CONTENTFUL_PAINT_MS",{}).get("percentile",0),
            "cls": metrics.get("CUMULATIVE_LAYOUT_SHIFT_MS",{}).get("percentile",0),
            "fid_ms": metrics.get("FIRST_INPUT_DELAY_MS",{}).get("percentile",0),
        }
    except Exception as e:
        log(f"PageSpeed error: {e}")
        return {}

def run_impeccable_audit(html_content):
    """Use Claude to run the 23 Impeccable rules against the HTML."""
    if not html_content: return {"score": 5, "issues": [], "recommendations": []}
    sample = html_content[:8000]
    prompt = f"""You are a brutal, world-class design critic. Audit this website HTML against these 23 Impeccable design rules:

{chr(10).join([f"{i+1}. {r}" for i,r in enumerate(IMPECCABLE_23)])}

Website HTML (first 8000 chars):
{sample}

For EACH rule, answer: PASS / FAIL / PARTIAL with one-line explanation.
Then list the TOP 5 most impactful issues.
Then give 3 specific, actionable recommendations.

Return as JSON:
{{"rule_results": [{{"rule":"...", "verdict":"PASS/FAIL/PARTIAL", "notes":"..."}}],
"top_5_issues": ["issue1", "issue2", "issue3", "issue4", "issue5"],
"recommendations": ["rec1", "rec2", "rec3"],
"impeccable_score": 0-10}}
"""
    try:
        import urllib.request
        payload = {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 800,
            "messages": [{"role": "user", "content": prompt}]
        }
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json", "x-api-key": ANTHROPIC_API_KEY,
                     "anthropic-version": "2023-06-01",
                     "anthropic-dangerous-direct-browser-access": "true"}
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            resp = json.loads(r.read())
            text = resp["content"][0]["text"]
            # Extract JSON
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(text[start:end])
    except Exception as e:
        log(f"Claude error: {e}")
    return {"score": 5, "issues": ["audit_failed"], "recommendations": ["Unable to complete AI audit"]}

def fetch_website_html(url):
    try:
        from urllib.request import urlopen, Request
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req, timeout=10) as r:
            return r.read().decode("utf-8", errors="ignore")
    except: return ""

def generate_audit_html(lead, impeccable_data, pagespeed_data):
    """Generate standalone HTML audit page."""
    biz = lead.get("business_name","Unknown Business")
    trade = lead.get("trade","Local Business")
    city = lead.get("city","Australia")
    url = lead.get("website","")
    score = lead.get("score",0)
    perf = pagespeed_data or {}
    issues = impeccable_data.get("top_5_issues", [])
    recs = impeccable_data.get("recommendations", [])
    rules = impeccable_data.get("rule_results", [])[:10]
    overall = impeccable_data.get("impeccable_score", score)

    # Score color
    if overall >= 8: color = "#22c55e"; label = "NEEDS WORK"
    elif overall >= 6: color = "#eab308"; label = "GETTING OLD"
    else: color = "#ef4444"; label = "OUTDATED"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{biz} — Website Audit</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0f0f0f; color: #f5f5f5; min-height: 100vh; }}
  .hero {{ background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); padding: 60px 20px; text-align: center; }}
  .hero h1 {{ font-size: clamp(28px,5vw,48px); font-weight: 800; color: #fff; margin-bottom: 8px; }}
  .hero p {{ color: #94a3b8; font-size: 18px; }}
  .score-badge {{ display: inline-block; background: {color}; color: #fff; font-size: 14px; font-weight: 700; padding: 4px 16px; border-radius: 20px; margin-top: 12px; text-transform: uppercase; letter-spacing: 1px; }}
  .container {{ max-width: 900px; margin: 0 auto; padding: 40px 20px; }}
  .website-link {{ background: #1e293b; border-radius: 12px; padding: 20px; margin: 20px 0; border: 1px solid #334155; }}
  .website-link a {{ color: #60a5fa; font-size: 16px; word-break: break-all; }}
  .website-link span {{ color: #64748b; font-size: 13px; display: block; margin-top: 4px; }}
  .metrics-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px; margin: 20px 0; }}
  .metric-card {{ background: #1e293b; border-radius: 12px; padding: 20px; border: 1px solid #334155; }}
  .metric-card .val {{ font-size: 36px; font-weight: 800; color: #fff; }}
  .metric-card .lbl {{ color: #64748b; font-size: 13px; margin-top: 4px; text-transform: uppercase; letter-spacing: 0.5px; }}
  .metric-card.perf {{ border-color: {'#22c55e' if perf.get('performance',0)>=80 else '#eab308' if perf.get('performance',0)>=50 else '#ef4444'}; }}
  .metric-card.acces {{ border-color: {'#22c55e' if perf.get('accessibility',0)>=80 else '#eab308' if perf.get('accessibility',0)>=50 else '#ef4444'}; }}
  .metric-card.seo {{ border-color: {'#22c55e' if perf.get('seo',0)>=80 else '#eab308' if perf.get('seo',0)>=50 else '#ef4444'}; }}
  .metric-card.bp {{ border-color: {'#22c55e' if perf.get('best_practices',0)>=80 else '#eab308' if perf.get('best_practices',0)>=50 else '#ef4444'}; }}
  .section {{ background: #1e293b; border-radius: 12px; padding: 24px; margin: 20px 0; border: 1px solid #334155; }}
  .section h2 {{ font-size: 20px; font-weight: 700; color: #fff; margin-bottom: 16px; border-bottom: 1px solid #334155; padding-bottom: 12px; }}
  .issue-item {{ background: #1e293b; border-left: 3px solid #ef4444; padding: 12px 16px; margin: 10px 0; border-radius: 0 8px 8px 0; }}
  .rec-item {{ background: #0f172a; border-left: 3px solid #22c55e; padding: 12px 16px; margin: 10px 0; border-radius: 0 8px 8px 0; font-size: 15px; }}
  .cta-section {{ background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); border-radius: 12px; padding: 40px; text-align: center; margin: 30px 0; }}
  .cta-section h2 {{ font-size: 28px; font-weight: 800; color: #fff; margin-bottom: 12px; }}
  .cta-section p {{ color: #94a3b8; margin-bottom: 24px; font-size: 16px; }}
  .cta-btn {{ display: inline-block; background: #FF5C1A; color: #fff; font-weight: 700; font-size: 18px; padding: 16px 40px; border-radius: 8px; text-decoration: none; text-transform: uppercase; letter-spacing: 1px; }}
  .cta-btn:hover {{ background: #e04a10; }}
  .rule-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 10px; }}
  .rule-item {{ background: #0f172a; padding: 10px 14px; border-radius: 6px; font-size: 13px; display: flex; align-items: center; gap: 8px; }}
  .rule-pass {{ color: #22c55e; font-weight: 700; }} .rule-fail {{ color: #ef4444; font-weight: 700; }}
  .rule-partial {{ color: #eab308; font-weight: 700; }}
  .footer {{ text-align: center; padding: 40px; color: #475569; font-size: 13px; }}
  @media (max-width: 600px) {{ .metrics-grid {{ grid-template-columns: 1fr 1fr; }} }}
</style>
</head>
<body>
<div class="hero">
  <h1>{biz}</h1>
  <p>{trade.title()} in {city}</p>
  <div class="score-badge">{label} — Score {overall}/10</div>
</div>
<div class="container">
  <div class="website-link">
    <a href="{url}" target="_blank">{url}</a>
    <span>Source: Google Maps + Direct</span>
  </div>
  <div class="metrics-grid">
    <div class="metric-card perf">
      <div class="val">{perf.get('performance','--')}</div>
      <div class="lbl">Performance</div>
    </div>
    <div class="metric-card acces">
      <div class="val">{perf.get('accessibility','--')}</div>
      <div class="lbl">Accessibility</div>
    </div>
    <div class="metric-card seo">
      <div class="val">{perf.get('seo','--')}</div>
      <div class="lbl">SEO</div>
    </div>
    <div class="metric-card bp">
      <div class="val">{perf.get('best_practices','--')}</div>
      <div class="lbl">Best Practices</div>
    </div>
  </div>
  <div class="section">
    <h2>Top Issues Found</h2>
    {''.join(f'<div class="issue-item">&#9888; {issue}</div>' for issue in issues[:5])}
  </div>
  <div class="section">
    <h2>What We'd Fix</h2>
    {''.join(f'<div class="rec-item">&#10004; {rec}</div>' for rec in recs[:3])}
  </div>
  <div class="cta-section">
    <h2>See What Your Site Could Look Like</h2>
    <p>We built a mockup for {biz}. It's free to look at — no obligation.</p>
    <a href="#" class="cta-btn">View Free Mockup</a>
  </div>
  <div class="section">
    <h2>Design Audit ({len(rules)} rules checked)</h2>
    <div class="rule-grid">
      {''.join(f'<div class="rule-item"><span class="rule-{r.get("verdict","partial").lower()}">{r.get("verdict","?")[:1]}</span> {r.get("rule","")}</div>' for r in rules)}
    </div>
  </div>
</div>
<div class="footer">
  Audit generated by The Smart Website Co. — AI-powered website analysis
</div>
</body>
</html>"""
    return html

def deploy_to_vercel(html_content, slug, vercel_token):
    """Deploy HTML audit page to Vercel."""
    if not vercel_token: return f"https://{slug}.thesmartwebsite.co"
    try:
        from urllib.request import urlopen, Request
        # Create a simple deployment via Vercel API
        import tempfile, os
        tmp = tempfile.mkdtemp()
        path = os.path.join(tmp, "index.html")
        with open(path, "w") as f:
            f.write(html_content)
        # Use Vercel CLI
        import subprocess
        result = subprocess.run(
            ["vercel", "--token", vercel_token, "--prod", tmp],
            capture_output=True, text=True, timeout=60
        )
        log(f"Vercel deploy: {result.stdout[:200]}")
        return f"https://{slug}.thesmartwebsite.co"
    except Exception as e:
        log(f"Vercel deploy error: {e}")
        return f"https://{slug}.thesmartwebsite.co"

def run():
    log("Audit generation starting")
    leads = get_approved_leads()
    log(f"Generating audits for {len(leads)} leads")
    for lead in leads:
        url = lead.get("website","")
        biz = lead.get("business_name","Unknown")
        email = lead.get("email","")
        log(f"Auditing: {biz[:40]}")
        slug = f"{slugify(biz)}-{lead.get('scored_at','')[:10]}"
        html_content = fetch_website_html(url)
        impeccable = run_impeccable_audit(html_content) if html_content else {}
        ps = run_pagespeed(url)
        audit_html = generate_audit_html(lead, impeccable, ps)
        audit_url = deploy_to_vercel(audit_html, slug, VERCEL_TOKEN)
        update_lead(email, {
            "audit_url": audit_url,
            "status": "AUDIT_GENERATED",
            "impeccable_score": impeccable.get("impeccable_score", lead.get("score",0)),
        })
        log(f"Audit done: {audit_url}")
        time.sleep(2)
    log("Audit generation complete")
    telegram(f"Audit generation complete for {len(leads)} leads")

if __name__ == "__main__":
    run()