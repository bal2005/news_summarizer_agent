# emailer.py
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")
EMAIL_TO = os.getenv("EMAIL_TO")

def send_digest_email(subject: str, html_body: str) -> None:
    """
    Send HTML email via Gmail using only EMAIL_USER, EMAIL_PASS, and EMAIL_TO.
    """
    msg = MIMEMultipart("alternative")
    msg["From"] = EMAIL_USER
    msg["To"] = EMAIL_TO
    msg["Subject"] = subject

    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        server.send_message(msg)

    print(f"✅ Email sent to {EMAIL_TO} with subject '{subject}'")
