import streamlit as st
from streamlit_audiorec import st_audiorec
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from datetime import datetime
from pathlib import Path
import pandas as pd
import uuid
import wave
import io
import random
import time
import yagmail
from EMAIL_CONFIG import EMAIL, APP_PASSWORD
from verified_users import VERIFIED_EMAILS

# --- CONFIG ---
TEMP_DIR = Path("temp")
TEMP_DIR.mkdir(exist_ok=True)
DB_PATH = Path("submission_metadata.csv")
OTP_LOG_PATH = Path("otp_log.csv")
GDRIVE_FOLDER_ID = "YOUR_GOOGLE_DRIVE_FOLDER_ID"  # Replace this
CREDENTIALS_FILE = "creds.json"

# --- INIT OTP LOG ---
if not OTP_LOG_PATH.exists():
    pd.DataFrame(columns=["email", "last_sent"]).to_csv(OTP_LOG_PATH, index=False)

# --- FUNCTIONS ---
def get_audio_duration(wav_data):
    try:
        with wave.open(io.BytesIO(wav_data), 'rb') as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            duration = frames / float(rate)
            return round(duration, 2)
    except Exception as e:
        st.error(f"Failed to calculate audio duration: {e}")
        return 0

def send_otp(recipient_email, otp):
    try:
        yag = yagmail.SMTP(EMAIL, APP_PASSWORD)
        yag.send(to=recipient_email, subject="Your OTP for Kath Bath Login", contents=f"Your OTP is: {otp}")
    except Exception as e:
        st.error(f"Failed to send OTP: {e}")
        raise

def upload_to_drive(file_path, filename):
    try:
        creds = service_account.Credentials.from_service_account_file(
            CREDENTIALS_FILE, scopes=["https://www.googleapis.com/auth/drive"]
        )
        service = build('drive', 'v3', credentials=creds)
        file_metadata = {'name': filename, 'parents': [GDRIVE_FOLDER_ID]}
        media = MediaFileUpload(file_path, resumable=True)
        uploaded = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        return uploaded.get("id")
    except Exception as e:
        st.error(f"Failed to upload to Google Drive: {e}")
        raise

# --- SESSION STATE ---
if "user" not in st.session_state:
    st.session_state.user = None
    st.session_state.otp_sent = False
    st.session_state.generated_otp = None
    st.session_state.email = None
    st.session_state.otp_verified = False

# --- LOGIN ---
if not st.session_state.user:
    st.title("🔐 Kath Bath - Email Login")

    if not st.session_state.otp_sent:
        email_input = st.text_input("Enter your email:")
        if st.button("Send OTP"):
            email_clean = email_input.strip().lower()

            if email_clean not in VERIFIED_EMAILS:
                st.error("❌ This email is not authorized.")
                st.stop()

            # Global rate limit check
            otp_df = pd.read_csv(OTP_LOG_PATH)
            now = time.time()
            if email_clean in otp_df["email"].values:
                last_time = otp_df.loc[otp_df["email"] == email_clean, "last_sent"].values[0]
                time_diff = now - float(last_time)
                if time_diff < 60:
                    remaining = int(60 - time_diff)
                    st.warning(f"⏳ Wait {remaining} seconds before requesting new OTP.")
                    st.stop()

            # Send OTP
            otp = str(random.randint(100000, 999999))
            try:
                send_otp(email_clean, otp)
                st.session_state.generated_otp = otp
                st.session_state.email = email_clean
                st.session_state.otp_sent = True
                st.success("✅ OTP sent to your verified email.")

                # Update OTP log
                otp_df = otp_df[otp_df["email"] != email_clean]
                new_entry = pd.DataFrame({"email": [email_clean], "last_sent": [now]})
                otp_df = pd.concat([otp_df, new_entry], ignore_index=True)
                otp_df.to_csv(OTP_LOG_PATH, index=False)

            except Exception as e:
                st.error(f"Failed to send OTP: {e}")
        st.stop()
    else:
        user_otp = st.text_input("Enter OTP", max_chars=6)
        if st.button("Verify OTP"):
            if user_otp == st.session_state.generated_otp:
                st.session_state.user = st.session_state.email.lower()
                st.success("✅ OTP Verified. You are logged in!")
                st.experimental_rerun()
            else:
                st.error("❌ Incorrect OTP")
        st.stop()
else:
    st.info(f"👤 Logged in as `{st.session_state.user}`")

# --- DASHBOARD ---
with st.expander("📊 View Submission Dashboard"):
    if DB_PATH.exists():
        df = pd.read_csv(DB_PATH)
        st.metric("Total Submissions", len(df))
        st.metric("Your Submissions", df[df["User"] == st.session_state.user].shape[0])
        st.dataframe(df[df["User"] == st.session_state.user].sort_values("Timestamp", ascending=False).head(5))
    else:
        st.info("No submissions yet.")

# --- VIDEO ---
st.markdown("### 🎬 Watch the Video")
st.video("https://www.youtube.com/watch?v=dQw4w9WgXcQ")  # Replace with your actual video

# --- RECORD AUDIO ---
st.markdown("### 🎙️ Record Your Response (30–59 seconds)")
wav_audio_data = st_audiorec()
audio_duration = None

if wav_audio_data:
    st.audio(wav_audio_data, format='audio/wav')
    audio_duration = get_audio_duration(wav_audio_data)
    st.info(f"⏱️ Duration: {audio_duration} seconds")

    if audio_duration < 30:
        st.warning("Recording is too short. Must be at least 30 seconds.")
    elif audio_duration > 59:
        st.warning("Recording is too long. Must be under 59 seconds.")

# --- METADATA FORM ---
st.markdown("### 📝 Submit Metadata")
with st.form("metadata_form"):
    name = st.text_input("Full Name")
    language = st.selectbox("Language", ["Hindi", "Tamil", "Telugu", "English", "Other"])
    gender = st.radio("Gender", ["Male", "Female", "Other"])
    age = st.selectbox("Age Range", ["18-25", "26-40", "41-60", "60+"])
    region = st.text_input("Region / State")
    device = st.text_input("Device Used")
    mic = st.radio("Mic Type", ["Built-in", "External"])
    submit = st.form_submit_button("📤 Submit")

# --- SUBMIT LOGIC ---
if submit and wav_audio_data:
    if not (30 <= audio_duration <= 59):
        st.error("Recording must be between 30 and 59 seconds.")
    else:
        unique_id = uuid.uuid4().hex[:16]
        filename = f"{language}_{region}_{unique_id}.wav"
        temp_path = TEMP_DIR / filename

        try:
            with open(temp_path, "wb") as f:
                f.write(wav_audio_data)

            gdrive_id = upload_to_drive(temp_path, filename)
            st.success(f"✅ Uploaded to Google Drive (ID: {gdrive_id})")

            metadata = {
                "User": st.session_state.user,
                "Name": name,
                "Language": language,
                "Gender": gender,
                "Age": age,
                "Region": region,
                "Device": device,
                "Mic": mic,
                "Filename": filename,
                "DriveFileID": gdrive_id,
                "Timestamp": datetime.now().isoformat()
            }

            if DB_PATH.exists():
                df = pd.read_csv(DB_PATH)
                df = pd.concat([df, pd.DataFrame([metadata])], ignore_index=True)
            else:
                df = pd.DataFrame([metadata])

            df.to_csv(DB_PATH, index=False)
            st.success("✅ Submission complete!")

        except Exception as e:
            st.error(f"❌ Submission failed: {e}")
        finally:
            # Clean up temp file
            if temp_path.exists():
                temp_path.unlink()
