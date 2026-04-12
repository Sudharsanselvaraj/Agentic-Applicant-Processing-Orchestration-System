#!/usr/bin/env python3
"""Open browser and WAIT - user logs in manually"""
from playwright.sync_api import sync_playwright

print("=" * 60)
print("MANUAL LOGIN DEMO")
print("=" * 60)

print("""
STEP FOR VIDEO:
1. Run this command
2. Browser OPENS - show this on screen
3. You manually click/login in the browser (show this!)
4. Don't press anything - just wait
5. Run test_cookies.py AFTER to verify login worked
""")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    page.goto("https://internshala.com/login")
    
    print("\n✓ Browser is OPEN - showing login page")
    print("✓ In video: show the browser, then manually log in")
    print("✓ After login, keep browser open")
    print("\nThen run: python test_cookies.py")
    print("Then run: python test_system.py")
    
    # Just keep browser open - don't close
    print("\nPress Ctrl+C to close browser")
    import time
    try:
        time.sleep(300)  # 5 minutes
    except:
        pass
    
    browser.close()