from __future__ import print_function

import os
import base64
import subprocess
from email.utils import parseaddr

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def authenticate():
    creds = None

    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file(
            "token.json",
            SCOPES
        )

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json",
                SCOPES
            )

            print()
            print("Abriendo autorización de Google...")
            print("Se abrirá el navegador predeterminado.")
            print()

            creds = flow.run_local_server(
                port=0,
                open_browser=True
            )

        with open("token.json", "w") as token:
            token.write(creds.to_json())

        os.chmod("token.json", 0o600)

    return creds


def decode_body(data):
    if not data:
        return ""

    try:
        return base64.urlsafe_b64decode(data).decode(
            "utf-8",
            errors="ignore"
        )
    except Exception:
        return ""


def extract_text(payload):
    text = ""

    if "body" in payload:
        text += decode_body(payload["body"].get("data"))

    for part in payload.get("parts", []):
        mime_type = part.get("mimeType", "")

        if mime_type == "text/plain":
            text += decode_body(
                part.get("body", {}).get("data")
            )

        elif mime_type.startswith("multipart/"):
            text += extract_text(part)

    return text


def get_header(headers, name):
    for header in headers:
        if header["name"].lower() == name.lower():
            return header["value"]

    return ""


def get_messages(service, max_results=10):
    response = service.users().messages().list(
        userId="me",
        q="newer_than:14d",
        maxResults=max_results
    ).execute()

    return response.get("messages", [])


def read_message(service, message_id):
    message = service.users().messages().get(
        userId="me",
        id=message_id,
        format="full"
    ).execute()

    payload = message.get("payload", {})
    headers = payload.get("headers", [])

    subject = get_header(headers, "Subject")
    sender = get_header(headers, "From")
    date = get_header(headers, "Date")

    sender_name, sender_email = parseaddr(sender)

    body = extract_text(payload)

    return {
        "id": message_id,
        "subject": subject,
        "sender_name": sender_name,
        "sender_email": sender_email,
        "date": date,
        "body": body,
    }


def main():
    print("=" * 60)
    print("GMAIL JOB ASSISTANT")
    print("=" * 60)
    print()

    print("Autenticando con Gmail...")

    credentials = authenticate()

    service = build(
        "gmail",
        "v1",
        credentials=credentials
    )

    print("Autenticación correcta.")
    print()
    print("Buscando correos de los últimos 14 días...")
    print()

    messages = get_messages(service)

    if not messages:
        print("No se encontraron correos recientes.")
        return

    print(f"Correos encontrados: {len(messages)}")
    print()

    for index, message in enumerate(messages, start=1):
        data = read_message(service, message["id"])

        print("-" * 60)
        print(f"CORREO #{index}")
        print(f"Asunto : {data['subject']}")
        print(
            f"De     : "
            f"{data['sender_name']} "
            f"<{data['sender_email']}>"
        )
        print(f"Fecha  : {data['date']}")
        print()

        preview = data["body"].replace("\n", " ").strip()

        if len(preview) > 500:
            preview = preview[:500] + "..."

        print("Contenido:")
        print(preview)
        print()

    print("=" * 60)
    print("Lectura finalizada")
    print("=" * 60)


if __name__ == "__main__":
    main()
