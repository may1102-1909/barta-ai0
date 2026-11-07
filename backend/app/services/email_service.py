import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
import resend
from app.config import settings

logger = logging.getLogger(__name__)

class EmailService:
    @staticmethod
    async def send_order_form_email(
        to_email: str,
        customer_name: str,
        product_name: str,
        price: float,
        form_url: str
    ) -> bool:
        """
        Sends an elegant order confirmation email containing the hosted link 
        where the customer fills in their delivery address and payment choice.
        """
        subject = f"Order Confirmation: Complete Your Delivery Details for {product_name}"
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
          <meta charset="utf-8">
          <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 20px; }}
            .container {{ max-width: 580px; margin: 0 auto; background: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; overflow: hidden; }}
            .header {{ background-color: #0f172a; padding: 24px; text-align: center; color: #ffffff; }}
            .header h1 {{ margin: 0; font-size: 20px; letter-spacing: 1px; font-weight: 600; }}
            .header p {{ margin: 4px 0 0; font-size: 13px; color: #94a3b8; }}
            .body {{ padding: 32px 24px; color: #334155; line-height: 1.6; }}
            .card {{ background: #f1f5f9; border-radius: 8px; padding: 16px; margin: 20px 0; }}
            .btn {{ display: inline-block; background-color: #0f172a; color: #ffffff !important; text-decoration: none; padding: 14px 28px; border-radius: 8px; font-weight: 600; font-size: 15px; margin-top: 10px; text-align: center; }}
            .footer {{ padding: 20px 24px; text-align: center; font-size: 12px; color: #94a3b8; border-top: 1px solid #e2e8f0; }}
          </style>
        </head>
        <body>
          <div class="container">
            <div class="header">
              <h1>CURATED INDIA</h1>
              <p>Handcrafted Indian Fashion</p>
            </div>
            <div class="body">
              <p>Namaste <strong>{customer_name}</strong>,</p>
              <p>Thank you for speaking with our voice assistant, BARTA. We are thrilled to confirm your reserved item from our festive catalog!</p>
              
              <div class="card">
                <div style="font-size: 15px; font-weight: 600; color: #0f172a;">{product_name}</div>
                <div style="font-size: 18px; font-weight: 700; color: #0f172a; margin-top: 6px;">₹{int(price)} <span style="font-size: 13px; color: #16a34a; font-weight: 500;">(Exclusive Festival Price)</span></div>
                <div style="font-size: 12px; color: #64748b; margin-top: 4px;">Free express shipping & 7-day hassle-free returns</div>
              </div>

              <p>To finalize your shipment, please click the secure link below to specify your delivery address and choose either <strong>Cash on Delivery (COD)</strong> or <strong>Online UPI</strong>:</p>

              <div style="text-align: center; margin: 30px 0;">
                <a href="{form_url}" class="btn">Enter Delivery Address & Payment</a>
              </div>

              <p style="font-size: 13px; color: #64748b;">
                * This single-use link will expire in <strong>72 hours</strong>. If you did not request this order, simply ignore this email.
              </p>
            </div>
            <div class="footer">
              <p>CURATED India · Designed for Modern Living<br>Powered by BARTA ai Voice Platform</p>
            </div>
          </div>
        </body>
        </html>
        """

        # Try Resend first
        if settings.RESEND_API_KEY:
            try:
                resend.api_key = settings.RESEND_API_KEY
                params = {
                    "from": settings.EMAIL_FROM,
                    "to": [to_email],
                    "subject": subject,
                    "html": html_content
                }
                res = resend.Emails.send(params)
                logger.info(f"Sent email via Resend to {to_email}: {res}")
                return True
            except Exception as e:
                logger.error(f"Resend email sending failed: {e}. Trying SMTP fallback.")

        # Fallback to SMTP if configured
        if settings.SMTP_HOST and settings.SMTP_USER and settings.SMTP_PASSWORD:
            try:
                msg = MIMEMultipart("alternative")
                msg["Subject"] = subject
                msg["From"] = settings.EMAIL_FROM
                msg["To"] = to_email
                msg.attach(MIMEText(html_content, "html"))

                with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                    server.starttls()
                    server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                    server.send_message(msg)
                logger.info(f"Sent email via SMTP to {to_email}")
                return True
            except Exception as e:
                logger.error(f"SMTP email sending failed: {e}")

        logger.info(f"[SIMULATED EMAIL] To: {to_email} | Subject: {subject} | Form Link: {form_url}")
        return True

