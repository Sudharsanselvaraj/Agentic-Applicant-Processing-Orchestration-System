#!/usr/bin/env python3
"""
Cookie Extractor for Internshala
=================================
Implements TWO approaches, tried in order:

APPROACH 1 — CDP attachment (preferred, fully programmable)
  Connects to a Chrome instance already running with remote debugging enabled.
  This reads cookies directly from the live session via Chrome DevTools Protocol
  without touching the login page or reCAPTCHA at all.

  Start Chrome first:
      google-chrome --remote-debugging-port=9222 --user-data-dir=/tmp/chrome_debug
  Then log in to Internshala manually in that window.
  Then run: python src/get_cookies.py

APPROACH 2 — Playwright non-headless fallback
  Opens a visible Chromium window, waits for you to log in manually,
  then extracts ALL cookies (including httpOnly ones, which extensions cannot read).
  This is the approach confirmed working in testing.

Usage:
    python src/get_cookies.py          # tries CDP first, falls back to Playwright
    python src/get_cookies.py --cdp    # CDP only
    python src/get_cookies.py --browser # Playwright only
"""

import sys
import json
import time
import asyncio
from pathlib import Path
from datetime import datetime

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
COOKIE_FILE = DATA_DIR / "cookies.json"
SESSION_EXPIRED_FLAG = DATA_DIR / "session_expired.flag"


# ─────────────────────────────────────────────
# APPROACH 1: CDP (Chrome DevTools Protocol)
# ─────────────────────────────────────────────

def try_cdp_extraction(port: int = 9222) -> dict:
    """
    Connect to a running Chrome instance via CDP and extract cookies.

    Chrome must be started with:
        google-chrome --remote-debugging-port=9222 --user-data-dir=/tmp/chrome_debug

    CDP gives us direct access to the cookie store, bypassing all extension
    restrictions. httpOnly cookies are fully accessible here.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("❌ Playwright not installed: pip install playwright && playwright install chromium")
        return {}

    print(f"🔌 Attempting CDP connection to Chrome on port {port}...")

    with sync_playwright() as p:
        try:
            # Attach to the ALREADY-RUNNING Chrome (not launching a new one)
            browser = p.chromium.connect_over_cdp(f"http://localhost:{port}")
        except Exception as e:
            print(f"   ❌ CDP connection failed: {e}")
            print(f"   Make sure Chrome is running with: --remote-debugging-port={port}")
            return {}

        print("   ✅ Connected to Chrome via CDP")

        # Get all contexts (browser windows)
        contexts = browser.contexts
        if not contexts:
            print("   ❌ No browser contexts found")
            browser.close()
            return {}

        context = contexts[0]
        all_cookies = context.cookies()

        # Filter to Internshala cookies
        internshala_cookies = [
            c for c in all_cookies
            if "internshala" in c.get("domain", "")
        ]

        if not internshala_cookies:
            print("   ⚠ No Internshala cookies found — are you logged in?")
            browser.close()
            return {}

        print(f"   ✅ Found {len(internshala_cookies)} Internshala cookies via CDP")
        browser.close()

        return {c["name"]: c["value"] for c in internshala_cookies}


# ─────────────────────────────────────────────
# APPROACH 2: Non-headless Playwright
# ─────────────────────────────────────────────

def try_playwright_extraction() -> dict:
    """
    Open a visible (non-headless) Chromium, wait for manual login,
    then extract all cookies including httpOnly ones.

    Playwright's context.cookies() has native access to the cookie store —
    unlike Chrome extensions which block httpOnly cookies via the extension API.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("❌ Playwright not installed: pip install playwright && playwright install chromium")
        return {}

    print("🚀 Opening visible Chromium browser (non-headless)...")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-web-security",
            ]
        )

        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        print("📱 Navigating to Internshala login...")
        page.goto("https://internshala.com/login", wait_until="domcontentloaded")

        print()
        print("=" * 50)
        print("ACTION REQUIRED:")
        print("  1. Log in to your Internshala EMPLOYER account")
        print("  2. Navigate to your job's applicant list page")
        print("  3. Come back to THIS terminal and press ENTER")
        print("=" * 50)
        print()

        try:
            input("⏳ Press ENTER once you are logged in and on the applications page...")
        except EOFError:
            print("No stdin — closing")
            browser.close()
            return {}

        # Extract all cookies from the live context
        all_cookies = context.cookies()
        internshala_cookies = [
            c for c in all_cookies
            if "internshala" in c.get("domain", "")
        ]

        print(f"\n📋 Extracted {len(all_cookies)} total cookies, {len(internshala_cookies)} Internshala cookies")
        browser.close()

        return {c["name"]: c["value"] for c in internshala_cookies}


# ─────────────────────────────────────────────
# Save + export helpers
# ─────────────────────────────────────────────

def save_cookies(cookie_dict: dict):
    """Persist cookies to data/cookies.json and print env var export commands."""
    if not cookie_dict:
        print("❌ No cookies to save")
        return

    with open(COOKIE_FILE, "w") as f:
        json.dump(cookie_dict, f, indent=2)

    print(f"\n✅ {len(cookie_dict)} cookies saved to {COOKIE_FILE}")
    print()
    print("──────────────────────────────────────────")
    print("Export these as environment variables:")
    print("──────────────────────────────────────────")
    for name, value in cookie_dict.items():
        safe = value.replace("'", "\\'")
        print(f"  export INTERNSHALA_{name.upper()}='{safe}'")

    # Clear any stale session-expired flag
    if SESSION_EXPIRED_FLAG.exists():
        SESSION_EXPIRED_FLAG.unlink()
        print("\n✅ Cleared stale session_expired.flag")

    print()
    print("Next step: python src/access_internshala.py")


# ─────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────

def main():
    print("=" * 60)
    print("APOS — Internshala Cookie Extractor")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    print()

    mode = sys.argv[1] if len(sys.argv) > 1 else "auto"

    cookies = {}

    if mode in ("auto", "--cdp"):
        cookies = try_cdp_extraction()

    if not cookies and mode in ("auto", "--browser"):
        print("\nFalling back to Playwright browser approach...")
        cookies = try_playwright_extraction()

    if cookies:
        save_cookies(cookies)
    else:
        print("\n❌ Could not extract cookies via any method.")
        print("Manually copy from DevTools → Application → Cookies → internshala.com")
        print("Then create data/cookies.json with the values.")


if __name__ == "__main__":
    main()
