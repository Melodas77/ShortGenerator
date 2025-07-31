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

st.set_page_config(page_title="ShortGenerator", layout="centered")
st.title("🎬 ShortGenerator")
st.subheader("AI-powered Shorts from Any Video")

# Firebase Configuration (replace with your actual Firebase config)
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

# Session state for login and user type
if "user" not in st.session_state:
    st.session_state.user = None
if "user_type" not in st.session_state:
    st.session_state.user_type = "free"  # or "premium"

# Ad gate session state
if "free_access" not in st.session_state:
    st.session_state.free_access = True

# Sidebar for login/signup
with st.sidebar:
    st.header("🔐 Login / Signup")
    if st.session_state.user:
        st.success(f"Logged in as {st.session_state.user['email']}")
        account_type = st.radio("Account Type", ["free", "premium"], index=0 if st.session_state.user_type == "free" else 1, disabled=True)
        if st.session_state.user_type == "free":
            if st.button("Upgrade to Premium"):
                st.markdown(f"[💳 Click here to upgrade via Stripe]({checkout_url})")
        if st.button("Logout"):
            st.session_state.user = None
            st.session_state.user_type = "free"
    else:
        choice = st.radio("Select Option", ["Login", "Signup"])
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        if choice == "Login":
            if st.button("Login"):
                try:
                    user = auth.sign_in_with_email_and_password(email, password)
                    st.session_state.user = user
                    st.success("Logged in successfully!")
                except:
                    st.error("Login failed. Check credentials.")
        else:
            if st.button("Signup"):
                try:
                    user = auth.create_user_with_email_and_password(email, password)
                    st.session_state.user = user
                    st.success("Account created and logged in!")
                except:
                    st.error("Signup failed. Email may already be used.")

    st.divider()
    st.header("📊 Usage Dashboard")
    if "usage" not in st.session_state:
        st.session_state.usage = {
            "videos_processed": 0,
            "shorts_generated": 0,
            "last_access": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    st.write(f"**Videos Processed:** {st.session_state.usage['videos_processed']}")
    st.write(f"**Shorts Generated:** {st.session_state.usage['shorts_generated']}")
    st.write(f"**Last Access:** {st.session_state.usage['last_access']}")

# Upload or YouTube Link
upload_option = st.radio("Choose Input Method", ["YouTube Link", "Upload File", "AI-Generated Video"])
video_path = None

if upload_option == "YouTube Link":
    yt_url = st.text_input("Paste YouTube URL")
    if yt_url:
        try:
            yt = YouTube(yt_url)
            stream = yt.streams.filter(file_extension='mp4').get_highest_resolution()
            with st.spinner("Downloading video..."):
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
                stream.download(filename=temp_file.name)
                video_path = temp_file.name
                st.success("Downloaded successfully!")
                st.session_state.usage["videos_processed"] += 1
        except Exception as e:
            st.error(f"Failed to download video: {e}")

elif upload_option == "Upload File":
    uploaded_file = st.file_uploader("Upload your video", type=["mp4", "mov", "mkv", "avi", "webm"])
    if uploaded_file:
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=uploaded_file.name)
        temp_file.write(uploaded_file.read())
        video_path = temp_file.name
        st.success("Video uploaded!")
        st.session_state.usage["videos_processed"] += 1

elif upload_option == "AI-Generated Video":
    st.subheader("🎤 Enter a Topic or Script")
    user_input = st.text_area("Enter a topic or short script")

    if st.button("Generate AI Video") and user_input:
        try:
            st.info("Generating voiceover...")
            tts = gTTS(text=user_input, lang='en')
            tts_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3").name
            tts.save(tts_path)

            st.info("Creating visual with stock footage and text overlay...")
            clip_duration = 30

            # Simulate stock footage by creating a background video from solid color or placeholder (can later use real stock clips)
            bg_clip = TextClip("", bg_color='darkblue', size=(720, 1280), duration=clip_duration).set_duration(clip_duration)
            txt_clip = TextClip(user_input, fontsize=40, color='white', size=(700, 1000), method='caption').set_position('center').set_duration(clip_duration)

            composite = CompositeVideoClip([bg_clip, txt_clip])
            composite = composite.set_audio(AudioFileClip(tts_path))

            final_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
            composite.write_videofile(final_path, fps=24)

            st.video(final_path)
            st.success("AI-generated video is ready!")

        except Exception as e:
            st.error(f"Failed to generate AI video: {e}")

# Ad-gate for free users
if st.session_state.user_type == "free" and not st.session_state.free_access:
    st.warning("🎥 Please watch this 30-second ad to continue.")
    with st.spinner("Simulated ad... please wait 30 seconds"):
        time.sleep(30)
    st.session_state.free_access = True
    st.success("Thanks for watching! You may now continue.")

# Premium feature: batch shorts
if video_path and st.session_state.free_access:
    if st.session_state.user_type == "premium":
        num_shorts = st.slider("How many shorts to generate?", 1, 15, 1)
    else:
        num_shorts = 1
        st.info("Upgrade to premium to generate up to 15 shorts at once.")

    if st.button("🔍 Analyze and Generate Short(s)"):
        st.info("Using Whisper to transcribe audio and find highlights...")
        try:
            model = whisper.load_model("base")
            result = model.transcribe(video_path)
            transcript = result["text"]
            st.text_area("Transcript", transcript, height=150)

            st.info(f"Generating {num_shorts} short(s)...")
            for i in range(num_shorts):
                start = 60 + i * 30
                end = start + 30
                short_clip_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
                video = VideoFileClip(video_path).subclip(start, end)
                video.write_videofile(short_clip_path)
                st.video(short_clip_path)
                st.success(f"Short #{i+1} ready!")

            st.session_state.usage["shorts_generated"] += num_shorts
            st.session_state.usage["last_access"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            st.session_state.free_access = False

        except Exception as e:
            st.error(f"Failed to process video: {e}")
