import os
import pickle
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import base64

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly', 'https://www.googleapis.com/auth/gmail.send']

def get_gmail_service():
    creds = None
    token_path = 'token.pickle'
    
    if os.path.exists(token_path):
        with open(token_path, 'rb') as token:
            creds = pickle.load(token)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            print("❌ No valid credentials. Run gmail_auth.py first.")
            return None
        
        with open(token_path, 'wb') as token:
            pickle.dump(creds, token)
    
    return build('gmail', 'v1', credentials=creds)

def send_email(to, subject, body, thread_id=None):
    service = get_gmail_service()
    if not service:
        return None
    
    message = MIMEMultipart()
    message['to'] = to
    message['subject'] = subject
    
    if thread_id:
        message['In-Reply-To'] = thread_id
        message['References'] = thread_id
    
    message.attach(MIMEText(body, 'plain'))
    
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
    
    try:
        if thread_id:
            sent = service.users().messages().send(
                userId='me',
                body={'raw': raw_message, 'threadId': thread_id}
            ).execute()
        else:
            sent = service.users().messages().send(
                userId='me',
                body={'raw': raw_message}
            ).execute()
        print(f"✅ Email sent to {to}")
        return sent
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        return None

def fetch_unread_emails():
    service = get_gmail_service()
    if not service:
        return []
    
    try:
        results = service.users().messages().list(
            userId='me',
            labelIds=['INBOX', 'UNREAD'],
            maxResults=20
        ).execute()
        
        messages = results.get('messages', [])
        emails = []
        
        for msg in messages:
            msg_data = service.users().messages().get(
                userId='me', 
                id=msg['id'],
                format='full'
            ).execute()
            
            headers = msg_data['payload']['headers']
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')
            sender = next((h['value'] for h in headers if h['name'] == 'From'), '')
            
            body = ''
            if 'parts' in msg_data['payload']:
                for part in msg_data['payload']['parts']:
                    if part['mimeType'] == 'text/plain':
                        body = part['body'].get('data', '')
                        break
            
            if body:
                body = base64.urlsafe_b64decode(body).decode('utf-8')
            
            emails.append({
                'id': msg['id'],
                'thread_id': msg_data.get('threadId'),
                'subject': subject,
                'from': sender,
                'body': body
            })
        
        return emails
    except Exception as e:
        print(f"❌ Failed to fetch emails: {e}")
        return []

def mark_as_read(msg_id):
    service = get_gmail_service()
    if not service:
        return
    
    try:
        service.users().messages().modify(
            userId='me',
            id=msg_id,
            body={'removeLabelIds': ['UNREAD']}
        ).execute()
    except Exception as e:
        print(f"❌ Failed to mark as read: {e}")