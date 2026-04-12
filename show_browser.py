#!/usr/bin/env python3
"""Playwright VISIBLE browser - for video demo"""
from playwright.sync_api import sync_playwright
import json
import os
import time

print("=" * 60)
print("PLAYWRIGHT - VISIBLE BROWSER LOGIN")
print("=" * 60)

print("\n[1] Opening browser...")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    
    print("[2] Navigating to Internshala login...")
    page.goto("https://internshala.com/login")
    
    print("\n[3] INSTRUCTIONS:")
    print("   In the BROWSER WINDOW:")
    print("   - Log in to Internshala (employer account)")
    print("   - Navigate to applications page")
    print("   - Then come back to THIS terminal")
    print("   - Press Ctrl+C when cookies are needed")
    
    print("\n[4] Waiting 30 seconds for login...")
    time.sleep(30)
    
    print("[5] Extracting cookies...")
    cookies = page.context.cookies()
    cookie_dict = {c['name']: c['value'] for c in cookies}
    os.makedirs('data', exist_ok=True)
    with open('data/cookies.json', 'w') as f:
        json.dump(cookie_dict, f, indent=2)
    
    print(f"   Saved {len(cookies)} cookies to data/cookies.json")
    browser.close()

print("\n✅ DONE!")