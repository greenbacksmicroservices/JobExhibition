# 📱 Unified Login Page - Visual Guide

## Before vs After

### ❌ OLD SYSTEM (Separate Pages)

```
User Landing
    ├─ /dashboard/login/ → Admin Login Page
    │   └─ Admin credentials only
    │   └─ Separate UI design
    │
    └─ /dashboard/company/login/ → Company Login Page
        └─ Company credentials only
        └─ Different UI design
```

**Problems:**
- Confusing for new users (which page to use?)
- Maintenance overhead (2 templates)
- Inconsistent branding
- Users can't easily switch between roles

---

### ✅ NEW SYSTEM (Unified Page)

```
User Landing
    └─ /dashboard/login/ → Unified Login Page
        ├─ Tab 1: Admin
        │   └─ Admin credentials
        │   └─ Admin dashboard redirect
        │
        └─ Tab 2: Company
            └─ Company credentials
            └─ Company dashboard redirect
```

**Benefits:**
- Single entry point for all users
- Easy role switching (just click tab)
- Consistent design language
- Better user experience
- Easier maintenance

---

## 🎯 Page Layout

```
┌─────────────────────────────────────────────────┐
│                                                 │
│            Floating Skills Animation            │
│           (PHP, Laravel, Python, etc)           │
│                                                 │
│  ┌─────────────────────────────────────────┐   │
│  │         JobExhibition                    │   │
│  │    Admin & Company Portal                │   │
│  │                                          │   │
│  │  [Admin Tab] | [Company Tab]             │   │
│  │                                          │   │
│  │  ℹ️ Demo: admin / admin123               │   │
│  │                                          │   │
│  │  👤 [Username Input]                     │   │
│  │  🔑 [Password Input]  [Eye Icon]         │   │
│  │                                          │   │
│  │  ☐ Remember me   [Forgot Password?]     │   │
│  │                                          │   │
│  │  [Admin Login Button]                    │   │
│  │                                          │   │
│  │  Secure Access Portal • 2026             │   │
│  └─────────────────────────────────────────┘   │
│                                                 │
└─────────────────────────────────────────────────┘
```

---

## 🎨 Tab Switching Behavior

### Initial Load (Admin Tab Active)
```
[Admin Tab ━━━━━] [Company Tab]
├─ Username field
├─ Password field
├─ Demo badge: "admin / admin123"
└─ Submit: "Admin Login"
```

### After Clicking Company Tab
```
[Admin Tab] [Company Tab ━━━━━]
├─ Username field
├─ Password field
├─ Demo badge: "company1 / 123456789"
└─ Submit: "Company Login"
```

**Transition:** Smooth fade effect (0.3s)

---

## 🔐 Authentication Pathways

### Admin Login Flow
```
User enters credentials (admin / admin123)
    ↓
POST request with login_type=admin
    ↓
authenticate(request, username, password)
    ↓
Check: user.is_staff or user.is_superuser?
    ├─ YES: login() & redirect to /admin-dashboard/
    └─ NO: Show error message
```

### Company Login Flow
```
User enters credentials (company1 / 123456789)
    ↓
POST request with login_type=company
    ↓
Query Company model by name
    ├─ Found & password match?
    │  ├─ YES: Create session & redirect to /company/dashboard/
    │  └─ NO: Show error
    │
    └─ Not found & demo credentials?
       ├─ YES: Create demo company & session & redirect
       └─ NO: Show error
```

---

## 📱 Responsive Behavior

### Desktop (1200px+)
```
                    Login Card (440px)
                    Centered on page
                    Full animation
                    420px form width
```

### Tablet (768px - 1199px)
```
        Login Card (90% width with padding)
        Centered
        Touch-friendly buttons
        Animation scaled down
```

### Mobile (< 768px)
```
    Full width form
    Padding for safety
    Touch targets: 44px+
    Optimized spacing
    Collapsed animations
```

---

## 🎭 Form Validation Messages

### Successful Login
```
POST /dashboard/login/
    ↓
Status: 302 (Redirect)
Location: /dashboard/admin-dashboard/
or
Location: /dashboard/company/dashboard/
```

### Failed Credentials - Admin
```
Error Message:
════════════════════════════════════════
❌ Invalid username or password.
════════════════════════════════════════
(Or)
❌ This account does not have admin access.
════════════════════════════════════════
```

### Failed Credentials - Company
```
Error Message:
════════════════════════════════════════
❌ Invalid company username or password.
════════════════════════════════════════
```

---

## 🎯 Interactive Elements

### Password Visibility Toggle
```
Input: [••••••••••]  [👁️]
       Default        Click to reveal
       
       ↓
       
Input: [password1]  [👁️‍🗨️]
       Password      Click to hide
```

**Works on both tabs independently**

### Tab Navigation
```
Inactive Tab:
[Light background] [Medium text color]

Active Tab:
[White background] [Blue text color] [Shadow]
```

---

## 🔄 Session Management

### After Admin Login
```
session = {
    'auth_id': <user_id>,
    '_auth_user_id': <user_id>,
    '_auth_user_backend': 'django.contrib.auth.backends.ModelBackend'
}
request.user = <Admin User Object>
request.user.is_authenticated = True
```

### After Company Login
```
session = {
    'company_id': <company_id>,
    'company_name': '<company_name>'
}
request.user.is_authenticated = False
request.session['company_id'] exists = True
```

---

## 🚫 Logout Pathway

### From Admin Dashboard
```
Click "Logout" in header/sidebar
    ↓
logout_view()
    ↓
logout(request) - Clears auth session
    ↓
Redirect to /dashboard/login/
```

### From Company Dashboard
```
Click "Logout" in header/sidebar
    ↓
company_logout_view()
    ↓
session.pop('company_id')
session.pop('company_name')
    ↓
Redirect to /dashboard/login/
```

---

## ✨ Interactive Features

### 1. Tab Switching
- Click tab name
- No page reload
- Smooth fade animation
- Form clears automatically
- Demo badge updates

### 2. Password Toggle
- Click eye icon in password field
- Real-time visibility change
- Works independently on each tab
- Icon changes (eye ↔ eye-slash)

### 3. Remember Me
- Checkbox on each tab
- Cookie-based persistence (optional implementation)
- Separate for admin/company

### 4. Forgot Password
- "Forgot Password?" link
- Routes to password reset page (future)
- Different per role

---

## 🛡️ Security Features

✅ CSRF Token Protection
```html
<form method="post" action="">
    {% csrf_token %}
    ...
</form>
```

✅ Password Input Masking
```
Display: ••••••••••
Storage: Never sent in plaintext (POST + HTTPS)
```

✅ Session-based Auth (Company)
```
- No password stored in frontend
- Session ID used for subsequent requests
- Decorator enforces auth check
```

✅ Role-based Redirects
```
- Admin tries /company/dashboard/ → redirected to admin-dashboard/
- Company tries /admin-dashboard/ → unauthorized (not staff)
```

---

## 📊 State Flow Diagram

```
                    ┌─────────────────┐
                    │  Initial Load   │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │ Admin Tab Active│
                    │ Show Admin Form │
                    └────────┬────────┘
                             │
          ┌──────────────────┼──────────────────┐
          │                  │                  │
      [Tab Click]    [Submit admin]    [Tab Click]
          │                  │                  │
    ┌─────▼──────┐    ┌──────▼──────┐    ┌─────▼──────┐
    │Company Tab │    │   Validate  │    │Company Form│
    │   Active   │    │ Credentials │    │   Active   │
    │ Fade Trans │    │             │    │ Fade Trans │
    └────────────┘    └──────┬──────┘    └────────────┘
                             │
                  ┌──────────┴──────────┐
                  │                     │
            [Valid]                [Invalid]
              │                        │
         ┌────▼─────┐          ┌──────▼──────┐
         │ Redirect │          │ Show Error  │
         │ Dashboard│          │ Stay on Tab │
         └──────────┘          └─────────────┘
```

---

## 🎓 Code Example

### HTML Structure
```html
<div class="login-tabs">
    <button class="tab-btn active" onclick="switchTab('admin')">
        <i class='bx bxs-shield'></i> Admin
    </button>
    <button class="tab-btn" onclick="switchTab('company')">
        <i class='bx bxs-building'></i> Company
    </button>
</div>

<div id="admin" class="tab-content active">
    <!-- Admin form here -->
</div>

<div id="company" class="tab-content">
    <!-- Company form here -->
</div>
```

### JavaScript Logic
```javascript
function switchTab(tabName) {
    // Hide all tabs
    document.getElementById('admin').classList.remove('active');
    document.getElementById('company').classList.remove('active');
    
    // Remove active from all buttons
    document.querySelectorAll('.tab-btn').forEach(btn => 
        btn.classList.remove('active')
    );
    
    // Show selected tab
    document.getElementById(tabName).classList.add('active');
    event.target.classList.add('active');
}
```

---

## 🔗 Related URLs

| URL | Purpose | Redirects To |
|-----|---------|-------------|
| `/dashboard/login/` | Unified login | - (main page) |
| `/dashboard/company/login/` | Old company URL | `/dashboard/login/` |
| `/dashboard/admin-dashboard/` | Admin dashboard | - (if logged in as admin) |
| `/dashboard/company/dashboard/` | Company dashboard | - (if company session exists) |
| `/dashboard/logout/` | Admin logout | `/dashboard/login/` |
| `/dashboard/company/logout/` | Company logout | `/dashboard/login/` |

---

**Version:** 1.0  
**Last Updated:** 2026-02-17  
**Status:** ✅ Active & Tested

