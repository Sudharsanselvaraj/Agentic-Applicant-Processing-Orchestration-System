#!/usr/bin/env python3
"""
Playwright VISIBLE browser - for video demo
Opens browser, waits for manual login, extracts cookies
"""
from playwright.sync_api import sync_playwright
import json
import os

print("=" * 60)
print("PLAYWRIGHT - VISIBLE BROWSER LOGIN")
print("=" * 60)

print("""
INSTRUCTIONS FOR VIDEO:
────────────────────
1. Browser will open (show this on screen)
2. You see Internshala login page
3. Log in manually as employer
4. Navigate to applications page
5. Come back HERE and press Ctrl+C
""")

with sync_playwright() as p:
    # VISIBLE browser - user sees it!
    browser = p.chromium.launch(
        headless=False,  # ← NOT headless!
        args=['--disable-blink-features=AutomationControlled']
    )
    
    page = browser.new_page()
    page.goto("https://internshala.com/login")
    
    print("\n✓ Browser opened - showing Internshala login")
    print("✓ Now log in manually...")
    print("✓ Then run this command to extract cookies:")
    print("   python -c \"import json; from playwright.sync_api import sync_playwright; "
    print("   with sync_playwright() as p: "
    print("     browser = p.chromium.launch(headless=False); "
    print("     page = browser.new_page(); "
    print("     page.goto('https://internshala.com/employer/applications'); "
    print("     cookies = page.context.cookies(); "
    print("     print(cookies))\"" )
    
    input("\nPress ENTER after logging in...") 
    
    # Get cookies
    cookies = page.context.cookies()
    
    # Save
    cookie_dict = {c['name']: c['value'] for c in cookies}
    os.makedirs('data', exist_ok=True)
    with open('data/cookies.json', 'w') as f:
        json.dump(cookie_dict, f, indent=2)
    
    print(f"\n✓ Saved {len(cookies)} cookies")
    print("  → data/cookies.json")
    
    browser.close()

print("\n✅ Done!")