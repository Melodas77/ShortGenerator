# ShortGenerator - Streamlit Prototype

import streamlit as st
from pytube import YouTube
import whisper
import os
import tempfile
from moviepy.editor import VideoFileClip, concatenate_videoclips, TextClip, CompositeVideoClip, AudioFileClip
import datetime
import pyrebase
from gtts import gTTS
import time
import stripe
import random

st.set_page_config(page_title="ShortGenerator", layout="wide")
st.markdown("""
    <style>
    .main { background-color: #f5f7fa; }
    .stApp { padding: 1rem; }
    .stButton>button { background-color: #4CAF50; color: white; }
    .stTextInput>div>div>input { padding: 0.5rem; }
    </style>
""", unsafe_allow_html=True)

st.title("🎬 ShortGenerator")
st.subheader("Turn Any Video Into Viral Shorts with AI ✂️")

# Firebase Configuration
firebase_config = {
    "apiKey": "YOUR_API_KEY",
    "authDomain": "YOUR_PROJECT.firebaseapp.com",
    "databaseURL": "https://YOUR_PROJECT.firebaseio.com",
    "projectId": "YOUR_PROJECT",
    "storageBucket": "YOUR_PROJECT.appspot.com",
    "messagingSenderId": "YOUR_SENDER_ID",
    "appId": "YOUR_APP_ID"
}

firebase = pyrebase.initialize_app(firebase_config)
auth = firebase.auth()

# Stripe Configuration
stripe.api_key = "sk_test_YOUR_SECRET_KEY"
checkout_url = "https://buy.stripe.com/test_YOUR_CHECKOUT_LINK"

# Session state
if "user" not in st.session_state:
    st.session_state.user = None
if "user_type" not in st.session_state:
    st.session_state.user_type = "free"
if "free_access" not in st.session_state:
    st.session_state.free_access = True

# Sidebar for login/signup
with st.sidebar:
    st.image("https://i.imgur.com/ya0OZ6K.png", width=200)
    st.header("🔐 Account")
    if st.session_state.user:
        st.success(f"Welcome, {st.session_state.user['email']}")
        account_type = st.radio("Account Type", ["free", "premium"], index=0 if st.session_state.user_type == "free" else 1, disabled=True)
        if st.session_state.user_type == "free":
            st.markdown(f"[🚀 Upgrade to Premium]({checkout_url})")
        if st.button("Logout"):
            st.session_state.user = None
            st.session_state.user_type = "free"
    else:
        choice = st.radio("Choose", ["Login", "Signup"])
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        if choice == "Login":
            if st.button("Login"):
                try:
                    user = auth.sign_in_with_email_and_password(email, password)
                    st.session_state.user = user
                    st.success("Logged in!")
                except:
                    st.error("Invalid credentials")
        else:
            if st.button("Signup"):
                try:
                    user = auth.create_user_with_email_and_password(email, password)
                    st.session_state.user = user
                    st.success("Signed up and logged in!")
                except:
                    st.error("Signup failed. Try another email.")

    st.divider()
    st.header("📊 Dashboard")
    if "usage" not in st.session_state:
        st.session_state.usage = {
            "videos_processed": 0,
            "shorts_generated": 0,
            "last_access": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    st.metric("Videos Processed", st.session_state.usage["videos_processed"])
    st.metric("Shorts Created", st.session_state.usage["shorts_generated"])
    st.caption(f"Last used: {st.session_state.usage['last_access']}")

# Upload or YouTube Link
st.markdown("### 🎥 Select Your Video Source")
col1, col2, col3 = st.columns(3)

with col1:
    yt_url = st.text_input("YouTube URL")
with col2:
    uploaded_file = st.file_uploader("Upload Video File", type=["mp4", "mov", "avi", "webm"])
with col3:
    user_input = st.text_area("Or enter topic for AI video")

video_path = None

if yt_url:
    try:
        yt = YouTube(yt_url)
        stream = yt.streams.filter(file_extension='mp4').get_highest_resolution()
        with st.spinner("Downloading from YouTube..."):
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
            stream.download(filename=temp_file.name)
            video_path = temp_file.name
            st.success("Downloaded!")
            st.session_state.usage["videos_processed"] += 1
    except Exception as e:
        st.error("Failed to download from YouTube. Check link or try later.")

elif uploaded_file:
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=uploaded_file.name)
    temp_file.write(uploaded_file.read())
    video_path = temp_file.name
    st.success("Uploaded video!")
    st.session_state.usage["videos_processed"] += 1

elif user_input and st.button("Generate AI Video"):
    try:
        st.info("Creating voiceover and visuals...")
        tts = gTTS(text=user_input, lang='en')
        tts_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3").name
        tts.save(tts_path)

        bg_clip = TextClip("", bg_color='darkblue', size=(720, 1280)).set_duration(30)
        txt_clip = TextClip(user_input, fontsize=40, color='white', size=(700, 1000), method='caption').set_position('center').set_duration(30)

        final = CompositeVideoClip([bg_clip, txt_clip]).set_audio(AudioFileClip(tts_path))
        final_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
        final.write_videofile(final_path, fps=24)
        st.video(final_path)
        st.success("AI video ready!")

    except Exception as e:
        st.error(f"Failed to generate video: {e}")

# Ad-gate for free users
if st.session_state.user_type == "free" and not st.session_state.free_access:
    st.warning("⏳ Watch a 30-second ad to continue")
    with st.spinner("Simulated Ad – wait 30 seconds"):
        time.sleep(30)
    st.session_state.free_access = True
    st.success("Thanks! Continue below.")

# Shorts generation
if video_path and st.session_state.free_access:
    st.markdown("### ✂️ Generate Shorts")
    if st.session_state.user_type == "premium":
        num_shorts = st.slider("How many shorts?", 1, 15, 3)
    else:
        num_shorts = 1
        st.info("Upgrade to generate more than 1 short")

    if st.button("Generate Shorts"):
        st.info("Transcribing and selecting highlights...")
        try:
            model = whisper.load_model("base")
            result = model.transcribe(video_path)
            transcript = result["text"]
            st.text_area("Transcript", transcript, height=150)

            for i in range(num_shorts):
                start = 60 + i * 30
                end = start + 30
                short_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
                clip = VideoFileClip(video_path).subclip(start, end)
                clip.write_videofile(short_path)
                st.video(short_path)
                st.success(f"Short #{i+1} is ready!")

            st.session_state.usage["shorts_generated"] += num_shorts
            st.session_state.usage["last_access"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            st.session_state.free_access = False

        except Exception as e:
            st.error(f"Failed to process: {e}")
