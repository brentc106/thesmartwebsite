export const runtime = 'nodejs';

import { NextRequest, NextResponse } from 'next/server';

const CORS = {
  'Access-Control-Allow-Origin': 'https://audit.thesmartwebsite.co',
  'Access-Control-Allow-Methods': 'POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type',
};

export async function OPTIONS() {
  return new Response(null, { status: 204, headers: CORS });
}

async function sendTg(token: string, chat_id: string, text: string): Promise<void> {
  if (!token || !chat_id) return;
  try {
    await fetch(`https://api.telegram.org/bot${token}/sendMessage`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ chat_id, text }),
    });
  } catch (e) {
    console.error('Telegram send failed:', e);
  }
}

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { name, email, suburb, trade, score, audit, accepted_at } = body;

    if (!name || !audit) {
      return NextResponse.json({ error: 'Missing required fields' }, { status: 400, headers: CORS });
    }

    const BRENT_TOKEN = process.env.TELEGRAM_SMARTWEB_BOT_TOKEN || '';
    const BRENT_CHAT_ID = process.env.TELEGRAM_BUILD_ALERTS_CHAT_ID || '';
    const MASON_CHAT_ID = process.env.TELEGRAM_MASON_CHAT_ID || '';

    const text = [
      '🔔 Build accepted',
      '',
      `Business: ${name}`,
      `Trade: ${trade || '—'}`,
      `Score: ${score || '—'}/30`,
      `Email: ${email || '—'}`,
      `Suburb: ${suburb || '—'}`,
      '',
      `Audit: ${audit}`,
      `Data: ${audit}/audit_data.json`,
      '',
      `Accepted: ${accepted_at || new Date().toISOString()}`,
    ].join('\n');

    // Fire to both Brent and Mason concurrently
    const promises = [];
    if (BRENT_TOKEN && BRENT_CHAT_ID) promises.push(sendTg(BRENT_TOKEN, BRENT_CHAT_ID, text));
    if (BRENT_TOKEN && MASON_CHAT_ID) promises.push(sendTg(BRENT_TOKEN, MASON_CHAT_ID, text));
    await Promise.allSettled(promises);

    return NextResponse.json({ success: true }, { headers: CORS });

  } catch (err) {
    const message = err instanceof Error ? err.message : 'Server error';
    console.error('Webhook error:', message);
    return NextResponse.json({ error: message }, { status: 500, headers: CORS });
  }
}