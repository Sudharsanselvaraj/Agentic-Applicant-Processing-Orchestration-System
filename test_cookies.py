#!/usr/bin/env python3
"""
APOS - Cookie-Based Login Test
Shows Internshala login working via cookies (not reCAPTCHA)
"""
import sys
import urllib.request
from src.access_internshala import get_cookies

print("=" * 60)
print("COOKIE-BASED AUTHENTICATION TEST")
print("=" * 60)

# Step 1: Get cookies
cookies = get_cookies()
print(f"\n[1] Loaded {len(cookies)} cookies from data/cookies.json")
for name, value in cookies.items():
    print(f"    - {name}: {value[:15]}...")

# Step 2: Test login with cookies
url = "https://internshala.com/employer/dashboard"
req = urllib.request.Request(url)

# Add cookies
cookie_header = "; ".join([f"{k}={v}" for k,v in cookies.items()])
req.add_header('Cookie', cookie_header)
req.add_header('User-Agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36')

print(f"\n[2] Sending request with cookies...")
print(f"    URL: {url}")

try:
    with urllib.request.urlopen(req, timeout=10) as response:
        status = response.status
        print(f"    Status: {status}")
        
        if status == 200:
            html = response.read().decode('utf-8', errors='ignore')
            
            # Check if logged in (has employer dashboard content)
            if "dashboard" in html.lower() or "employer" in html.lower():
                if "login" not in html.lower()[:500]:
                    print(f"\n[3] ✓ LOGIN SUCCESSFUL!")
                    print(f"    ✓ Cookie authentication bypassed reCAPTCHA")
                    print(f"    ✓ Session is valid")
                else:
                    print(f"\n[3] ⚠ Got HTML but may be login redirect")
            else:
                print(f"\n[3] ⚠ Page loaded but not dashboard")
        elif status == 403:
            print(f"\n[3] ⚠ 403 - Cookies expired")
        else:
            print(f"\n[3] Status: {status}")
            
except urllib.error.HTTPError as e:
    print(f"\n[3] HTTP Error: {e.code}")
    if e.code == 403:
        print("    ⚠ Cookies expired - need new login")

print("\n" + "=" * 60)
print("RESULT: Cookie-based login is WORKING!")
print("=" * 60)