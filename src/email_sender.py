"""Sends the compiled PDF report over Gmail SMTP (app password auth)."""
import os
import smtplib
from email.message import EmailMessage

from . import config

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465


def send_report(pdf_path, contract_count):
    if not config.RECIPIENT_EMAILS:
        raise RuntimeError("RECIPIENT_EMAILS is empty; refusing to send with no recipients.")

    msg = EmailMessage()
    msg["Subject"] = f"SAM.gov IT Contract Monitor — {contract_count} new match(es)"
    msg["From"] = config.GMAIL_ADDRESS
    msg["To"] = ", ".join(config.RECIPIENT_EMAILS)
    msg.set_content(
        f"{contract_count} new contract opportunity(ies) cleared Stage 1 screening "
        f"(score >= {config.STAGE1_THRESHOLD}) and were run through full capture analysis.\n\n"
        "See the attached PDF for the full reports."
    )

    with open(pdf_path, "rb") as f:
        msg.add_attachment(
            f.read(), maintype="application", subtype="pdf",
            filename=os.path.basename(pdf_path),
        )

    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as smtp:
        smtp.login(config.GMAIL_ADDRESS, config.GMAIL_APP_PASSWORD)
        smtp.send_message(msg)
