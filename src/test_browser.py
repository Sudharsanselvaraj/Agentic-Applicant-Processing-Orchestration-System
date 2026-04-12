#!/usr/bin/env python3
"""
Simple Test - Just open browser to prove it works

Run this first to verify browser opens:
    python3 src/test_browser.py
"""

from playwright.sync_api import sync_playwright

print("🚀 Testing Chromium...")
print("If browser opens, everything works!")
print()

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    print("✅ Browser opened!")
    
    page = browser.new_page()
    page.goto("https://internshala.com")
    print("✅ Navigated to Internshala")
    
    print()
    print("Browser should be open right now.")
    print("Press Ctrl+C in this terminal to close.")
    
    import time
    time.sleep(300)  # 5 minutes