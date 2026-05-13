#!/usr/bin/env python3
"""
Wait for MiniMax rate limit to clear, then run the audit pipeline.
Call with: python3 wait_and_run.py [batch_count]
Default batch: 1 (just the test lead)
"""
import json, urllib.request, time, subprocess, sys

KEY = 'sk-cp-vy21dTXtEeoNvh5tbDnRbVeQC4X9HF4f51Y2yaVhIj_e7bg3osM87w49ZA1dVEgIRos6SMiTQlvzgWx6xpgieR1h6dj2HBP0aRtLZDGVncJqJme_ofnTYZs'
GROUP_ID = '1912000199186714869'
MAX_WAIT = 3600  # 1 hour max

def probe():
    payload = json.dumps({
        'model': 'MiniMax-Text-01',
        'max_tokens': 20,
        'messages': [{'role': 'user', 'content': 'ok', 'sender_name': 'U', 'sender_type': 'USER'}],
        'bot_setting': [{'bot_name': 'A', 'content': 'x'}],
        'reply_constraints': {'status': 'success', 'length': 64, 'role': 'assistant', 'sender_type': 'BOT', 'sender_name': 'A'}
    }).encode()
    req = urllib.request.Request(
        'https://api.minimax.io/v1/text/chatcompletion_pro',
        data=payload,
        headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {KEY}', 'GroupId': GROUP_ID}
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            resp = json.loads(r.read())
        code = resp.get('base_resp', {}).get('status_code', 0)
        msg = resp.get('base_resp', {}).get('status_msg', '')
        return code, msg, resp
    except Exception as e:
        return 999, str(e), None

print("[Probe] Checking MiniMax rate limit status...")
for attempt in range(MAX_WAIT):
    code, msg, resp = probe()
    elapsed = attempt + 1
    
    if code == 0 or code == 200:
        print(f"[Probe] ✅ CLEAR after {elapsed}s — status: {msg}")
        choices = resp.get('choices', []) if resp else []
        raw_text = ''
        if choices:
            for m in choices[0].get('messages', []):
                if m.get('type') == 'text':
                    raw_text = m.get('text', '')
                    break
        if raw_text:
            print(f"[Probe] Response confirmed: {raw_text[:100]}")
        
        # Run the audit
        count = int(sys.argv[1]) if len(sys.argv) > 1 else 1
        print(f"[Probe] Running audit_generate.py --batch {count} ...")
        result = subprocess.run(
            ['python3', '/Users/brentext/.openclaw/workspace/smart-website/jarvis/crons/audit_generate.py', '--batch', str(count)],
            cwd='/Users/brentext/.openclaw/workspace/smart-website'
        )
        print(f"[Probe] Done. Exit code: {result.returncode}")
        exit(0)
    elif code == 1002 or 'rate limit' in msg.lower():
        if attempt % 10 == 0:
            print(f"[Probe] Rate limited... {elapsed}s elapsed, retrying in 30s")
        time.sleep(30)
    else:
        print(f"[Probe] Unexpected status {code}: {msg} — waiting 30s")
        time.sleep(30)

print("[Probe] MAX WAIT (1hr) exceeded — giving up")
exit(1)
