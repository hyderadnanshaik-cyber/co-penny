import os
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "465"))
        self.sender_email = os.getenv("SMTP_USER")
        self.password = os.getenv("SMTP_PASSWORD")
        self.enabled = bool(self.sender_email and self.password)

    def send_alert(self, to_email: str, subject: str, body: str) -> bool:
        """
        Send an email alert.
        Returns True if successful, False otherwise.
        """
        if not self.enabled:
            logger.warning("Email service disabled. SMTP_USER or SMTP_PASSWORD not set.")
            return False

        message = MIMEMultipart()
        message["From"] = self.sender_email
        message["To"] = to_email
        message["Subject"] = subject
        message.attach(MIMEText(body, "plain"))

        try:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port, context=context) as server:
                server.login(self.sender_email, self.password)
                server.sendmail(self.sender_email, to_email, message.as_string())
            logger.info(f"Email sent to {to_email}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
