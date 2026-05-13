import { NextRequest, NextResponse } from 'next/server';

const MAILGUN_API_KEY = process.env.MAILGUN_API_KEY || '';
const MAILGUN_DOMAIN = process.env.MAILGUN_DOMAIN || '';

function validateField(field: string | null | undefined, label: string): string {
  if (!field || typeof field !== 'string' || field.trim().length === 0) {
    throw new Error(`${label} is required`);
  }
  return field.trim();
}

function validatePhone(phone: string | null | undefined): string {
  if (!phone || typeof phone !== 'string' || phone.trim().length === 0) {
    throw new Error('Mobile number is required');
  }
  const cleaned = phone.replace(/\s|-|\(|\)/g, '');
  const auPhoneRegex = /^(\+?61[42]\d{8,9}|0[42]\d{8,9}|1300\d{6}|1800\d{6})$/;
  if (!auPhoneRegex.test(cleaned)) {
    throw new Error('Please enter a valid Australian mobile number');
  }
  return cleaned;
}

function validateUrl(url: string | null | undefined): string | null {
  if (!url || typeof url !== 'string' || url.trim().length === 0) {
    return null;
  }
  const trimmed = url.trim();
  if (!trimmed.startsWith('http')) {
    return 'https://' + trimmed;
  }
  return trimmed;
}

function formatPhoneForDisplay(phone: string): string {
  const cleaned = phone.replace(/\D/g, '');
  if (cleaned.startsWith('61')) {
    return '+' + cleaned.slice(0, 2) + ' ' + cleaned.slice(2, 4) + ' ' + cleaned.slice(4);
  }
  return phone;
}

function ackEmailHTML(name: string, businessName: string): string {
  return `<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>Your audit is in the queue</title></head><body style="margin:0;padding:0;background:#EFEFEF;font-family:Arial,sans-serif;"><table width="100%" cellpadding="0" cellspacing="0" style="background:#EFEFEF;padding:40px 16px;"><tr><td align="center"><table width="100%" cellpadding="0" cellspacing="0" style="max-width:580px;"><tr><td style="background:#080808;padding:24px 32px;border-radius:12px 12px 0 0;"><table width="100%" cellpadding="0" cellspacing="0"><tr><td><span style="font-family:Arial,sans-serif;font-weight:900;font-size:15px;text-transform:uppercase;letter-spacing:-0.02em;color:#FFFFFF;">THE<span style="color:#B8FF00;">SMART</span>WEBSITE.CO</span></td><td align="right"><span style="font-family:Arial,sans-serif;font-weight:700;font-size:10px;text-transform:uppercase;letter-spacing:0.12em;color:#444;">Free Audit</span></td></tr></table></td></tr><tr><td style="background:#B8FF00;height:3px;line-height:3px;font-size:3px;">&nbsp;</td></tr><tr><td style="background:#0F0F0F;padding:14px 32px;"><table cellpadding="0" cellspacing="0"><tr><td style="width:8px;height:8px;background:#B8FF00;border-radius:50%;vertical-align:middle;"></td><td style="padding-left:10px;font-family:Arial,sans-serif;font-weight:700;font-size:11px;text-transform:uppercase;letter-spacing:0.12em;color:#B8FF00;vertical-align:middle;">Audit queued — processing now</td></tr></table></td></tr><tr><td style="background:#FFFFFF;padding:44px 32px 36px;"><p style="font-family:Arial,sans-serif;font-weight:700;font-size:11px;text-transform:uppercase;letter-spacing:0.12em;color:#999;margin:0 0 20px;">For: ${businessName}</p><h1 style="font-family:Arial,sans-serif;font-weight:900;font-size:32px;color:#080808;margin:0 0 20px;line-height:1.15;text-transform:uppercase;letter-spacing:-0.02em;">We're on it, ${name}.</h1><p style="font-family:Arial,sans-serif;font-size:16px;color:#444;line-height:1.75;margin:0 0 12px;">Your audit for <strong style="color:#080808;">${businessName}</strong> is being put together now.</p><p style="font-family:Arial,sans-serif;font-size:16px;color:#444;line-height:1.75;margin:0 0 32px;">We're scanning your website, benchmarking you against local competitors, and calculating exactly what it's costing you each month. Expect your full report within <strong style="color:#080808;">2 hours</strong>.</p><table width="100%" cellpadding="0" cellspacing="0" style="background:#F7F7F7;border-radius:8px;border-left:3px solid #B8FF00;margin-bottom:36px;"><tr><td style="padding:22px 24px;"><p style="font-family:Arial,sans-serif;font-weight:700;font-size:11px;text-transform:uppercase;letter-spacing:0.12em;color:#999;margin:0 0 16px;">Your audit covers</p><table cellpadding="0" cellspacing="0"><tr><td style="padding-bottom:12px;font-family:Arial,sans-serif;font-size:14px;color:#333;line-height:1.5;"><span style="color:#B8FF00;font-weight:900;">&#10003;</span>&nbsp;&nbsp;23-point design and conversion review</td></tr><tr><td style="padding-bottom:12px;font-family:Arial,sans-serif;font-size:14px;color:#333;line-height:1.5;"><span style="color:#B8FF00;font-weight:900;">&#10003;</span>&nbsp;&nbsp;Google Business Profile check</td></tr><tr><td style="padding-bottom:12px;font-family:Arial,sans-serif;font-size:14px;color:#333;line-height:1.5;"><span style="color:#B8FF00;font-weight:900;">&#10003;</span>&nbsp;&nbsp;Local competitor benchmarking</td></tr><tr><td style="font-family:Arial,sans-serif;font-size:14px;color:#333;line-height:1.5;"><span style="color:#B8FF00;font-weight:900;">&#10003;</span>&nbsp;&nbsp;Monthly revenue opportunity estimate</td></tr></table></td></tr></table><p style="font-family:Arial,sans-serif;font-size:14px;color:#888;line-height:1.7;margin:0 0 32px;">In the meantime — got questions? Just reply to this email. It goes straight to us.</p><p style="font-family:Arial,sans-serif;font-size:15px;color:#444;margin:0;line-height:1.6;">Talk soon,<br/><strong style="color:#080808;">The Smart Website Co.</strong></p></td></tr><tr><td style="background:#080808;height:4px;line-height:4px;font-size:4px;border-radius:0 0 12px 12px;">&nbsp;</td></tr><tr><td style="padding:28px 0;text-align:center;"><p style="font-family:Arial,sans-serif;font-size:11px;color:#999;margin:0 0 6px;">www.thesmartwebsite.co &nbsp;·&nbsp; hello@thesmartwebsite.co</p><p style="font-family:Arial,sans-serif;font-size:10px;color:#BBBBBB;margin:0;">Websites and AI for Australian tradies and local businesses</p></td></tr></table></td></tr></table></body></html>`;
}

async function sendTelegramBuildAlert(name: string, businessName: string, email: string, website: string, trade: string) {
  const token = process.env.TELEGRAM_SMARTWEB_BOT_TOKEN || '';
  const chat_id = process.env.TELEGRAM_BUILD_ALERTS_CHAT_ID || '';
  if (!token || !chat_id) return;
  const msg = `🔔 New inbound lead\n\nName: ${name}\nBusiness: ${businessName}\nTrade: ${trade}\nEmail: ${email}\nWebsite: ${website}\n\nAudit queued — report due in ~2 hours`;
  await fetch(`https://api.telegram.org/bot${token}/sendMessage`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ chat_id, text: msg }),
  }).catch(() => {});
}

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { name, businessName, phone, website, suburb, biggestProblem, anythingElse } = body;

    // Server-side validation — all 7 required fields
    const cleanName = validateField(name, 'Your name');
    const cleanBusiness = validateField(businessName, 'Business name');
    const cleanPhone = validatePhone(phone);
    const cleanWebsite = validateUrl(website);
    const cleanSuburb = validateField(suburb, 'Suburb / location');
    const cleanProblem = validateField(biggestProblem, 'Biggest problem');
    const cleanAnythingElse = (anythingElse || '').trim();

    const ghlWebhookUrl = process.env.GHL_WEBHOOK_URL;

    // Fire GHL webhook + Mailgun concurrently
    const promises: Promise<unknown>[] = [];

    // 1. GHL webhook — creates INBOUND_LEAD in CRM
    if (ghlWebhookUrl) {
      promises.push(
        fetch(ghlWebhookUrl, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            event: 'INBOUND_LEAD',
            source: 'thesmartwebsite.co',
            timestamp: new Date().toISOString(),
            lead: {
              name: cleanName,
              businessName: cleanBusiness,
              phone: formatPhoneForDisplay(cleanPhone),
              email: null, // not collected on this form
              website: cleanWebsite,
              suburb: cleanSuburb,
              biggestProblem: cleanProblem,
              notes: cleanAnythingElse || null,
            },
          }),
        }).catch((err) => {
          console.error('GHL webhook error:', err);
          // Non-fatal — don't fail the form submission if GHL is down
        })
      );
    } else {
      console.warn('GHL_WEBHOOK_URL env var not set — skipping CRM write');
    }

    // 2. Mailgun — readable notification email to hello@thesmartwebsite.co
    const problemLabels: Record<string, string> = {
      'not-enough-leads': 'Not enough leads coming in',
      'cant-find-google': "Can't be found on Google",
      'outdated': 'Website looks outdated or embarrassing',
      'no-website': "I don't have a website yet",
      'losing-calls': "I'm losing calls I don't know about",
    };
    const problemLabel = problemLabels[cleanProblem] || cleanProblem;

    const textBody = [
      `New Audit Request — thesmartwebsite.co`,
      ``,
      `Name:    ${cleanName}`,
      `Business: ${cleanBusiness}`,
      `Phone:   ${formatPhoneForDisplay(cleanPhone)}`,
      `Website: ${cleanWebsite || 'Not provided'}`,
      `Suburb:  ${cleanSuburb}`,
      `Problem: ${problemLabel}`,
      cleanAnythingElse ? `\nAdditional notes:\n${cleanAnythingElse}` : '',
    ].filter(Boolean).join('\n');

    const htmlBody = `<!DOCTYPE html>
<html>
<body style="margin:0; padding:0; background:#0A0A0A; font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
  <div style="max-width:560px; margin:40px auto; background:#111; border:1px solid #222; border-radius:16px; padding:40px;">
    <div style="background:#B8FF00; color:#0A0A0A; display:inline-block; padding:6px 14px; border-radius:6px; font-size:12px; font-weight:700; text-transform:uppercase; letter-spacing:0.05em; margin-bottom:28px;">
      New Audit Request
    </div>
    <table style="width:100%; border-collapse:collapse;">
      <tr>
        <td style="padding:14px 0; border-bottom:1px solid #1a1a1a; color:#666; font-size:13px; width:90px;">Name</td>
        <td style="padding:14px 0; border-bottom:1px solid #1a1a1a; color:#f5f5f5; font-size:15px; font-weight:600;">${cleanName}</td>
      </tr>
      <tr>
        <td style="padding:14px 0; border-bottom:1px solid #1a1a1a; color:#666; font-size:13px;">Business</td>
        <td style="padding:14px 0; border-bottom:1px solid #1a1a1a; color:#f5f5f5; font-size:15px; font-weight:600;">${cleanBusiness}</td>
      </tr>
      <tr>
        <td style="padding:14px 0; border-bottom:1px solid #1a1a1a; color:#666; font-size:13px;">Phone</td>
        <td style="padding:14px 0; border-bottom:1px solid #1a1a1a; font-size:15px;">
          <a href="tel:${cleanPhone}" style="color:#B8FF00; text-decoration:none; font-weight:600;">${formatPhoneForDisplay(cleanPhone)}</a>
        </td>
      </tr>
      <tr>
        <td style="padding:14px 0; border-bottom:1px solid #1a1a1a; color:#666; font-size:13px;">Website</td>
        <td style="padding:14px 0; border-bottom:1px solid #1a1a1a; font-size:15px;">
          ${cleanWebsite ? `<a href="${cleanWebsite}" style="color:#B8FF00; text-decoration:none;">${cleanWebsite}</a>` : '<span style="color:#555;">Not provided</span>'}
        </td>
      </tr>
      <tr>
        <td style="padding:14px 0; border-bottom:1px solid #1a1a1a; color:#666; font-size:13px;">Suburb</td>
        <td style="padding:14px 0; border-bottom:1px solid #1a1a1a; color:#f5f5f5; font-size:15px;">${cleanSuburb}</td>
      </tr>
      <tr>
        <td style="padding:14px 0; border-bottom:1px solid #1a1a1a; color:#666; font-size:13px;">Problem</td>
        <td style="padding:14px 0; border-bottom:1px solid #1a1a1a; color:#f5f5f5; font-size:15px;">${problemLabel}</td>
      </tr>
      ${cleanAnythingElse ? `
      <tr>
        <td style="padding:14px 0; color:#666; font-size:13px; vertical-align:top;">Notes</td>
        <td style="padding:14px 0; color:#888; font-size:14px; line-height:1.6;">${cleanAnythingElse}</td>
      </tr>` : ''}
    </table>
    <div style="margin-top:32px; padding-top:24px; border-top:1px solid #1a1a1a;">
      <a href="tel:${cleanPhone}" style="display:inline-block; background:#B8FF00; color:#0A0A0A; padding:14px 28px; border-radius:8px; text-decoration:none; font-weight:700; font-size:15px;">Call ${cleanName}</a>
      <a href="mailto:?subject=Re: Your free audit — ${cleanBusiness}&body=Hi ${cleanName.split(' ')[0]},%0A%0AThanks for your interest. I'd love to chat about your website.%0A%0A" style="display:inline-block; margin-left:12px; background:#1a1a1a; color:#f5f5f5; padding:14px 28px; border-radius:8px; text-decoration:none; font-weight:600; font-size:15px;">Email back</a>
    </div>
    <p style="color:#444; font-size:12px; margin-top:24px;">${new Date().toLocaleString('en-AU', { timeZone: 'Australia/Sydney' })} · thesmartwebsite.co</p>
  </div>
</body>
</html>`;

    promises.push(
      fetch(`https://api.mailgun.net/v3/${MAILGUN_DOMAIN}/messages`, {
        method: 'POST',
        headers: {
          'Authorization': 'Basic ' + Buffer.from(`api:${MAILGUN_API_KEY}`).toString('base64'),
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: new URLSearchParams({
          from: `The Smart Website Co. <hello@${MAILGUN_DOMAIN.replace('sandbox', '').split('.')[0] || 'sandbox'}.mailgun.org>`,
          to: 'hello@thesmartwebsite.co',
          subject: `Audit Request: ${cleanBusiness} — ${cleanSuburb}`,
          text: textBody,
          html: htmlBody,
        }),
      }).catch((err) => {
        console.error('Mailgun error:', err);
      })
    );

    // 3. Acknowledgement email to the client
    if (body.email) {
      const ackForm = new FormData();
      ackForm.append('from', 'The Smart Website Co. <hello@thesmartwebsite.co>');
      ackForm.append('to', body.email);
      ackForm.append('subject', `Your audit is in the queue — ${body.businessName}`);
      ackForm.append('html', ackEmailHTML(body.name, body.businessName));
      promises.push(
        fetch(`https://api.mailgun.net/v3/${MAILGUN_DOMAIN}/messages`, {
          method: 'POST',
          headers: {
            'Authorization': 'Basic ' + Buffer.from(`api:${MAILGUN_API_KEY}`).toString('base64'),
          },
          body: ackForm,
        }).catch((err) => {
          console.error('Client ack email error:', err);
        })
      );
    }

    // 4. Telegram build alert
    promises.push(
      sendTelegramBuildAlert(body.name, body.businessName, body.email || '', body.website || '', body.trade || '').catch(() => {})
    );

    // Wait for all to complete (non-blocking failures)
    await Promise.allSettled(promises);

    return NextResponse.json({ success: true });

  } catch (err) {
    const message = err instanceof Error ? err.message : 'Server error';
    console.error('Form submission error:', message);
    return NextResponse.json({ error: message }, { status: 400 });
  }
}