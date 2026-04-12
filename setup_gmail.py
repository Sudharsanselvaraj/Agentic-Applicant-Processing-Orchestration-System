#!/usr/bin/env python3
"""
Gmail OAuth Setup — run ONCE before the demo.

Steps:
  1. Go to console.cloud.google.com
  2. Create a project → Enable Gmail API
  3. OAuth consent screen → External → Add your email as test user
  4. Credentials → OAuth 2.0 Client ID → Desktop app → Download JSON
  5. Save it as credentials.json in this folder
  6. Run: python setup_gmail.py
  7. Browser opens → approve access → token.pickle is saved
  8. Done. The system will use token.pickle from now on.
"""

import pickle
import os
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.modify',
]

CREDS_FILE = "credentials.json"
TOKEN_FILE = "token.pickle"


def main():
    print("=" * 50)
    print("APOS — Gmail OAuth Setup")
    print("=" * 50)

    if not Path(CREDS_FILE).exists():
        print(f"\n❌ {CREDS_FILE} not found.")
        print("Download it from Google Cloud Console:")
        print("  console.cloud.google.com → APIs & Services → Credentials")
        print("  Create OAuth 2.0 Client ID (Desktop) → Download JSON")
        print(f"  Save as: {CREDS_FILE}")
        return

    creds = None

    if Path(TOKEN_FILE).exists():
        with open(TOKEN_FILE, 'rb') as f:
            creds = pickle.load(f)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing expired token...")
            creds.refresh(Request())
        else:
            print("Opening browser for OAuth approval...")
            flow = InstalledAppFlow.from_client_secrets_file(CREDS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, 'wb') as f:
            pickle.dump(creds, f)

    print(f"\n✅ Gmail authenticated successfully!")
    print(f"✅ token.pickle saved.")
    print(f"\nYou can now run: python src/orchestrator.py --once")


if __name__ == "__main__":
    main()
