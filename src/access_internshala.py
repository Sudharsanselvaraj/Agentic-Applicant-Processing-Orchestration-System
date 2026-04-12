"""
ACCESS Component: Internshala Data Extraction

This module handles authentication and data extraction from Internshala.
Uses cookie-based auth - cookies must be provided via environment variables.

Note: Internshala uses Google reCAPTCHA Enterprise (invisible variant) which blocks
automated browsers. The workaround is to use valid session cookies from a manual login.
"""

import os
import re
import json
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Optional
import aiohttp
import pandas as pd
from bs4 import BeautifulSoup
from src.config import DATA_DIR, OUTPUT_DIR

COOKIE_ENV_VARS = [
    "INTERNSHALA_SESSION",
    "INTERNSHALA_BANNER",
    "INTERNSHALA_USER"
]

def get_cookies() -> dict:
    """Extract cookies from environment variables OR saved file."""
    cookies = {}
    
    # First: Check environment variables
    for var in COOKIE_ENV_VARS:
        value = os.environ.get(var, "")
        if value:
            cookie_parts = value.split("=")
            if len(cookie_parts) == 2:
                cookies[cookie_parts[0]] = cookie_parts[1]
            else:
                cookies[var.replace("INTERNSHALA_", "").lower()] = value
    
    # Second: Check saved cookie file (fallback)
    cookie_file = Path("data/cookies.json")
    if not cookies and cookie_file.exists():
        try:
            with open(cookie_file) as f:
                file_cookies = json.load(f)
                for name, value in file_cookies.items():
                    cookies[name] = value
            print(f"📂 Loaded cookies from {cookie_file}")
        except Exception as e:
            print(f"⚠️ Could not load cookie file: {e}")
    
    # Third: Check raw session file
    raw_file = Path("data/cookies_raw.txt")
    if not cookies.get('session') and raw_file.exists():
        session_value = raw_file.read_text().strip()
        if session_value:
            cookies['session'] = session_value
            print(f"📂 Loaded session from {raw_file}")
    
    return cookies

async def fetch_page(session, url: str, cookies: dict) -> Optional[str]:
    """Fetch a page with session cookies."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }
    
    try:
        async with session.get(url, cookies=cookies, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as resp:
            if resp.status == 200:
                return await resp.text()
            elif resp.status == 403:
                print("❌ 403 Forbidden - Cookies may be expired or invalid")
                return None
            else:
                print(f"❌ HTTP {resp.status}")
                return None
    except Exception as e:
        print(f"❌ Request failed: {e}")
        return None

def parse_applicants(html: str) -> list:
    """Parse applicant data from Internshala HTML."""
    if not html:
        return []
    
    soup = BeautifulSoup(html, "html.parser")
    applicants = []
    
    # Internshala applicant cards typically have this structure
    applicant_cards = soup.find_all("div", class_="internship_container")
    
    for card in applicant_cards:
        try:
            # Extract name
            name_elem = card.find("h3", class_="profile_heading") or card.find("a", href=re.compile(r"/profile/"))
            name = name_elem.get_text(strip=True) if name_elem else ""
            
            # Extract email from mailto: or specific element
            email_elem = card.find("a", href=re.compile(r"mailto:")) or card.find("div", class_="detail_value")
            email = ""
            if email_elem and email_elem.get("href"):
                email_match = re.search(r"mailto:([^?]+)", email_elem.get("href", ""))
                email = email_match.group(1) if email_match else ""
            
            # Extract skills
            skills_elem = card.find("div", class_="skill_tags") or card.find("span", class_="skill_required")
            skills = skills_elem.get_text(strip=True) if skills_elem else ""
            
            # If no structured data, try generic extraction
            if not name:
                # Fallback: find any link that looks like a profile
                profile_link = card.find("a", href=re.compile(r"/profile/|/application/"))
                if profile_link:
                    name = profile_link.get_text(strip=True)
            
            if name:
                applicants.append({
                    "name": name,
                    "email": email,
                    "skills": skills,
                    "github": "",
                    "answer": "",
                    "response_time": 0,
                    "scraped_at": datetime.now().isoformat()
                })
        except Exception as e:
            continue
    
    return applicants

async def fetch_all_applicants(base_url: str, pages: int = 5) -> list:
    """
    Fetch applicants across multiple pages.
    
    Args:
        base_url: URL of the applicant's list page
        pages: Number of pages to fetch
    
    Returns:
        List of applicant dictionaries
    """
    all_applicants = []
    cookies = get_cookies()
    
    if not cookies:
        print("⚠ No cookies found. Set INTERNSHALA_* environment variables.")
        print("   To get cookies:")
        print("   1. Log into Internshala in your browser")
        print("   2. Open DevTools → Application → Cookies")
        print("   3. Copy session cookie value")
        print("   4. Set: export INTERNSHALA_SESSION='session=VALUE'")
        return []
    
    async with aiohttp.ClientSession() as session:
        for page in range(1, pages + 1):
            url = f"{base_url}?page={page}"
            print(f"📄 Fetching page {page}...")
            
            html = await fetch_page(session, url, cookies)
            if html:
                applicants = parse_applicants(html)
                all_applicants.extend(applicants)
                print(f"   Found {len(applicants)} applicants")
            else:
                print(f"   Failed to fetch page {page}")
            
            await asyncio.sleep(1)  # Rate limiting
    
    return all_applicants

def export_applicants(applicants: list, output_path: str = None) -> str:
    """Export applicants to CSV."""
    if not output_path:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        output_path = OUTPUT_DIR / "scraped_applicants.csv"
    
    if applicants:
        df = pd.DataFrame(applicants)
        df.to_csv(output_path, index=False)
        print(f"✅ Exported {len(applicants)} applicants to {output_path}")
    
    return str(output_path)

async def main():
    """CLI entry point."""
    import sys
    
    # Check for cookies
    cookies = get_cookies()
    if not cookies:
        print("❌ No Internshala cookies found in environment")
        print("\nTo set up:")
        print("1. Log into Internshala in Chrome")
        print("2. DevTools (F12) → Application → Cookies → internshala.com")
        print("3. Copy the 'session' cookie value")
        print("4. Run: export INTERNSHALA_SESSION='session=YOUR_VALUE'")
        print("5. Run this script again")
        return
    
    # Demo: fetch sample URL (would be from actual job posting)
    url = os.environ.get("INTERNSHALA_JOB_URL", "")
    if not url:
        print("❌ Set INTERNSHALA_JOB_URL environment variable")
        return
    
    pages = int(os.environ.get("INTERNSHALA_PAGES", "5"))
    applicants = await fetch_all_applicants(url, pages)
    
    if applicants:
        export_applicants(applicants)
    else:
        print("❌ No applicants fetched")

if __name__ == "__main__":
    asyncio.run(main())