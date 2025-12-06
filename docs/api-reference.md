# API Reference

Complete API documentation for AcquireMock Payment Gateway.

## Base URL

```
http://localhost:8000
```

For production, replace with your actual domain.

## Authentication

AcquireMock doesn't require API keys for invoice creation. Security is enforced through:
- HMAC-SHA256 webhook signatures
- CSRF tokens for payment forms
- Rate limiting (5 requests/minute per IP)

---

## Endpoints

### Create Invoice

Create a new payment invoice and get a checkout URL.

**Endpoint:** `POST /api/create-invoice`

**Request Body:**

```json
{
  "amount": 10000,
  "reference": "ORDER-123",
  "webhookUrl": "https://yoursite.com/webhook",
  "redirectUrl": "https://yoursite.com/success"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `amount` | integer | Yes | Amount in smallest currency unit (e.g., cents) |
| `reference` | string | Yes | Your unique order reference |
| `webhookUrl` | string | Yes | URL to receive payment notifications |
| `redirectUrl` | string | Yes | URL to redirect user after payment |

**Response:** `200 OK`

```json
{
  "pageUrl": "http://localhost:8000/checkout/550e8400-e29b-41d4-a716-446655440000"
}
```

**Errors:**

- `400 Bad Request` - Invalid input data
- `429 Too Many Requests` - Rate limit exceeded

**Example:**

```bash
curl -X POST http://localhost:8000/api/create-invoice \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 25000,
    "reference": "ORDER-456",
    "webhookUrl": "https://api.mystore.com/webhook",
    "redirectUrl": "https://mystore.com/order/success"
  }'
```

---

### Health Check

Check API health status.

**Endpoint:** `GET /health`

**Response:** `200 OK`

```json
{
  "status": "ok",
  "timestamp": "2025-01-15T10:30:00.000000",
  "version": "2.0.0",
  "currency": "USD"
}
```

**Example:**

```bash
curl http://localhost:8000/health
```

---

### Verify Webhook Signature

Utility endpoint to verify webhook signature calculation.

**Endpoint:** `POST /webhooks/verify`

**Headers:**
```
X-Signature: your-calculated-signature
```

**Request Body:**
```json
{
  "payment_id": "abc-123",
  "status": "paid",
  "amount": 10000
}
```

**Response:** `200 OK`

```json
{
  "valid": true
}
```

**Example:**

```bash
curl -X POST http://localhost:8000/webhooks/verify \
  -H "Content-Type: application/json" \
  -H "X-Signature: a1b2c3d4..." \
  -d '{"payment_id":"123","status":"paid","amount":10000}'
```

---

## Webhook Events

After payment completion, AcquireMock sends a POST request to your `webhookUrl`.

### Webhook Payload

```json
{
  "payment_id": "550e8400-e29b-41d4-a716-446655440000",
  "reference": "ORDER-123",
  "amount": 10000,
  "status": "paid",
  "timestamp": "2025-01-15T10:30:00.000000",
  "card_mask": "**** 4444"
}
```

### Webhook Headers

```
Content-Type: application/json
X-Signature: hmac-sha256-signature-here
X-Payment-ID: 550e8400-e29b-41d4-a716-446655440000
```

### Payment Statuses

| Status | Description |
|--------|-------------|
| `pending` | Payment created, awaiting card details |
| `waiting_for_otp` | Card submitted, waiting for OTP verification |
| `paid` | Payment successfully completed |
| `failed` | Payment failed (insufficient funds, etc.) |
| `expired` | Payment session expired (15 minutes) |
| `refunded` | Payment refunded (future feature) |

### Signature Verification

**Algorithm:** HMAC-SHA256

**Message:** JSON payload with sorted keys

**Secret:** Your `WEBHOOK_SECRET` from environment variables

**Python Example:**

```python
import hmac
import hashlib
import json

def verify_webhook_signature(payload: dict, signature: str, secret: str) -> bool:
    """Verify webhook signature."""
    message = json.dumps(payload, sort_keys=True)
    expected_signature = hmac.new(
        secret.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected_signature, signature)
```

**Node.js Example:**

```javascript
const crypto = require('crypto');

function verifyWebhookSignature(payload, signature, secret) {
  const message = JSON.stringify(payload, Object.keys(payload).sort());
  const expectedSignature = crypto
    .createHmac('sha256', secret)
    .update(message)
    .digest('hex');
  return crypto.timingSafeEqual(
    Buffer.from(signature),
    Buffer.from(expectedSignature)
  );
}
```

### Webhook Retry Logic

If webhook delivery fails, AcquireMock automatically retries:

| Attempt | Delay |
|---------|-------|
| 1 | Immediate |
| 2 | 2 seconds |
| 3 | 4 seconds |
| 4 | 8 seconds |
| 5 | 16 seconds |

**Maximum attempts:** 5

**Your webhook endpoint should:**
- Return `200-299` status code for success
- Respond within 10 seconds
- Be idempotent (handle duplicate webhooks)

### Webhook Response

Your endpoint should return a success response:

```json
{
  "status": "ok"
}
```

Or any 2xx status code. Failed webhooks (4xx, 5xx, timeout) will be retried.

---

## Error Codes

| Code | Message | Description |
|------|---------|-------------|
| `PAYMENT_NOT_FOUND` | Payment not found | Invalid payment ID |
| `PAYMENT_ALREADY_PROCESSED` | Payment already processed | Payment is already paid/failed |
| `PAYMENT_EXPIRED` | Payment session expired | 15-minute window exceeded |
| `INSUFFICIENT_FUNDS` | Insufficient funds | Invalid card or test card failed |
| `INVALID_OTP` | Invalid OTP code | Wrong verification code entered |
| `CSRF_TOKEN_MISMATCH` | CSRF validation failed | Security token mismatch |
| `SAVED_CARD_NOT_FOUND` | Saved card not found | Requested card doesn't exist |

### Error Response Format

```json
{
  "error": "PAYMENT_EXPIRED",
  "message": "Payment session has expired",
  "payment_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

---

## Rate Limits

| Endpoint | Limit |
|----------|-------|
| `/api/create-invoice` | 10/minute per IP |
| `/pay/*` | 5/minute per IP |
| All others | 100/minute per IP |

**Rate Limit Headers:**

```
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 7
X-RateLimit-Reset: 1642252800
```

When exceeded, you'll receive:

```json
{
  "error": "Rate limit exceeded",
  "retry_after": 60
}
```

---

## Idempotency

Use the `Idempotency-Key` header to prevent duplicate payments:

```bash
curl -X POST /pay/abc-123 \
  -H "Idempotency-Key: unique-key-12345" \
  -d "card_number=4444444444444444&..."
```

If you retry with the same key:
- Same `payment_id`: Returns existing payment result
- Different `payment_id`: Processes normally

**Best Practice:** Use UUID or order ID + timestamp.

---

## Testing

### Test Card Numbers

| Card Number | Result |
|-------------|--------|
| `4444 4444 4444 4444` | Success (with OTP) |
| Any other number | Insufficient Funds |

### Test OTP Codes

If SMTP is not configured, OTP codes are logged to console. Otherwise, check your email.

### Webhook Testing

Use https://webhook.site to get a unique webhook URL for testing:

1. Visit https://webhook.site
2. Copy your unique URL
3. Use it as `webhookUrl` in invoice creation
4. View received webhooks in real-time

---

## SDKs & Libraries

### Official

- Python SDK: Coming soon
- Node.js SDK: Coming soon

### Community

Check our [GitHub Discussions](https://github.com/illusiOxd/acquiremock/discussions) for community-maintained SDKs.

---

## Postman Collection

Import our Postman collection for quick testing:

```bash
# Download collection
curl -O https://raw.githubusercontent.com/illusiOxd/acquiremock/main/postman_collection.json

# Import in Postman and set variables:
# - base_url: http://localhost:8000
# - webhook_secret: your-secret-key
```

---

## OpenAPI Specification

View interactive API docs:

```
http://localhost:8000/docs        # Swagger UI
http://localhost:8000/redoc       # ReDoc
http://localhost:8000/openapi.json # OpenAPI JSON
```

---

## Support

- **Issues:** [GitHub Issues](https://github.com/illusiOxd/acquiremock/issues)
- **Questions:** [GitHub Discussions](https://github.com/illusiOxd/acquiremock/discussions)

---

**Next:** [Webhook Integration Guide](./webhook-guide.md)