# Kath Bath – Streamlit Audio Collection App

This app allows users to watch a video, speak about it naturally, record their voice, and upload the audio with metadata securely to Google Drive — all after email OTP verification.

---

## 🔒 Features

- ✅ Email OTP login (only verified users)
- ✅ Audio recording (must be 30–59 seconds)
- ✅ Upload to Google Drive via service account
- ✅ Dashboard with user-wise submission history

---

## 🚀 Setup Instructions

### 1. Add Gmail App Credentials (Do NOT commit this)
```python
# EMAIL_CONFIG.py
EMAIL = "your-email@gmail.com"
APP_PASSWORD = "your-app-password"
