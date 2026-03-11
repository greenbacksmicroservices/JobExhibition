# Email OTP API - Postman Testing Guide

## API Endpoint

**URL:** `http://localhost:8000/api/test-email-otp/`

**Method:** `POST`

**Content-Type:** `application/json`

---

## Quick Test with Postman

### Step 1: Create New Request

1. Open Postman
2. Click **New Request** (or `+` button)
3. Set method to **POST**
4. Enter URL: `http://localhost:8000/api/test-email-otp/`

### Step 2: Configure Headers

Click on **Headers** tab and add:

```
Content-Type: application/json
```

### Step 3: Add Request Body

Click on **Body** tab → Select **raw** → Choose **JSON** from dropdown

Add this JSON:

```json
{
    "email": "your-email@example.com",
    "name": "Your Name"
}
```

**Example:**
```json
{
    "email": "test@gmail.com",
    "name": "John Doe"
}
```

### Step 4: Send Request

Click **Send** button

---

## Expected Responses

### ✅ Success Response (200 OK)

```json
{
    "success": true,
    "message": "OTP sent successfully to test@gmail.com",
    "debug_otp": "123456",
    "note": "OTP shown because DEBUG=True. In production, this will not be included."
}
```

**Note:** The `debug_otp` field is only included when `DEBUG=True` (development mode).

### ❌ Error Responses

**Missing Email (400 Bad Request):**
```json
{
    "success": false,
    "error": "Email address is required"
}
```

**Invalid JSON (400 Bad Request):**
```json
{
    "success": false,
    "error": "Invalid JSON format"
}
```

**SMTP Error (500 Internal Server Error):**
```json
{
    "success": false,
    "error": "Unable to connect to email server. Please try again."
}
```

---

## GET Request (API Documentation)

You can also send a **GET** request to see API documentation:

**URL:** `http://localhost:8000/api/test-email-otp/`

**Method:** `GET`

**Response:**
```json
{
    "endpoint": "/api/test-email-otp/",
    "method": "POST",
    "description": "Test API endpoint for sending email OTP via SMTP",
    "request_body": {
        "email": "recipient@example.com (required)",
        "name": "Recipient Name (optional)"
    },
    "response_success": {
        "success": true,
        "message": "OTP sent successfully",
        "debug_otp": "123456 (only in DEBUG mode)"
    },
    "response_error": {
        "success": false,
        "error": "Error message"
    },
    "smtp_config": {
        "host": "smtp.hostinger.com",
        "port": 465,
        "from_email": "SabkaPaisa <registration@sabkapaisa.com>"
    }
}
```

---

## cURL Commands

If you prefer command line testing:

### POST Request (Send OTP)

```bash
curl -X POST http://localhost:8000/api/test-email-otp/ ^
  -H "Content-Type: application/json" ^
  -d "{\"email\": \"test@gmail.com\", \"name\": \"Test User\"}"
```

### GET Request (API Info)

```bash
curl http://localhost:8000/api/test-email-otp/
```

---

## Postman Collection

You can import this collection into Postman:

```json
{
    "info": {
        "name": "JobExhibition Email OTP API",
        "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
    },
    "item": [
        {
            "name": "Send Email OTP",
            "request": {
                "method": "POST",
                "header": [
                    {
                        "key": "Content-Type",
                        "value": "application/json"
                    }
                ],
                "body": {
                    "mode": "raw",
                    "raw": "{\n    \"email\": \"{{test_email}}\",\n    \"name\": \"{{test_name}}\"\n}"
                },
                "url": {
                    "raw": "http://localhost:8000/api/test-email-otp/",
                    "protocol": "http",
                    "host": ["localhost"],
                    "port": "8000",
                    "path": ["api", "test-email-otp", ""]
                }
            }
        },
        {
            "name": "Get API Info",
            "request": {
                "method": "GET",
                "header": [],
                "url": {
                    "raw": "http://localhost:8000/api/test-email-otp/",
                    "protocol": "http",
                    "host": ["localhost"],
                    "port": "8000",
                    "path": ["api", "test-email-otp", ""]
                }
            }
        }
    ],
    "variable": [
        {
            "key": "test_email",
            "value": "test@example.com"
        },
        {
            "key": "test_name",
            "value": "Test User"
        }
    ]
}
```

**To Import:**
1. Copy the JSON above
2. In Postman, click **Import** (top left)
3. Select **Raw text**
4. Paste the JSON
5. Click **Continue** → **Import**

---

## Testing Checklist

- [ ] Server is running on `http://localhost:8000`
- [ ] SMTP settings are configured in `.env` or `settings.py`
- [ ] Email address is valid
- [ ] Request body is valid JSON
- [ ] Content-Type header is set to `application/json`

---

## Troubleshooting

### Issue: "Connection refused"
**Solution:** Make sure Django server is running:
```bash
python manage.py runserver
```

### Issue: "Unable to connect to email server"
**Solution:** Check SMTP settings in `settings.py`:
```python
EMAIL_HOST = "smtp.hostinger.com"
EMAIL_PORT = 465
EMAIL_HOST_USER = "registration@sabkapaisa.com"
EMAIL_HOST_PASSWORD = "Admin$12345"
EMAIL_USE_SSL = True
```

### Issue: "Authentication failed"
**Solution:** Verify email credentials are correct and the email account exists on Hostinger.

### Issue: 404 Not Found
**Solution:** Make sure the URL is correct: `http://localhost:8000/api/test-email-otp/`

---

## Email Template Preview

When the OTP email is sent, it will look like this:

```
┌─────────────────────────────────────────┐
│  🔐 Your OTP Code                       │
│  (Purple gradient header)               │
├─────────────────────────────────────────┤
│                                         │
│  Hello John Doe,                        │
│                                         │
│  You requested a One-Time Password      │
│  (OTP) for your account.                │
│                                         │
│  Use the following OTP to complete      │
│  your verification:                     │
│                                         │
│         ┌─────────────┐                 │
│         │  1 2 3 4 5 6 │  (Large box)   │
│         └─────────────┘                 │
│                                         │
│  ⚠️ Security Notice:                    │
│  • This OTP is valid for 10 minutes     │
│  • Do not share this code with anyone   │
│  • If you didn't request this, ignore   │
│                                         │
│  Best regards,                          │
│  SabkaPaisa Team                        │
└─────────────────────────────────────────┘
```

---

## Production Notes

When deploying to production:

1. **Set `DEBUG=False`** in settings
2. **OTP will NOT be shown** in API response
3. **Use environment variables** for SMTP credentials
4. **Enable HTTPS** for secure transmission
5. **Rate limit** the API to prevent abuse

---

## Additional Endpoints

### Forgot Password (Web Form)
**URL:** `http://localhost:8000/forgot-password/`
**Method:** `POST` (form submission)
**Purpose:** Production password reset flow

### Verify OTP (Registration)
**URL:** `http://localhost:8000/otp/verify/`
**Method:** `POST`
**Purpose:** Verify OTP during user registration

---

**Last Updated:** March 11, 2026  
**Status:** ✅ Ready to Test  
**Server:** http://localhost:8000
