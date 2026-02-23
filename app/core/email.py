import resend
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# Initialize Resend once at module level
if settings.RESEND_API_KEY:
    resend.api_key = settings.RESEND_API_KEY

def get_sender():
    """Validates and returns the sender email address."""
    if settings.USE_REAL_MAIL:
        if not settings.MAIL_FROM or settings.MAIL_FROM == "onboarding@resend.dev":
            logger.warning("PROD WARNING: Using sandbox sender or MAIL_FROM is unset with USE_REAL_MAIL=True")
            # In a strict production environment, we might want to raise an error here
        return settings.MAIL_FROM
    return settings.MAIL_FROM or "onboarding@resend.dev"

async def send_invitation_email(email: str, invitation_link: str):
    """
    Sends an invitation email using the official Resend Python SDK.
    """
    if not settings.USE_REAL_MAIL or not settings.RESEND_API_KEY:
        print(f"\n[MOCK EMAIL] To: {email}")
        print(f"Message: You're invited to join GoalUP...")
        print(f"🔗 Link: {invitation_link}\n")
        return True

    welcome_msg = (
        "You're invited to join GoalUP — your all-in-one platform for managing "
        "football tournaments, fixtures, results, and team performance. "
        "Get ready to organize, compete, and track every goal with ease!"
    )

    params: resend.Emails.SendParams = {
        "from": get_sender(),
        "to": [email],
        "subject": "Welcome to GoalUP! Set up your account password",
        "html": f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #eee; border-radius: 8px;">
                <h1 style="color: #1a1a1a;">Welcome to GoalUP</h1>
                
                <p style="font-size: 1.05em; color: #444;">
                    {welcome_msg}
                </p>

                <p>
                    To activate your account and create your password, 
                    please click the button below:
                </p>

                <div style="text-align: center; margin: 25px 0;">
                    <a href="{invitation_link}" 
                       style="background-color: #2563eb; color: #ffffff; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold; display: inline-block;">
                       Set Up My Password
                    </a>
                </div>

                <p style="font-size: 0.9em; color: #666;">
                    ⏳ This link will expire in 24 hours.
                </p>

                <p style="font-size: 0.9em; color: #666;">
                    If you did not expect this invitation, you can safely ignore this email.
                </p>

                <hr style="margin: 20px 0; border: none; border-top: 1px solid #eee;" />

                <p style="font-size: 0.8em; color: #999;">
                    © {settings.PROJECT_NAME or "GoalUP"} – Football Tournament Management System
                </p>
            </div>
        </body>
        </html>
        """
    }

    try:
        # Note: resend-python is currently synchronous
        email_response = resend.Emails.send(params)
        logger.info(f"Email sent via Resend: {email_response}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email via Resend SDK: {str(e)}")
        print(f"\n[EMAIL FAILED] Falling back to console for {email}:")
        print(f"Error details: {e}")
        print(f"🔗 Link: {invitation_link}\n")
        return False

async def send_reset_password_email(email: str, reset_link: str):
    """
    Sends a password reset email using the Resend Python SDK.
    """
    if not settings.USE_REAL_MAIL or not settings.RESEND_API_KEY:
        print(f"\n[MOCK RESET EMAIL] To: {email}")
        print(f"🔗 Link: {reset_link}\n")
        return True
    
    params: resend.Emails.SendParams = {
        "from": get_sender(),
        "to": [email],
        "subject": "Reset your GoalUP password",
        "html": f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #eee; border-radius: 8px;">
                <h1 style="color: #1a1a1a;">Reset Your Password</h1>
                <p>We received a request to reset your GoalUP account password.</p>
                <p>Click the button below to choose a new password:</p>
                <div style="text-align: center; margin: 25px 0;">
                    <a href="{reset_link}" 
                       style="background-color: #2563eb; color: #ffffff; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold; display: inline-block;">
                       Reset Password
                    </a>
                </div>
                <p style="font-size: 0.9em; color: #666;">
                    ⏳ This link will expire in 2 hours for your security.
                </p>
                <p style="font-size: 0.9em; color: #666;">
                    If you didn't request a password reset, you can safely ignore this email.
                </p>
                <hr style="margin: 20px 0; border: none; border-top: 1px solid #eee;" />
                <p style="font-size: 0.8em; color: #999;">
                    © {settings.PROJECT_NAME or "GoalUP"} – Football Tournament Management System
                </p>
            </div>
        </body>
        </html>
        """
    }

    try:
        resend.Emails.send(params)
        logger.info(f"Reset password email sent to {email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send reset email: {str(e)}")
        print(f"\n[RESET EMAIL FAILED] Falling back to console for {email}:")
        print(f"🔗 Link: {reset_link}\n")
        return False