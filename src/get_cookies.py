#!/usr/bin/env python3
"""
Cookie Extractor - Opens browser, waits for ENTER to extract

Usage - RUN IN A NEW TERMINAL:
    python3 src/get_cookies.py
"""

import time
import json
from pathlib import Path

print("=" * 60)
print("Internshala Cookie Extractor")
print("=" * 60)
print()

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("❌ Playwright not installed")
    print("   Run: pip install playwright && playwright install chromium")
    exit(1)

print("🚀 Opening Chromium browser...")
print()

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=False,
        args=['--disable-blink-features=AutomationControlled']
    )
    
    context = browser.new_context()
    page = context.new_page()
    
    print("📱 Navigating to internshala.com...")
    page.goto("https://www.internshala.com", wait_until="networkidle")
    
    print()
    print("=" * 40)
    print("INSTRUCTIONS:")
    print("=" * 40)
    print("1. Log in to your Internshala employer account")
    print("2. Go to your applications page")
    print("3. Switch to THIS terminal and press ENTER")
    print()
    
    try:
        input("Press ENTER after logging in and viewing applications...")
    except EOFError:
        print("No input available - closing browser")
        browser.close()
        exit(1)
    
    # Extract cookies
    cookies = context.cookies()
    
    print(f"\n📋 Found {len(cookies)} cookies")
    
    # Save to file
    cookie_file = Path("data/cookies.json")
    cookie_file.parent.mkdir(parents=True, exist_ok=True)
    
    cookie_dict = {}
    for c in cookies:
        cookie_dict[c['name']] = c['value']
    
    with open(cookie_file, "w") as f:
        json.dump(cookie_dict, f, indent=2)
    
    # Save raw session
    for c in cookies:
        if c['name'] == 'session':
            raw_file = Path("data/cookies_raw.txt")
            raw_file.write_text(c['value'])
            print("✅ Session cookie saved")
            break
    
    print(f"✅ All cookies saved to {cookie_file}")
    
    browser.close()

print("\n✅ Done!")
print("Next: python3 src/access_internshala.py")