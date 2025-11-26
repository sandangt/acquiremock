import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

SMTP_HOST = os.getenv('SMTP_HOST')
SMTP_PORT = os.getenv('SMTP_PORT')
SMTP_USER = os.getenv('SMTP_USER')
SMTP_PASS = os.getenv('SMTP_PASS')


def send_email(to_email, subject, html_content, text_content):
    msg = MIMEMultipart("alternative")
    msg['Subject'] = subject
    msg['From'] = SMTP_USER
    msg['To'] = to_email

    part1 = MIMEText(text_content, "plain", "utf-8")
    part2 = MIMEText(html_content, "html", "utf-8")

    msg.attach(part1)
    msg.attach(part2)

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_USER, [to_email], msg.as_string())
        print(f"Email sent to {to_email}")
    except Exception as e:
        print(f"Failed to send email: {e}")


def send_otp_email(to_email, otp_code):
    subject = "AcquireMock: Ваш код підтвердження"
    template_path = Path("templates/misc/email-letter.html")

    try:
        with open(template_path, "r", encoding="utf-8") as f:
            html_content = f.read()
    except FileNotFoundError:
        html_content = f"<h1>Code: {otp_code}</h1>"

    html_body = html_content.replace("{{ code }}", str(otp_code))
    text_body = f"Ваш код підтвердження: {otp_code}"

    send_email(to_email, subject, html_body, text_body)


def send_receipt_email(to_email, payment_data):
    subject = f"Чек про оплату замовлення #{payment_data.get('reference')}"
    template_path = Path("templates/misc/receipt.html")

    try:
        with open(template_path, "r", encoding="utf-8") as f:
            html_content = f.read()
    except FileNotFoundError:
        html_content = "<h1>Payment Successful</h1>"

    replacements = {
        "{{ amount }}": str(payment_data.get('amount')),
        "{{ reference }}": str(payment_data.get('reference')),
        "{{ date }}": datetime.now().strftime("%d.%m.%Y %H:%M"),
        "{{ card_mask }}": payment_data.get('card_mask', '****'),
        "{{ payment_id }}": payment_data.get('payment_id', '')
    }

    for key, value in replacements.items():
        html_content = html_content.replace(key, value)

    text_body = f"Оплата успішна. Сума: {payment_data.get('amount')} грн. Замовлення: {payment_data.get('reference')}"

    send_email(to_email, subject, html_content, text_body)


if __name__ == "__main__":
    send_otp_email("test@example.com", "1234")