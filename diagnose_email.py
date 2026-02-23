import asyncio
import os
from dotenv import load_dotenv
from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType

# Load environment variables
load_dotenv(".env")

async def send_test_email():
    print("--- GoalUP Email Diagnostic Tool (Standalone) ---")
    
    use_real = os.getenv("USE_REAL_MAIL", "False").lower() == "true"
    mail_server = os.getenv("MAIL_SERVER", "smtp.gmail.com")
    mail_port = int(os.getenv("MAIL_PORT", "587"))
    mail_user = os.getenv("MAIL_USERNAME")
    mail_pass = os.getenv("MAIL_PASSWORD")
    mail_from = os.getenv("MAIL_FROM", "info@goalup.com")
    mail_from_name = os.getenv("MAIL_FROM_NAME", "GoalUP Admin")
    mail_starttls = os.getenv("MAIL_STARTTLS", "True").lower() == "true"
    mail_ssl_tls = os.getenv("MAIL_SSL_TLS", "False").lower() == "true"
    
    print(f"USE_REAL_MAIL: {use_real}")
    print(f"MAIL_SERVER:   {mail_server}")
    print(f"MAIL_PORT:     {mail_port}")
    print(f"MAIL_USERNAME: {mail_user or 'Not Set'}")
    print(f"MAIL_FROM:     {mail_from}")
    print(f"MAIL_STARTTLS: {mail_starttls}")
    print(f"MAIL_SSL_TLS:  {mail_ssl_tls}")
    print("-" * 48)
    
    email = "test@example.com"
    subject = "GoalUP Diagnostic Test"
    link = "http://localhost:5173/setup-password?token=test_token"
    body = f"<h1>Diagnostic Test</h1><p>Link: <a href='{link}'>{link}</a></p>"

    if not use_real or not mail_user:
        print("\n--- 📧 SIMULATED EMAIL ---")
        print(f"To:      {email}")
        print(f"Subject: {subject}")
        print(f"Link:    {link}")
        print(f"Reason:  {'USE_REAL_MAIL=False' if not use_real else 'MAIL_USERNAME not set'}")
        print(f"--------------------------\n")
        return

    conf = ConnectionConfig(
        MAIL_USERNAME=mail_user,
        MAIL_PASSWORD=mail_pass,
        MAIL_FROM=mail_from,
        MAIL_PORT=mail_port,
        MAIL_SERVER=mail_server,
        MAIL_FROM_NAME=mail_from_name,
        MAIL_STARTTLS=mail_starttls,
        MAIL_SSL_TLS=mail_ssl_tls,
        USE_CREDENTIALS=True
    )

    message = MessageSchema(
        subject=subject,
        recipients=[email],
        body=body,
        subtype=MessageType.html
    )

    fm = FastMail(conf)
    try:
        await fm.send_message(message)
        print(f"\nSUCCESS: Email sent to {email}")
    except Exception as e:
        print(f"\nFAILED: {str(e)}")

if __name__ == "__main__":
    asyncio.run(send_test_email())
