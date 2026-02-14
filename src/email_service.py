import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv
from utils.logger import setup_logger

logger = setup_logger("email_service")

class EmailService:
    """
    Handles sending Pulse reports via SMTP.
    """
    
    @staticmethod
    def send_email(to_email: str, subject: str, html_content: str) -> bool:
        """
        Sends an HTML email to the specified recipient.
        """
        # Force reload .env to ensure any manual changes by user are picked up
        load_dotenv(override=True)
        
        smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_user = os.getenv("SMTP_USERNAME", "").strip()
        # Gmail App passwords often have spaces in UI, but smtplib needs them stripped.
        smtp_pass = os.getenv("SMTP_PASSWORD", "").replace(" ", "").strip()
        from_email = os.getenv("EMAIL_FROM", smtp_user).strip()

        if not smtp_user or not smtp_pass:
            logger.error("SMTP credentials (USERNAME or PASSWORD) are missing from .env")
            return False

        # Debug log (Safe: only show length and first/last char)
        user_mask = f"{smtp_user[0]}...{smtp_user[-1]}" if len(smtp_user) > 2 else "???"
        pass_mask = f"{smtp_pass[0]}...{smtp_pass[-1]}" if len(smtp_pass) > 2 else "???"
        logger.info(f"Attempting SMTP Login: User={user_mask}, Server={smtp_server}:{smtp_port}")
        logger.info(f"Password Length confirmed: {len(smtp_pass)} chars")

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = from_email
        msg["To"] = to_email

        # Attach HTML part
        part = MIMEText(html_content, "html")
        msg.attach(part)

        try:
            # First attempt with Port 587 (TLS)
            logger.info(f"Attempting connection via Port {smtp_port}...")
            server = smtplib.SMTP(smtp_server, smtp_port, timeout=15)
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(from_email, to_email, msg.as_string())
            server.quit()
            logger.info(f"Email successfully sent to {to_email} via port {smtp_port}")
            return True
        except (smtplib.SMTPAuthenticationError, smtplib.SMTPException) as e:
            logger.warning(f"Failed via port {smtp_port}: {e}. Trying fallback Port 465 (SSL)...")
            try:
                # Fallback attempt with Port 465 (SSL)
                server = smtplib.SMTP_SSL(smtp_server, 465, timeout=15)
                server.login(smtp_user, smtp_pass)
                server.sendmail(from_email, to_email, msg.as_string())
                server.quit()
                logger.info(f"Email successfully sent to {to_email} via port 465")
                return True
            except Exception as e_ssl:
                logger.error(f"Final failure after testing both ports. SSL Error: {e_ssl}")
                return False
        except Exception as e:
            logger.error(f"Unexpected error in send_email: {e}")
            return False
