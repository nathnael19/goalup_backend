from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from app.core.config import settings
from pydantic import EmailStr
import logging

logger = logging.getLogger(__name__)

conf = ConnectionConfig(
    MAIL_USERNAME=settings.MAIL_USERNAME or "",
    MAIL_PASSWORD=settings.MAIL_PASSWORD or "",
    MAIL_FROM=settings.MAIL_FROM,
    MAIL_PORT=settings.MAIL_PORT,
    MAIL_SERVER=settings.MAIL_SERVER,
    MAIL_FROM_NAME=settings.MAIL_FROM_NAME,
    MAIL_STARTTLS=settings.MAIL_STARTTLS,
    MAIL_SSL_TLS=settings.MAIL_SSL_TLS,
    USE_CREDENTIALS=True if settings.MAIL_USERNAME else False,
    VALIDATE_CERTS=True if settings.ENVIRONMENT == "production" else False
)

async def send_invitation_email(email: str, invitation_link: str):
    """
    Sends an invitation email with a password setup link.
    If USE_REAL_MAIL is False or credentials are missing, it logs to console.
    """
    logger.info(f"Attempting to send invitation email to {email}")
    print(f"DEBUG: Attempting to send email to {email}")
    print(f"DEBUG: settings.USE_REAL_MAIL: {settings.USE_REAL_MAIL}")
    print(f"DEBUG: settings.MAIL_USERNAME: {settings.MAIL_USERNAME}")
    print(f"DEBUG: conf.MAIL_PORT: {conf.MAIL_PORT}")
    print(f"DEBUG: conf.MAIL_SSL_TLS: {conf.MAIL_SSL_TLS}")
    
    subject = "Welcome to GoalUP! Set up your password"
    body = f"""
    <h1>Welcome to GoalUP</h1>
    <p>You have been invited to join the GoalUP Admin Panel.</p>
    <p>Please click the link below to set up your password and activate your account:</p>
    <a href="{invitation_link}">Set up my password</a>
    <p>This link will expire in 24 hours.</p>
    <p>If you did not expect this invitation, please ignore this email.</p>
    """

    if not settings.USE_REAL_MAIL or not settings.MAIL_USERNAME:
        logger.info(f"SIMULATED EMAIL TO {email}")
        print(f"\n--- SIMULATED EMAIL ---")
        print(f"To:      {email}")
        print(f"Subject: {subject}")
        print(f"Link:    {invitation_link}")
        print(f"Reason:  {'USE_REAL_MAIL=False' if not settings.USE_REAL_MAIL else 'MAIL_USERNAME not set'}")
        print(f"--------------------------\n")
        return

    message = MessageSchema(
        subject=subject,
        recipients=[email],
        body=body,
        subtype=MessageType.html
    )

    fm = FastMail(conf)
    try:
        await fm.send_message(message)
        logger.info(f"Invitation email sent to {email}")
    except Exception as e:
        logger.error(f"Failed to send email to {email}: {str(e)}")
        # Fallback to console on error
        print(f"\n[EMAIL FAILED] Falling back to console for {email}:")
        print(f"🔗 Link: {invitation_link}\n")
