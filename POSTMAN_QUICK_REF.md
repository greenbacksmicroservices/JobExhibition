# 📬 Email OTP API - Quick Reference

## ✅ API is Ready!

**Server:** http://localhost:8000  
**API Endpoint:** http://localhost:8000/api/test-email-otp/

---

## 🚀 Test with Postman

### 1. Create Request

- **Method:** `POST`
- **URL:** `http://localhost:8000/api/test-email-otp/`

### 2. Headers

```
Content-Type: application/json
```

### 3. Body (raw JSON)

```json
{
    "email": "your-email@example.com",
    "name": "Your Name"
}
```

### 4. Click Send!

---

## 📊 Example Request/Response

### Request
```http
POST /api/test-email-otp/ HTTP/1.1
Host: localhost:8000
Content-Type: application/json

{
    "email": "test@gmail.com",
    "name": "John Doe"
}
```

### Response (Success)
```json
{
    "success": true,
    "message": "OTP sent successfully to test@gmail.com",
    "debug_otp": "582941",
    "note": "OTP shown because DEBUG=True. In production, this will not be included."
}
```

### Response (Error)
```json
{
    "success": false,
    "error": "Email address is required"
}
```

---

## 📝 cURL Command

```bash
curl -X POST http://localhost:8000/api/test-email-otp/ ^
  -H "Content-Type: application/json" ^
  -d "{\"email\": \"test@gmail.com\", \"name\": \"Test User\"}"
```

---

## 🔧 SMTP Configuration

Your PHP credentials are configured:

| Setting | Value |
|---------|-------|
| **Host** | smtp.hostinger.com |
| **Port** | 465 |
| **Username** | registration@sabkapaisa.com |
| **Password** | Admin$12345 |
| **Encryption** | SSL |

---

## 📁 Files Created/Modified

1. **New:** `dashboard/otp/email.py` - Email OTP module
2. **New:** `API_TEST_GUIDE.md` - Detailed Postman guide
3. **New:** `SMTP_SETUP.md` - SMTP configuration docs
4. **Updated:** `jobexhibition/settings.py` - SMTP settings
5. **Updated:** `dashboard/views.py` - API endpoint added
6. **Updated:** `dashboard/urls.py` - Route added
7. **Updated:** `.env.example` - SMTP defaults

---

## ✨ Features

- ✅ HTML email template (matching your PHP design)
- ✅ SMTP authentication with your credentials
- ✅ Debug mode shows OTP in response
- ✅ Error handling and logging
- ✅ GET request returns API documentation

---

## 🔍 Test API Info (GET)

```bash
curl http://localhost:8000/api/test-email-otp/
```

Returns API documentation and current SMTP configuration.

---

**Status:** ✅ Server Running  
**Time:** March 11, 2026  
**Port:** 8000
