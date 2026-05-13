#!/usr/bin/env python3
"""
email_templates.py — Transactional email templates for Smart Website Co.
Two templates:
  1. ack_email()  — client acknowledgement on form submit
  2. audit_delivery_email() — branded audit report delivery

Used by: inbound_audit_cron.py (delivery) and audit_generate_v2.py (delivery)
"""
from datetime import datetime


def ack_email(lead: dict, process_after: datetime) -> tuple[str, str]:
    """
    Client acknowledgement email — sent immediately on form submission.
    Returns (subject, html_body).
    """
    name = lead.get("name", "")
    business_name = lead.get("business_name", lead.get("businessName", ""))
    email_addr = lead.get("email", "")
    suburb = lead.get("suburb", "")
    phone = lead.get("phone", "")

    subject = f"Your free audit for {business_name} is confirmed"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Your audit is in the queue</title>
</head>
<body style="margin:0;padding:0;background:#EFEFEF;font-family:Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#EFEFEF;padding:40px 16px;">
<tr><td align="center">
<table width="100%" cellpadding="0" cellspacing="0" style="max-width:580px;">

<!-- Header -->
<tr><td style="background:#080808;padding:20px 32px;">
<table width="100%" cellpadding="0" cellspacing="0">
<tr><td>
<span style="font-family:Arial,sans-serif;font-weight:900;font-size:14px;text-transform:uppercase;letter-spacing:-0.02em;color:#FFFFFF;">THE<span style="color:#B8FF00;">SMART</span>WEBSITE.CO</span>
</td><td align="right">
<span style="font-family:Arial,sans-serif;font-weight:700;font-size:10px;text-transform:uppercase;letter-spacing:0.12em;color:#555;">Free Website Audit</span>
</td></tr>
</table>
</td></tr>

<!-- Signal bar -->
<tr><td style="background:#B8FF00;height:3px;font-size:3px;line-height:3px;">&nbsp;</td></tr>

<!-- Status badge -->
<tr><td style="background:#0F0F0F;padding:10px 32px;">
<table cellpadding="0" cellspacing="0"><tr>
<td style="width:8px;height:8px;background:#B8FF00;border-radius:50%;"></td>
<td style="padding-left:10px;font-family:Arial,sans-serif;font-weight:700;font-size:10px;text-transform:uppercase;letter-spacing:0.12em;color:#B8FF00;">Audit queued — processing now</td>
</tr></table>
</td></tr>

<!-- Body -->
<tr><td style="background:#FFFFFF;padding:44px 32px 36px;">
<p style="font-family:Arial,sans-serif;font-weight:700;font-size:11px;text-transform:uppercase;letter-spacing:0.12em;color:#999;margin:0 0 20px;">For: {business_name}</p>
<h1 style="font-family:Arial,sans-serif;font-weight:900;font-size:30px;color:#080808;margin:0 0 20px;line-height:1.2;text-transform:uppercase;letter-spacing:-0.02em;">We're on it, {name.split(' ')[0]}.</h1>
<p style="font-family:Arial,sans-serif;font-size:15px;color:#444;line-height:1.75;margin:0 0 12px;">Your audit for <strong style="color:#080808;">{business_name}</strong> is being processed now.</p>
<p style="font-family:Arial,sans-serif;font-size:15px;color:#444;line-height:1.75;margin:0 0 32px;">We scan your website, benchmark you against local competitors, and calculate exactly what it's costing you each month.</p>

<!-- What's included -->
<table width="100%" cellpadding="0" cellspacing="0" style="background:#F7F7F7;border-radius:8px;border-left:3px solid #B8FF00;margin-bottom:36px;">
<tr><td style="padding:20px 24px;">
<p style="font-family:Arial,sans-serif;font-weight:700;font-size:11px;text-transform:uppercase;letter-spacing:0.12em;color:#999;margin:0 0 14px;">Your audit covers</p>
{"".join(f"""
<p style="font-family:Arial,sans-serif;font-size:14px;color:#333;line-height:1.6;margin:0 0 10px;"><span style="color:#B8FF00;font-weight:900;">&#10003;</span>&nbsp;&nbsp;{item}</p>"""
    for item in [
        "23-point design and conversion review",
        "Google competitor benchmarking",
        "PageSpeed and mobile analysis",
        "Revenue opportunity calculation",
        "Your top 5 specific fixes",
    ])}
</p>
</td></tr>
</table>

<p style="font-family:Arial,sans-serif;font-size:15px;color:#444;line-height:1.75;margin:0 0 8px;"><strong style="color:#080808;">Expect your full report within 2 hours.</strong></p>
<p style="font-family:Arial,sans-serif;font-size:15px;color:#444;line-height:1.75;margin:0;">We'll send your personalised audit report to <strong style="color:#080808;">{email_addr}</strong> as soon as it's ready.</p>
</td></tr>

<!-- Footer -->
<tr><td style="background:#F4F4F4;padding:20px 32px;border-radius:0 0 12px 12px;">
<p style="font-family:Arial,sans-serif;font-size:12px;color:#999;margin:0;">Questions? Reply to this email or contact <a href="mailto:hello@thesmartwebsite.co" style="color:#B8FF00;">hello@thesmartwebsite.co</a></p>
</td></tr>

</table></td></tr></table>
</body>
</html>"""

    return subject, html


def audit_delivery_email(lead: dict, audit_data: dict, audit_url: str) -> tuple[str, str]:
    """
    Audit delivery email — sent when the audit page is ready.
    Contains the score, top 3 issues, and a CTA button.
    Returns (subject, html_body).
    """
    name = lead.get("name", "")
    business_name = lead.get("business_name", lead.get("businessName", ""))
    email_addr = lead.get("email", "")
    score = audit_data.get("score", 0)
    issues = audit_data.get("issues", [])[:3]

    # Severity label
    if score >= 26:
        severity = "NEEDS WORK"
        severity_color = "#F59E0B"
    elif score >= 21:
        severity = "GETTING OLD"
        severity_color = "#F59E0B"
    else:
        severity = "CRITICAL"
        severity_color = "#EF4444"

    # Score label
    score_label = f"{score}/30"

    subject = f"Your free audit for {business_name} is ready"

    # Build issues list HTML
    issues_html = "".join(
        f"""<tr>
        <td style="padding:16px 0;border-bottom:1px solid #EEE;font-family:Arial,sans-serif;font-size:14px;color:#333;line-height:1.5;">
          <span style="color:{severity_color};font-weight:700;">{i+1}.</span>&nbsp;{issue.get('title', '')}
        </td>
        </tr>"""
        for i, issue in enumerate(issues)
    )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Your free website audit is ready</title>
</head>
<body style="margin:0;padding:0;background:#EFEFEF;font-family:Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#EFEFEF;padding:40px 16px;">
<tr><td align="center">
<table width="100%" cellpadding="0" cellspacing="0" style="max-width:580px;">

<!-- Header -->
<tr><td style="background:#080808;padding:20px 32px;">
<table width="100%" cellpadding="0" cellspacing="0">
<tr><td>
<span style="font-family:Arial,sans-serif;font-weight:900;font-size:14px;text-transform:uppercase;letter-spacing:-0.02em;color:#FFFFFF;">THE<span style="color:#B8FF00;">SMART</span>WEBSITE.CO</span>
</td><td align="right">
<span style="font-family:Arial,sans-serif;font-weight:700;font-size:10px;text-transform:uppercase;letter-spacing:0.12em;color:#555;">Free Audit Results</span>
</td></tr>
</table>
</td></tr>

<!-- Signal bar -->
<tr><td style="background:#B8FF00;height:3px;font-size:3px;line-height:3px;">&nbsp;</td></tr>

<!-- Body -->
<tr><td style="background:#FFFFFF;padding:44px 32px 36px;">
<p style="font-family:Arial,sans-serif;font-weight:700;font-size:11px;text-transform:uppercase;letter-spacing:0.12em;color:#999;margin:0 0 16px;">For: {business_name}</p>

<h1 style="font-family:Arial,sans-serif;font-weight:900;font-size:28px;color:#080808;margin:0 0 6px;text-transform:uppercase;letter-spacing:-0.02em;line-height:1.2;">Your audit is ready, {name.split(' ')[0]}.</h1>
<p style="font-family:Arial,sans-serif;font-size:15px;color:#666;margin:0 0 32px;">Here's what we found when we reviewed your website — and what it's costing you.</p>

<!-- Score box -->
<table width="100%" cellpadding="0" cellspacing="0" style="background:#0A0A0A;border-radius:12px;margin-bottom:32px;">
<tr><td style="padding:28px 32px;">
<table cellpadding="0" cellspacing="0" width="100%">
<tr>
<td style="vertical-align:middle;">
<span style="font-family:Arial,sans-serif;font-weight:900;font-size:56px;color:{severity_color};line-height:1;">{score}</span>
<span style="font-family:Arial,sans-serif;font-size:18px;color:#666;margin-left:4px;">/30</span>
</td>
<td style="padding-left:24px;">
<span style="font-family:Arial,sans-serif;font-weight:700;font-size:10px;text-transform:uppercase;letter-spacing:0.12em;color:{severity_color};background:rgba(255,255,255,0.06);padding:4px 12px;border-radius:20px;">{severity}</span>
<p style="font-family:Arial,sans-serif;font-size:13px;color:#666;margin:8px 0 0;">Website health score</p>
</td>
</tr>
</table>
</td></tr>
</table>

<!-- Top 3 issues -->
<h2 style="font-family:Arial,sans-serif;font-weight:900;font-size:14px;text-transform:uppercase;letter-spacing:0.08em;color:#080808;margin:0 0 4px;">Top 3 issues found</h2>
<table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:32px;">
{issues_html}
</table>

<!-- CTA -->
<div style="text-align:center;margin-bottom:28px;">
<a href="{audit_url}" style="display:inline-block;background:#B8FF00;color:#080808;font-family:Arial,sans-serif;font-weight:700;font-size:15px;padding:16px 40px;border-radius:8px;text-decoration:none;text-transform:uppercase;letter-spacing:0.05em;">See full audit with all 5 issues &#8594;</a>
</div>

<p style="font-family:Arial,sans-serif;font-size:13px;color:#999;text-align:center;margin:0;">Built free first. Only pay if you love it.</p>
</td></tr>

<!-- Footer -->
<tr><td style="background:#F4F4F4;padding:20px 32px;border-radius:0 0 12px 12px;">
<p style="font-family:Arial,sans-serif;font-size:12px;color:#999;margin:0;">Questions? Reply to this email or contact <a href="mailto:hello@thesmartwebsite.co" style="color:#B8FF00;">hello@thesmartwebsite.co</a></p>
</td></tr>

</table></td></tr></table>
</body>
</html>"""

    return subject, html