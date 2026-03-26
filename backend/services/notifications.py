"""
SendGrid (email) + Twilio (SMS) notification service.
"""
import os
import logging
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, To, From, Subject, HtmlContent
from twilio.rest import Client as TwilioClient

logger = logging.getLogger(__name__)


def _build_email_html(patient: dict, doctor: dict, slot: dict) -> str:
    return f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #0a0f1e; color: #e2e8f0; margin: 0; padding: 0; }}
    .container {{ max-width: 560px; margin: 40px auto; background: rgba(255,255,255,0.05);
                  border: 1px solid rgba(255,255,255,0.12); border-radius: 16px;
                  overflow: hidden; }}
    .header {{ background: linear-gradient(135deg, #0f766e, #0891b2);
               padding: 32px; text-align: center; }}
    .header h1 {{ color: white; margin: 0; font-size: 24px; font-weight: 700; }}
    .body {{ padding: 32px; }}
    .card {{ background: rgba(20, 184, 166, 0.1); border: 1px solid rgba(20,184,166,0.3);
             border-radius: 12px; padding: 20px; margin: 20px 0; }}
    .label {{ color: #94a3b8; font-size: 12px; text-transform: uppercase;
              letter-spacing: 0.05em; margin-bottom: 4px; }}
    .value {{ color: #f1f5f9; font-size: 16px; font-weight: 600; }}
    .footer {{ padding: 24px 32px; border-top: 1px solid rgba(255,255,255,0.08);
               color: #64748b; font-size: 13px; text-align: center; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>◈ Kyron Medical</h1>
      <p style="color:rgba(255,255,255,0.8); margin:8px 0 0;">Appointment Confirmed</p>
    </div>
    <div class="body">
      <p>Hi {patient['first_name']},</p>
      <p>Your appointment has been successfully scheduled. Here are your details:</p>
      <div class="card">
        <div class="label">Patient</div>
        <div class="value">{patient['first_name']} {patient['last_name']}</div>
        <div style="color:#94a3b8; font-size:14px; margin-top:4px;">Patient ID: {patient.get('patient_id', 'N/A')}</div>
      </div>
      <div class="card">
        <div class="label">Doctor</div>
        <div class="value">{doctor['name']}</div>
        <div style="color:#94a3b8; font-size:14px; margin-top:4px;">{doctor['specialty']}</div>
      </div>
      <div class="card">
        <div class="label">Date & Time</div>
        <div class="value">{slot['display_date']} at {slot['time']}</div>
      </div>
      <div class="card">
        <div class="label">Location</div>
        <div class="value">Kyron Medical Group</div>
        <div style="color:#94a3b8; font-size:14px; margin-top:4px;">
          1250 Medical Center Drive, Suite 400, Houston, TX 77030
        </div>
      </div>
      <p style="color:#94a3b8; font-size:14px;">
        Please arrive 15 minutes early to complete any remaining paperwork.
        If you need to reschedule, call us at (713) 555-0192.
      </p>
    </div>
    <div class="footer">
      Kyron Medical Group · 1250 Medical Center Drive, Houston TX 77030<br>
      This is an automated message. Please do not reply to this email.
    </div>
  </div>
</body>
</html>
"""


async def send_confirmation_email(patient: dict, doctor: dict, slot: dict) -> bool:
    try:
        sg = SendGridAPIClient(os.environ["SENDGRID_API_KEY"])
        message = Mail(
            from_email=From(os.environ["SENDGRID_FROM_EMAIL"], "Kyron Medical"),
            to_emails=To(patient["email"], f"{patient['first_name']} {patient['last_name']}"),
            subject=Subject(f"Appointment Confirmed – {slot['display_date']} with {doctor['name']}"),
            html_content=HtmlContent(_build_email_html(patient, doctor, slot)),
        )
        sg.send(message)
        logger.info("Confirmation email sent to %s", patient["email"])
        return True
    except Exception as e:
        logger.error("Email send failed: %s", e)
        return False


async def send_confirmation_sms(patient: dict, doctor: dict, slot: dict) -> bool:
    try:
        client = TwilioClient(os.environ["TWILIO_ACCOUNT_SID"], os.environ["TWILIO_AUTH_TOKEN"])
        body = (
            f"Hi {patient['first_name']}! Your appointment with {doctor['name']} "
            f"({doctor['specialty']}) is confirmed for {slot['display_date']} at {slot['time']}. "
            f"Kyron Medical Group — (713) 555-0192. Reply STOP to opt out."
        )
        client.messages.create(
            body=body,
            from_=os.environ["TWILIO_PHONE_NUMBER"],
            to=patient["phone"],
        )
        logger.info("Confirmation SMS sent to %s", patient["phone"])
        return True
    except Exception as e:
        logger.error("SMS send failed: %s", e)
        return False
