# Getting Started with AcquireMock

This guide will help you integrate AcquireMock into your application in under 10 minutes.

## Prerequisites

- Python 3.11+ or Docker
- Basic understanding of REST APIs
- A webhook endpoint (optional, can use webhook.site for testing)

## Quick Start

### Option 1: Using Docker (Recommended)

```bash
# Clone the repository
git clone https://github.com/illusiOxd/acquiremock.git
cd acquiremock

# Start the service
docker-compose up -d

# Check if it's running
curl http://localhost:8000/health
```

### Option 2: Manual Installation

```bash
# Clone and setup
git clone https://github.com/illusiOxd/acquiremock.git
cd acquiremock

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
nano .env  # Edit your settings

# Run database migrations
# (Tables are created automatically on first run)

# Start the server
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## Creating Your First Payment

### 1. Create a Payment Invoice

```bash
curl -X POST http://localhost:8000/api/create-invoice \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 10000,
    "reference": "ORDER-123",
    "webhookUrl": "https://webhook.site/your-unique-id",
    "redirectUrl": "https://yoursite.com/success"
  }'
```

**Response:**
```json
{
  "pageUrl": "http://localhost:8000/checkout/abc-123-def"
}
```

### 2. Redirect User to Payment Page

Open the `pageUrl` in a browser. The user will see a professional checkout page.

### 3. Test Payment

Use these test credentials:

| Field | Value |
|-------|-------|
| Card Number | `4444 4444 4444 4444` |
| Expiry | Any future date (e.g., `12/25`) |
| CVV | Any 3 digits (e.g., `123`) |

**Note:** Any other card number will result in "Insufficient Funds" error.

### 4. OTP Verification

After submitting the card, an OTP code will be sent:
- **If SMTP is configured:** Code sent to email
- **If SMTP is NOT configured:** Code printed to console logs

Check your terminal for output like:
```
🔐 OTP Code for user@example.com: 1234
```

### 5. Receive Webhook Notification

After successful payment, AcquireMock will send a webhook to your `webhookUrl`:

```json
{
  "payment_id": "abc-123-def",
  "reference": "ORDER-123",
  "amount": 10000,
  "status": "paid",
  "timestamp": "2025-01-15T10:30:00Z",
  "card_mask": "**** 4444"
}
```

**Headers:**
```
X-Signature: hmac-sha256-signature
X-Payment-ID: abc-123-def
Content-Type: application/json
```

## Verifying Webhook Signatures

Always verify webhook signatures to ensure requests come from AcquireMock:

```python
import hmac
import hashlib
import json

def verify_webhook(payload: dict, signature: str, secret: str) -> bool:
    message = json.dumps(payload, sort_keys=True)
    expected = hmac.new(
        secret.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)

# In your webhook handler
@app.post("/webhook")
async def payment_webhook(request: Request):
    signature = request.headers.get("X-Signature")
    payload = await request.json()
    
    if not verify_webhook(payload, signature, WEBHOOK_SECRET):
        return {"error": "Invalid signature"}, 403
    
    # Process payment
    if payload["status"] == "paid":
        # Update order status in your database
        pass
    
    return {"status": "ok"}
```

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | - | Database connection string |
| `WEBHOOK_SECRET` | Yes | - | Secret key for webhook signatures (min 32 chars) |
| `BASE_URL` | Yes | `http://localhost:8000` | Your application base URL |
| `CURRENCY_CODE` | No | `USD` | Currency code (USD, EUR, UAH, etc.) |
| `CURRENCY_SYMBOL` | No | `$` | Currency symbol |
| `SMTP_HOST` | No | - | SMTP server for emails |
| `SMTP_PORT` | No | - | SMTP port (usually 587) |
| `SMTP_USER` | No | - | SMTP username |
| `SMTP_PASS` | No | - | SMTP password |

### Generating Webhook Secret

```bash
# Linux/macOS
openssl rand -hex 32

# Python
python -c "import secrets; print(secrets.token_hex(32))"
```

## Testing Interactive UI

AcquireMock includes a built-in test page:

1. Visit `http://localhost:8000/test`
2. Fill in the form with test data
3. Click "Create Invoice"
4. You'll get a payment link to test the full flow

## Email Configuration

### Gmail Example

1. Enable 2-Factor Authentication in your Google Account
2. Generate an App Password: https://myaccount.google.com/apppasswords
3. Add to `.env`:

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASS=your-16-char-app-password
```

### Testing Without Email

If you don't configure SMTP, OTP codes will be printed to console:

```bash
# Watch the logs
docker-compose logs -f app

# Or if running manually
# Just look at your terminal output
```

## Payment Flow Diagram

```
User → Your Site → AcquireMock API
                        ↓
                  Create Invoice
                        ↓
                  Return pageUrl
                        ↓
User → Payment Page → Enter Card
                        ↓
                    Send OTP
                        ↓
                  Verify OTP
                        ↓
                Update Status
                        ↓
              ┌─────────┴─────────┐
              ↓                   ↓
        Send Webhook         Redirect User
              ↓                   ↓
        Your Server          Success Page
```

## Common Issues

### "Connection Refused" Error

Make sure the server is running:
```bash
curl http://localhost:8000/health
```

### OTP Not Received

Check if SMTP is configured. If not, check console logs:
```bash
docker-compose logs -f app | grep "OTP"
```

### Webhook Not Delivered

- Check your webhook URL is publicly accessible
- Use https://webhook.site for testing
- Check firewall/network settings
- Review webhook logs in database table `webhook_logs`

## Next Steps

- [API Reference](./api-reference.md) - Complete API documentation
- [Webhook Guide](./webhook-guide.md) - Advanced webhook handling
- [Examples](./examples/) - Integration examples in different languages
- [Migration Guide](./migration-guide.md) - Moving to production PSP

## Support

- **Issues:** https://github.com/illusiOxd/acquiremock/issues
- **Discussions:** https://github.com/illusiOxd/acquiremock/discussions
- **Email:** support@acquiremock.dev (if available)

---

**Ready to integrate?** Check out our [integration examples](./examples/) for your programming language.