# Webhook Integration Guide

Complete guide to handling webhooks from AcquireMock.

## Overview

Webhooks are HTTP callbacks that notify your server when payment events occur. AcquireMock sends webhooks to the URL you specify when creating an invoice.

## Webhook Flow

```
Payment Completed → AcquireMock → Your Webhook Endpoint
                         ↓
                    Retry if Failed
                         ↓
                    Log Result
```

## Receiving Webhooks

### Endpoint Requirements

Your webhook endpoint must:

1. **Accept POST requests** with JSON payload
2. **Respond within 10 seconds** (timeout)
3. **Return 2xx status code** for success (200, 201, 204)
4. **Be publicly accessible** (use ngrok for local testing)
5. **Be idempotent** (handle duplicate webhooks)

### Example Endpoint (FastAPI)

```python
from fastapi import FastAPI, Request, HTTPException
import hmac
import hashlib
import json

app = FastAPI()

WEBHOOK_SECRET = "your_secret_here"

@app.post("/webhook/payment")
async def payment_webhook(request: Request):
    # 1. Get signature from headers
    signature = request.headers.get("X-Signature")
    if not signature:
        raise HTTPException(status_code=403, detail="Missing signature")
    
    # 2. Get payload
    payload = await request.json()
    
    # 3. Verify signature
    if not verify_signature(payload, signature):
        raise HTTPException(status_code=403, detail="Invalid signature")
    
    # 4. Process webhook
    payment_id = payload["payment_id"]
    status = payload["status"]
    reference = payload["reference"]
    
    if status == "paid":
        # Update your database
        order = await get_order(reference)
        order.status = "paid"
        await order.save()
        
        # Send confirmation email
        await send_confirmation_email(order)
    
    # 5. Return success response
    return {"status": "ok"}

def verify_signature(payload: dict, signature: str) -> bool:
    """Verify HMAC-SHA256 signature."""
    message = json.dumps(payload, sort_keys=True)
    expected = hmac.new(
        WEBHOOK_SECRET.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)
```

## Webhook Payload

### Structure

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

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `payment_id` | string | Unique payment identifier (UUID) |
| `reference` | string | Your order reference from invoice creation |
| `amount` | integer | Payment amount in smallest currency unit |
| `status` | string | Payment status: `paid`, `failed`, `expired` |
| `timestamp` | string | ISO 8601 timestamp of the event |
| `card_mask` | string | Masked card number (e.g., `**** 4444`) |

### Status Values

| Status | When Sent | Action Required |
|--------|-----------|-----------------|
| `paid` | Payment successfully completed | Update order, send confirmation |
| `failed` | Payment failed (card declined) | Notify customer, retry payment |
| `expired` | Payment session expired (15min) | Cancel order or request new payment |

## Security

### Signature Verification

**Always verify the webhook signature** before processing!

#### Why?

- Prevents attackers from faking webhooks
- Ensures webhooks come from AcquireMock
- Protects against replay attacks

#### How It Works

1. AcquireMock creates HMAC-SHA256 signature using your `WEBHOOK_SECRET`
2. Signature is sent in `X-Signature` header
3. You calculate expected signature from payload
4. Compare signatures using constant-time comparison

#### Implementation Examples

**Python:**

```python
import hmac
import hashlib
import json

def verify_webhook_signature(payload: dict, signature: str, secret: str) -> bool:
    message = json.dumps(payload, sort_keys=True)
    expected = hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)
```

**Node.js:**

```javascript
const crypto = require('crypto');

function verifyWebhookSignature(payload, signature, secret) {
  const message = JSON.stringify(payload, Object.keys(payload).sort());
  const expected = crypto.createHmac('sha256', secret).update(message).digest('hex');
  return crypto.timingSafeEqual(Buffer.from(signature), Buffer.from(expected));
}
```

**PHP:**

```php
function verifyWebhookSignature($payload, $signature, $secret) {
    ksort($payload);
    $message = json_encode($payload);
    $expected = hash_hmac('sha256', $message, $secret);
    return hash_equals($expected, $signature);
}
```

**Ruby:**

```ruby
require 'openssl'
require 'json'

def verify_webhook_signature(payload, signature, secret)
  message = JSON.generate(payload.sort.to_h)
  expected = OpenSSL::HMAC.hexdigest('SHA256', secret, message)
  Rack::Utils.secure_compare(expected, signature)
end
```

### Important Notes

- ❌ **Never** use `==` for signature comparison (timing attacks)
- ✅ **Always** use constant-time comparison (`hmac.compare_digest`, `crypto.timingSafeEqual`, etc.)
- ✅ **Always** sort JSON keys before hashing
- ✅ Store `WEBHOOK_SECRET` securely (environment variables)

## Idempotency

### Why?

Webhooks may be delivered multiple times due to:
- Network issues
- Timeout on your server
- Retry logic

### How to Handle

```python
@app.post("/webhook/payment")
async def payment_webhook(request: Request):
    payload = await request.json()
    payment_id = payload["payment_id"]
    
    # Check if already processed
    if await is_webhook_processed(payment_id):
        return {"status": "ok", "message": "Already processed"}
    
    # Process webhook
    await process_payment(payload)
    
    # Mark as processed
    await mark_webhook_processed(payment_id)
    
    return {"status": "ok"}
```

### Best Practices

1. **Store webhook IDs** in database
2. **Check before processing** if webhook was already handled
3. **Use transactions** to ensure atomic operations
4. **Log all webhooks** for debugging

## Retry Logic

### How AcquireMock Retries

If your endpoint returns non-2xx status or times out:

| Attempt | Delay | Total Time |
|---------|-------|------------|
| 1 | Immediate | 0s |
| 2 | 2 seconds | 2s |
| 3 | 4 seconds | 6s |
| 4 | 8 seconds | 14s |
| 5 | 16 seconds | 30s |

After 5 failed attempts, webhook is marked as permanently failed.

### Monitoring Retries

Check the `webhook_logs` table in AcquireMock database:

```sql
SELECT * FROM webhook_logs 
WHERE success = false 
ORDER BY created_at DESC;
```

## Testing Webhooks Locally

### Using webhook.site

1. Go to https://webhook.site
2. Copy your unique URL
3. Use it when creating invoices:

```bash
curl -X POST http://localhost:8000/api/create-invoice \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 10000,
    "reference": "TEST-123",
    "webhookUrl": "https://webhook.site/your-unique-id",
    "redirectUrl": "http://localhost:3000/success"
  }'
```

4. View received webhooks in real-time at webhook.site

### Using ngrok

For testing with your local server:

1. **Install ngrok:**
   ```bash
   # macOS
   brew install ngrok
   
   # Linux
   wget https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.tgz
   tar xvzf ngrok-*.tgz
   ```

2. **Start your server:**
   ```bash
   python your_app.py  # Running on port 3000
   ```

3. **Create tunnel:**
   ```bash
   ngrok http 3000
   ```

4. **Use ngrok URL in webhook:**
   ```bash
   curl -X POST http://localhost:8000/api/create-invoice \
     -d '{"webhookUrl": "https://abc123.ngrok.io/webhook/payment", ...}'
   ```

5. **View requests in ngrok dashboard:**
   ```
   http://localhost:4040
   ```

## Advanced Patterns

### Webhook Queue

For high-volume applications, process webhooks asynchronously:

```python
import asyncio
from queue import Queue

webhook_queue = Queue()

@app.post("/webhook/payment")
async def payment_webhook(request: Request):
    payload = await request.json()
    
    # Verify signature
    if not verify_signature(payload, request.headers.get("X-Signature")):
        raise HTTPException(403, "Invalid signature")
    
    # Add to queue
    webhook_queue.put(payload)
    
    # Return immediately
    return {"status": "queued"}

# Background worker
async def process_webhook_queue():
    while True:
        if not webhook_queue.empty():
            payload = webhook_queue.get()
            await process_payment(payload)
        await asyncio.sleep(0.1)
```

### Webhook Forwarding

Forward webhooks to multiple services:

```python
WEBHOOK_TARGETS = [
    "https://api.mystore.com/webhook",
    "https://analytics.mysite.com/webhook",
    "https://slack.com/api/incoming/webhook"
]

@app.post("/webhook/payment")
async def payment_webhook(request: Request):
    payload = await request.json()
    
    # Forward to all targets
    async with httpx.AsyncClient() as client:
        tasks = [
            client.post(url, json=payload)
            for url in WEBHOOK_TARGETS
        ]
        await asyncio.gather(*tasks, return_exceptions=True)
    
    return {"status": "ok"}
```

## Troubleshooting

### Webhook Not Received

**Check:**
1. ✅ Webhook URL is publicly accessible
2. ✅ Server is running and listening
3. ✅ Firewall allows incoming connections
4. ✅ Check AcquireMock logs: `docker-compose logs -f`
5. ✅ Check webhook_logs table for errors

### Invalid Signature Error

**Check:**
1. ✅ Using correct `WEBHOOK_SECRET`
2. ✅ Sorting JSON keys before hashing
3. ✅ Using UTF-8 encoding
4. ✅ Not modifying payload before verification

### Webhooks Timing Out

**Check:**
1. ✅ Database queries are optimized
2. ✅ Not making slow external API calls
3. ✅ Processing in background if needed
4. ✅ Responding within 10 seconds

### Duplicate Webhooks

**Solution:**
Implement idempotency checks (see above).

## Webhook Monitoring

### Logging Best Practices

```python
import logging

logger = logging.getLogger(__name__)

@app.post("/webhook/payment")
async def payment_webhook(request: Request):
    payload = await request.json()
    payment_id = payload["payment_id"]
    
    logger.info(f"Webhook received: {payment_id}")
    
    try:
        # Process webhook
        await process_payment(payload)
        logger.info(f"Webhook processed: {payment_id}")
    except Exception as e:
        logger.error(f"Webhook failed: {payment_id}, error: {e}")
        raise
```

### Metrics to Track

- Total webhooks received
- Success rate
- Average processing time
- Failed webhooks by reason
- Retry counts

## Next Steps

- [API Reference](./api-reference.md) - Complete API documentation
- [Examples](../examples/) - Integration code examples
- [Getting Started](./getting-started.md) - Quick setup guide

---

**Need Help?**
- [GitHub Issues](https://github.com/illusiOxd/acquiremock/issues)
- [Discussions](https://github.com/illusiOxd/acquiremock/discussions)