#!/usr/bin/env python3
"""GHL CRM integration - Smart Website v3"""
import os, requests

GHL_KEY = os.environ.get("GHL_API_KEY", "pit-1018a51b-896e-4e37-a94a-da314b3aeb78")
GHL_LOC = os.environ.get("GHL_LOCATION_ID", "jptMFdSGspW5HK3uWBDb")
BASE = "https://api.gohighlevel.com"
H = {"Authorization": f"Bearer {GHL_KEY}", "Location": GHL_LOC, "Content-Type": "application/json", "Accept": "application/json"}

def api_get(path):
    r = requests.get(BASE + path, headers=H, timeout=15)
    try:
        return r.status_code, r.json()
    except:
        return r.status_code, r.text

def api_post(path, data):
    r = requests.post(BASE + path, json=data, headers=H, timeout=15)
    try:
        return r.status_code, r.json()
    except:
        return r.status_code, r.text

def test():
    s, d = api_get("/")
    print(f"/ → {s}: {str(d)[:80]}")
    s2, d2 = api_get("/contacts?limit=1")
    print(f"/contacts → {s2}: {str(d2)[:100]}")

if __name__ == "__main__":
    test()
