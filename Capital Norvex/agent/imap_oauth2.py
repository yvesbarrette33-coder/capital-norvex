import imaplib
import base64
import requests
from dotenv import load_dotenv
from pathlib import Path
import os

# Secrets stockés hors du repo (~/.capitalnorvex/.env, perms 600).
# Fallback : .env local pour rétrocompatibilité dev.
for _p in (Path.home() / ".capitalnorvex" / ".env", Path(__file__).parent / ".env"):
    if _p.exists():
        load_dotenv(_p)
        break

def get_access_token():
    url = "https://login.microsoftonline.com/" + os.getenv("AZURE_TENANT_ID") + "/oauth2/v2.0/token"
    data = {
        "grant_type": "client_credentials",
        "client_id": os.getenv("AZURE_CLIENT_ID"),
        "client_secret": os.getenv("AZURE_CLIENT_SECRET"),
        "scope": "https://outlook.office365.com/.default",
    }
    response = requests.post(url, data=data)
    response.raise_for_status()
    return response.json()["access_token"]

def connect_imap():
    email = os.getenv("MAIL_USER")
    token = get_access_token()
    auth_string = "user=" + email + "\x01auth=Bearer " + token + "\x01\x01"
    auth_b64 = base64.b64encode(auth_string.encode())
    mail = imaplib.IMAP4_SSL("outlook.office365.com", 993)
    mail.authenticate("XOAUTH2", lambda x: auth_b64)
    print("Connexion IMAP reussie !")
    return mail

mail = connect_imap()
mail.select("INBOX")
_, messages = mail.search(None, "UNSEEN")
print("Messages non lus : " + str(len(messages[0].split())))
