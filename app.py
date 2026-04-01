import streamlit as st
from PIL import Image
import cv2
import numpy as np
import joblib
import time
import datetime
import requests
import os 
from skimage.feature import hog, local_binary_pattern, graycomatrix, graycoprops

# --- 1. PAGE SETUP ---
st.set_page_config(
    page_title="Plant Doctor AI", 
    page_icon="🌿", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. WEATHER ---
def get_real_weather():
    try:
        url = "https://api.open-meteo.com/v1/forecast?latitude=31.5204&longitude=74.3587&current_weather=true"
        response = requests.get(url, timeout=3) 
        data = response.json()
        return data['current_weather']['temperature'], data['current_weather']['windspeed']
    except:
        return 28, 12

temp, wind = get_real_weather()

# --- 3. CSS ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=Noto+Nastaliq+Urdu&display=swap');
    
    html, body, [class*="css"] { font-family: 'Outfit', sans-serif; scroll-behavior: smooth; }

    @keyframes fadeInUp { from { opacity: 0; transform: translateY(30px); } to { opacity: 1; transform: translateY(0); } }
    @keyframes popIn { 0% { transform: scale(0.8); opacity: 0; } 100% { transform: scale(1); opacity: 1; } }
    @keyframes pulse-red { 0% { box-shadow: 0 0 0 0 rgba(255,50,50,0.7); } 70% { box-shadow: 0 0 0 10px rgba(255,50,50,0); } 100% { box-shadow: 0 0 0 0 rgba(255,50,50,0); } }
    @keyframes float-weather { 0%,100% { transform: translateY(0px); } 50% { transform: translateY(-8px); } }
    @keyframes diamond-wind { 0% { transform: translateY(0) translateX(0); } 100% { transform: translateY(100px) translateX(-100px); } }
    @keyframes gradientBG { 0% { background-position: 0% 50%; } 50% { background-position: 100% 50%; } 100% { background-position: 0% 50%; } }
    @keyframes float-logo { 0%,100% { transform: translateY(0px); box-shadow: 0 0 15px rgba(16,185,129,0.4); } 50% { transform: translateY(-8px); box-shadow: 0 0 30px rgba(16,185,129,0.7); } }
    @keyframes shimmer { 0% { background-position: -200% center; } 100% { background-position: 200% center; } }
    @keyframes pulse-green { 0%,100% { box-shadow: 0 0 0 0 rgba(16,185,129,0.4); } 50% { box-shadow: 0 0 20px 8px rgba(16,185,129,0.2); } }
    @keyframes scroll { 0% { transform: translateX(0); } 100% { transform: translateX(calc(-600px * 6)); } }

    h1, h2, h3, p, span, a, div.stMarkdown { animation: fadeInUp 0.8s ease-out both; }

    .stApp::before {
        content: ""; position: fixed; top: -50%; left: -50%; width: 200%; height: 200%;
        background-image: radial-gradient(circle at 20px 30px, rgba(4,120,87,0.5) 0px, transparent 2px), radial-gradient(circle at 40px 70px, rgba(16,185,129,0.6) 0px, transparent 2px), radial-gradient(circle at 50px 160px, rgba(5,150,105,0.5) 0px, transparent 2px), radial-gradient(circle at 90px 40px, rgba(52,211,153,0.7) 0px, transparent 3px), radial-gradient(circle at 130px 80px, rgba(6,78,59,0.6) 0px, transparent 2px);
        background-repeat: repeat; background-size: 200px 200px; animation: diamond-wind 25s linear infinite; pointer-events: none; z-index: 0;
    }

    [data-testid="stSidebar"] { background-image: linear-gradient(180deg, #064e3b 0%, #047857 100%); border-right: none; }
    [data-testid="stSidebar"] * { color: #ecfdf5 !important; }
    [data-testid="stSidebar"] .stRadio div[role="radiogroup"] label { background: rgba(0,0,0,0.25); padding: 15px 20px; border-radius: 15px; margin-bottom: 12px !important; border: 1px solid rgba(255,255,255,0.1); width: 100%; display: flex; align-items: center; transition: all 0.3s ease; box-shadow: 0 4px 6px rgba(0,0,0,0.1); cursor: pointer; }
    [data-testid="stSidebar"] .stRadio div[role="radiogroup"] label:hover { background: rgba(255,255,255,0.15); transform: scale(1.02); border-color: #34d399; }
    [data-testid="stSidebar"] .stRadio div[role="radiogroup"] div[aria-checked="true"] + div + label { background: linear-gradient(90deg, #059669, #10b981) !important; border: 1px solid #a7f3d0 !important; font-weight: 800; transform: scale(1.03); box-shadow: 0 0 20px rgba(16,185,129,0.6) !important; color: white !important; }
    [data-testid="stSidebar"] .stRadio div[role="radiogroup"] div[role="radio"] { display: none; }

    .hero-container { text-align: center; padding: 50px 20px 40px; border-radius: 35px; background: linear-gradient(-45deg, #ccfbf1, #d1fae5, #a7f3d0, #6ee7b7); background-size: 400% 400%; animation: gradientBG 15s ease infinite, popIn 1s ease-out; box-shadow: 0 20px 60px rgba(0,0,0,0.15); margin-bottom: 30px; border: 2px solid rgba(255,255,255,0.8); position: relative; z-index: 1; }

    .hero-stats { display: flex; justify-content: center; gap: 40px; margin: 25px 0; flex-wrap: wrap; }
    .hero-stat { text-align: center; }
    .hero-stat-val { font-size: 2rem; font-weight: 800; color: #064e3b; }
    .hero-stat-lbl { font-size: 0.85rem; color: #047857; font-weight: 600; }
    .hero-divider { width: 1px; background: rgba(6,78,59,0.2); align-self: stretch; }

    .hero-cta-row { display: flex; justify-content: center; gap: 15px; flex-wrap: wrap; margin-top: 25px; }
    .cta-primary { display: inline-block; background: linear-gradient(90deg, #059669, #10b981); color: white !important; padding: 16px 40px; border-radius: 50px; font-weight: 800; font-size: 1.05rem; text-decoration: none !important; box-shadow: 0 10px 30px rgba(16,185,129,0.5); transition: all 0.3s; border: 2px solid #a7f3d0; animation: pulse-green 3s infinite; }
    .cta-primary:hover { transform: scale(1.08) translateY(-3px); box-shadow: 0 15px 40px rgba(16,185,129,0.6); }
    .cta-secondary { display: inline-block; background: rgba(255,255,255,0.8); color: #064e3b !important; padding: 16px 35px; border-radius: 50px; font-weight: 700; font-size: 1rem; text-decoration: none !important; box-shadow: 0 5px 20px rgba(0,0,0,0.1); transition: all 0.3s; border: 2px solid rgba(6,78,59,0.2); backdrop-filter: blur(10px); }
    .cta-secondary:hover { transform: scale(1.05) translateY(-2px); background: white; }

    .slider-wrapper { position: relative; }
    .slider-container { width: 100%; overflow: hidden; border-radius: 25px; box-shadow: 0 20px 50px rgba(0,0,0,0.2); border: 2px solid rgba(255,255,255,0.7); background: #000; height: 420px; }
    .slide-track { display: flex; width: calc(600px * 12); animation: scroll 60s linear infinite; cursor: grab; }
    .slide-track:hover { animation-play-state: paused; }
    .slide-track:active { cursor: grabbing; }
    .slide { width: 600px; height: 420px; flex-shrink: 0; padding: 0 5px; }
    .slide img { width: 100%; height: 100%; object-fit: cover; border-radius: 15px; transition: transform 0.4s; pointer-events: none; }

    .weather-container { position: relative; border-radius: 25px; padding: 25px; overflow: hidden; transition: transform 0.3s ease; height: 420px; display: flex; flex-direction: column; justify-content: space-between; }
    .weather-container:hover { transform: translateY(-5px); }
    .weather-glow { position: absolute; top: -50%; left: -50%; width: 200%; height: 200%; background: radial-gradient(circle, rgba(255,255,255,0.2) 0%, transparent 60%); z-index: 0; pointer-events: none; }
    .weather-content { position: relative; z-index: 2; display: flex; flex-direction: column; align-items: center; height: 100%; }
    .weather-header { width: 100%; display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
    .live-badge { background: rgba(0,0,0,0.3); padding: 6px 14px; border-radius: 20px; font-size: 0.75rem; font-weight: 700; letter-spacing: 1px; display: flex; align-items: center; gap: 8px; border: 1px solid rgba(255,255,255,0.1); }
    .live-dot { width: 8px; height: 8px; background: #ef4444; border-radius: 50%; box-shadow: 0 0 8px #ef4444; animation: pulse-red 1.5s infinite; }
    .temp-big { font-size: 5rem; font-weight: 800; line-height: 1; background: linear-gradient(180deg, #ffffff 20%, rgba(255,255,255,0.6) 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; filter: drop-shadow(0 4px 10px rgba(0,0,0,0.2)); margin: 10px 0; }
    .weather-icon-3d { font-size: 3.5rem; filter: drop-shadow(0 10px 15px rgba(0,0,0,0.3)); animation: float-weather 6s ease-in-out infinite; }
    .details-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; width: 100%; margin-top: auto; padding-top: 15px; }
    .detail-item { background: rgba(255,255,255,0.15); border-radius: 15px; padding: 10px; text-align: center; border: 1px solid rgba(255,255,255,0.1); }
    .detail-label { font-size: 0.7rem; color: rgba(255,255,255,0.8); text-transform: uppercase; letter-spacing: 1px; }
    .detail-val { font-size: 1.1rem; font-weight: 700; color: white; }

    .feature-card { background: rgba(255,255,255,0.9); backdrop-filter: blur(25px); padding: 30px; border-radius: 30px; text-align: center; border: 1px solid rgba(255,255,255,0.6); box-shadow: 0 10px 30px rgba(0,0,0,0.08); height: 100%; display: flex; flex-direction: column; justify-content: center; align-items: center; transition: transform 0.4s ease, box-shadow 0.4s ease; position: relative; z-index: 1; }
    .feature-card:hover { transform: perspective(1000px) rotateX(5deg) rotateY(-5deg) translateY(-15px); box-shadow: 0 30px 60px rgba(16,185,129,0.3); border-color: #34d399; }

    .crop-card { background: rgba(255,255,255,0.92); backdrop-filter: blur(25px); padding: 35px 25px; border-radius: 30px; text-align: center; border: 1px solid rgba(255,255,255,0.6); box-shadow: 0 10px 30px rgba(0,0,0,0.08); min-height: 260px; display: flex; flex-direction: column; justify-content: center; align-items: center; transition: all 0.35s ease; cursor: pointer; position: relative; overflow: hidden; }
    .crop-card::after { content: ""; position: absolute; inset: 0; border-radius: 30px; opacity: 0; transition: opacity 0.3s; background: linear-gradient(135deg, rgba(16,185,129,0.08), rgba(6,78,59,0.05)); }
    .crop-card:hover { transform: translateY(-14px) scale(1.02); box-shadow: 0 30px 60px rgba(16,185,129,0.25); border-color: #34d399; }
    .crop-card:hover::after { opacity: 1; }
    .crop-card-soon { border: 2px dashed #f59e0b; background: rgba(254,243,199,0.7); }
    .crop-card-soon:hover { border-color: #d97706; box-shadow: 0 30px 60px rgba(245,158,11,0.2); }
    .crop-card-dev { border: 2px dashed #8b5cf6; background: rgba(237,233,254,0.7); }
    .crop-card-dev:hover { border-color: #7c3aed; box-shadow: 0 30px 60px rgba(139,92,246,0.2); }
    .crop-arrow { font-size: 1.3rem; margin-top: 10px; opacity: 0; transform: translateX(-8px); transition: all 0.3s; }
    .crop-card:hover .crop-arrow { opacity: 1; transform: translateX(0); }

    .badge-live { display: inline-block; background: linear-gradient(90deg, #059669, #10b981); color: white; padding: 5px 16px; border-radius: 20px; font-size: 0.8rem; font-weight: 700; letter-spacing: 0.5px; margin-top: 10px; }
    .badge-soon { display: inline-block; background: linear-gradient(90deg, #f59e0b, #ef4444); background-size: 200% auto; color: white; padding: 5px 16px; border-radius: 20px; font-size: 0.8rem; font-weight: 700; margin-top: 10px; animation: shimmer 2s infinite linear; }
    .badge-dev { display: inline-block; background: linear-gradient(90deg, #6366f1, #8b5cf6); color: white; padding: 5px 16px; border-radius: 20px; font-size: 0.8rem; font-weight: 700; margin-top: 10px; }

    .result-box { padding: 30px; border-radius: 25px; text-align: center; background: rgba(255,255,255,0.95); box-shadow: 0 20px 50px rgba(0,0,0,0.1); animation: popIn 0.6s ease-out; border: 2px solid white; }
    img { border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.15); transition: transform 0.3s; }
    .urdu-name { font-family: 'Noto Nastaliq Urdu', serif; font-size: 1.4rem; direction: rtl; line-height: 2; }
    .local-name { font-family: 'Noto Nastaliq Urdu', serif; font-size: 1.1rem; direction: rtl; color: #666; }

    .tech-tag { display: inline-block; padding: 5px 12px; border-radius: 8px; font-size: 0.85rem; font-weight: 600; margin: 3px; }
    </style>
    """, unsafe_allow_html=True)

# JS for manual slider drag
st.markdown("""
<script>
document.addEventListener('DOMContentLoaded', function() {
    const track = document.querySelector('.slide-track');
    if (!track) return;
    let isDown = false, startX, scrollLeft;
    track.addEventListener('mousedown', e => { isDown = true; startX = e.pageX - track.offsetLeft; scrollLeft = track.scrollLeft; track.style.animationPlayState = 'paused'; });
    track.addEventListener('mouseleave', () => { isDown = false; });
    track.addEventListener('mouseup', () => { isDown = false; });
    track.addEventListener('mousemove', e => { if (!isDown) return; e.preventDefault(); const x = e.pageX - track.offsetLeft; track.scrollLeft = scrollLeft - (x - startX); });
});
</script>
""", unsafe_allow_html=True)

# --- URDU NAMES ---
TOMATO_URDU_NAMES = {"Bacterial Spot": "بیکٹیریل دھبے", "Early Blight": "اگیتی جھلس", "Late Blight": "پچھیتی جھلس", "Leaf Mold": "پتے کی پھپھوندی", "Septoria Leaf Spot": "سیپٹوریا دھبے", "Target Spot": "ہدف دھبے", "Yellow Leaf Curl Virus": "پیلا پتہ مروڑ وائرس", "Mosaic Virus": "موزیک وائرس", "Healthy": "صحت مند"}
TOMATO_LOCAL_NAMES = {"Bacterial Spot": "ٹماٹر تے کالے داغ", "Early Blight": "اگیتی سڑن", "Late Blight": "پچھیتی سڑن", "Leaf Mold": "پتیاں تے پھپھوند", "Septoria Leaf Spot": "پتیاں تے چھوٹے داغ", "Target Spot": "گول داغ روگ", "Yellow Leaf Curl Virus": "پیلا پتہ وائرس", "Mosaic Virus": "چتکبری بیماری", "Healthy": "تندرست فصل"}
POTATO_URDU_NAMES = {"Early Blight": "اگیتی جھلس", "Late Blight": "پچھیتی جھلس", "Healthy": "صحت مند"}
POTATO_LOCAL_NAMES = {"Early Blight": "اگیتی سڑن", "Late Blight": "پچھیتی سڑن", "Healthy": "تندرست فصل"}

# --- MODEL LOADING ---
@st.cache_resource
def load_ml_model():
    try:
        data = joblib.load("potato_disease_model.pkl")
        return data['model'], data['scaler'], data['class_names']
    except Exception as e:
        st.error(f"Error loading potato model: {e}")
        return None, None, None

@st.cache_resource
def load_tomato_model():
    try:
        data = joblib.load("tomato_disease_model_9_classes.pkl")
        return data['model'], data['scaler'], data['class_names']
    except Exception as e:
        st.error(f"Error loading tomato model: {e}")
        return None, None, None

rf_model, scaler, class_names = load_ml_model()
t_model, t_scaler, t_class_names = load_tomato_model()

# --- FEATURE EXTRACTION ---
def extract_all_features(image_bytes):
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    img = cv2.resize(img, (128, 128))
    gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    hist_bgr = cv2.calcHist([img], [0,1,2], None, [8,8,8], [0,256,0,256,0,256])
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    hist_hsv = cv2.calcHist([hsv], [0,1,2], None, [8,8,8], [0,180,0,256,0,256])
    f_color = np.hstack([hist_bgr.flatten(), hist_hsv.flatten()])
    f_hog = hog(gray_img, orientations=9, pixels_per_cell=(8,8), cells_per_block=(2,2), visualize=False)
    radius, n_points = 2, 16
    lbp = local_binary_pattern(gray_img, n_points, radius, method='uniform')
    hist, _ = np.histogram(lbp.ravel(), bins=np.arange(0, n_points+3), range=(0, n_points+2))
    hist = hist.astype("float"); f_lbp = hist / (hist.sum() + 1e-7)
    glcm = graycomatrix(gray_img, distances=[1,2], angles=[0, np.pi/4, np.pi/2, 3*np.pi/4], levels=256, symmetric=True, normed=True)
    f_glcm = np.array([graycoprops(glcm, p).mean() for p in ['contrast','correlation','energy','homogeneity','dissimilarity']])
    return np.hstack([f_color, f_hog, f_lbp, f_glcm])

# --- SIDEBAR ---
st.sidebar.markdown("""
    <div style="display:flex;justify-content:center;margin-bottom:25px;margin-top:10px;">
        <img src="https://cdn-icons-png.flaticon.com/512/11698/11698467.png" 
             style="width:150px;border-radius:50%;padding:10px;background:rgba(255,255,255,0.15);border:3px solid rgba(255,255,255,0.4);animation:float-logo 3s ease-in-out infinite;">
    </div>""", unsafe_allow_html=True)
st.sidebar.markdown("<h1 style='text-align:center;color:white;font-weight:800;margin-top:-10px;font-size:2.2rem;text-shadow:0 2px 10px rgba(0,0,0,0.2);'>Plant Doctor</h1>", unsafe_allow_html=True)
st.sidebar.markdown("<p style='text-align:center;font-size:0.9rem;opacity:0.9;margin-bottom:30px;letter-spacing:2px;font-weight:600;'>AI DIAGNOSTICS</p>", unsafe_allow_html=True)
st.sidebar.write("---")

# ✅ Pepper sidebar mein add
nav = st.sidebar.radio("", ["🏠 Home Page", "🥔 Potato (Aloo)", "🍅 Tomato Check", "🌽 Corn Field", "🫑 Pepper (Mirch)"])

st.sidebar.write("---")
with st.sidebar.expander("📸 Tips for Best Results"):
    st.markdown("* ☀️ **Lighting:** Use bright daylight.\n* 🍃 **Focus:** Capture only the leaf.\n* 🖼️ **Background:** Keep it plain.")
st.sidebar.write("---")
st.sidebar.info("**Developers:**\n\n👨‍💻 **Saqlain Khan**\n(Data Engineer)\n\n👨‍💻 **Raheel Chishti**\n(Team Member)")

# ==================== HOME PAGE ====================
if nav == "🏠 Home Page":

    # ✅ IMPROVED HERO — stats + 2 buttons
    st.markdown("""
    <div class="hero-container">
        <p style="color:#047857;font-size:0.95rem;font-weight:700;letter-spacing:3px;text-transform:uppercase;margin-bottom:10px;">🌿 AI-Powered Agriculture</p>
        <h1 style="font-size:4rem;font-weight:900;background:-webkit-linear-gradient(#064e3b,#059669);-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin:0;">Plant Doctor AI</h1>
        <p style="color:#065f46;font-size:1.2rem;font-weight:600;margin:12px 0 5px;">Apni Fasal Ki Bimari Seconds Mein Pehchanein</p>
        <p style="color:#047857;font-size:1rem;max-width:600px;margin:auto;line-height:1.6;opacity:0.9;">Pattay ki photo upload karein — AI fauran bimari detect karke ilaj batayega</p>
        
        <div class="hero-stats">
            <div class="hero-stat">
                <div class="hero-stat-val">97%</div>
                <div class="hero-stat-lbl">Accuracy</div>
            </div>
            <div class="hero-divider"></div>
            <div class="hero-stat">
                <div class="hero-stat-val">18K+</div>
                <div class="hero-stat-lbl">Images Trained</div>
            </div>
            <div class="hero-divider"></div>
            <div class="hero-stat">
                <div class="hero-stat-val">4</div>
                <div class="hero-stat-lbl">Crops</div>
            </div>
            <div class="hero-divider"></div>
            <div class="hero-stat">
                <div class="hero-stat-val">&lt;3s</div>
                <div class="hero-stat-lbl">Result Time</div>
            </div>
        </div>

        <div class="hero-cta-row">
            <a class="cta-primary" href="#supported-crops">🥔 Aloo Check Karein</a>
            <a class="cta-secondary" href="#how-it-works">📖 Kaise Kaam Karta Hai?</a>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ✅ Slider + Weather same height
    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown("""
        <div class="slider-wrapper">
        <div class="slider-container">
            <div class="slide-track">
                <div class="slide"><img src="https://images.unsplash.com/photo-1625246333195-78d9c38ad449?w=800" draggable="false"></div>
                <div class="slide"><img src="https://images.unsplash.com/photo-1586771107445-d3ca888129ff?w=800" draggable="false"></div>
                <div class="slide"><img src="https://images.unsplash.com/photo-1530836369250-ef72a3f5cda8?w=800" draggable="false"></div>
                <div class="slide"><img src="https://images.unsplash.com/photo-1587334274328-64186a80aeee?w=800" draggable="false"></div>
                <div class="slide"><img src="https://images.unsplash.com/photo-1551754655-cd27e38d2076?w=800" draggable="false"></div>
                <div class="slide"><img src="https://images.unsplash.com/photo-1464226184884-fa280b87c399?w=800" draggable="false"></div>
                <div class="slide"><img src="https://images.unsplash.com/photo-1500382017468-9049fed747ef?w=800" draggable="false"></div>
                <div class="slide"><img src="https://images.unsplash.com/photo-1416879595882-3373a0480b5b?w=800" draggable="false"></div>
                <div class="slide"><img src="https://images.unsplash.com/photo-1592087046781-3070b59e4c14?w=800" draggable="false"></div>
                <div class="slide"><img src="https://images.unsplash.com/photo-1625246333195-78d9c38ad449?w=800" draggable="false"></div>
                <div class="slide"><img src="https://images.unsplash.com/photo-1586771107445-d3ca888129ff?w=800" draggable="false"></div>
                <div class="slide"><img src="https://images.unsplash.com/photo-1530836369250-ef72a3f5cda8?w=800" draggable="false"></div>
            </div>
        </div>
        <p style="text-align:center;font-size:0.8rem;color:#aaa;margin-top:8px;">🖱️ Hover to pause | Drag to scroll manually</p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        if temp > 30:
            card_bg = "linear-gradient(145deg, #f59e0b 0%, #ea580c 100%)"
            weather_icon = "☀️"; condition = "Sunny / Dhoop"
        elif temp < 20:
            card_bg = "linear-gradient(145deg, #6366f1 0%, #3b82f6 100%)"
            weather_icon = "❄️"; condition = "Chilly / Thanda"
        else:
            card_bg = "linear-gradient(145deg, #10b981 0%, #059669 100%)"
            weather_icon = "⛅"; condition = "Pleasant / Khushgawar"

        st.markdown(f"""
        <div class="weather-container" style="background:{card_bg};">
            <div class="weather-glow"></div>
            <div class="weather-content">
                <div class="weather-header">
                    <div class="live-badge"><div class="live-dot"></div> LIVE</div>
                    <div style="font-weight:600;font-size:0.9rem;color:rgba(255,255,255,0.9);">📍 Punjab, PK</div>
                </div>
                <div class="weather-icon-3d">{weather_icon}</div>
                <div class="temp-big">{temp}°C</div>
                <div style="font-size:1.1rem;font-weight:600;color:rgba(255,255,255,0.95);margin-bottom:5px;">{condition}</div>
                <div style="font-size:0.8rem;color:rgba(255,255,255,0.7);margin-bottom:10px;">Fasal ke liye mausam</div>
                <div class="details-grid">
                    <div class="detail-item"><div class="detail-label">Wind / Hawa</div><div class="detail-val">{wind} km/h</div></div>
                    <div class="detail-item"><div class="detail-label">Humidity / Nam</div><div class="detail-val">65%</div></div>
                    <div class="detail-item"><div class="detail-label">Spray Time?</div><div class="detail-val">{"❌ Na Karein" if wind > 20 else "✅ Theek Hai"}</div></div>
                    <div class="detail-item"><div class="detail-label">Bimari Risk</div><div class="detail-val">{"🔴 Zyada" if temp > 28 else "🟢 Kam"}</div></div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # How it works
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<h2 id='how-it-works' style='text-align:center;color:#064e3b;font-weight:900;margin-top:50px;font-size:2.2rem;'>How It Works | Kaise Kaam Karta Hai</h2>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    steps = [("📸", "Photo Upload Karein", "Pattay ki saaf tasveer lein aur upload karein. Background sada hona chahiye."), ("🤖", "AI Analysis", "Hamara Random Forest model HOG, LBP, GLCM aur Color features se bimari dhundta hai."), ("💊", "Ilaj Payein", "Fauran result + Urdu mein ilaj ki hidayat milegi.")]
    for col, (icon, title, desc) in zip([c1,c2,c3], steps):
        with col:
            st.markdown(f"""
            <div class="feature-card">
                <div style="font-size:3.5rem;margin-bottom:15px;">{icon}</div>
                <h3 style="color:#064e3b;font-weight:700;margin-bottom:8px;">{title}</h3>
                <p style="color:#555;font-size:0.9rem;line-height:1.6;">{desc}</p>
            </div>
            """, unsafe_allow_html=True)

    # ✅ Supported Crops — clickable cards
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<h2 id='supported-crops' style='text-align:center;color:#064e3b;font-weight:900;margin-top:50px;font-size:2.2rem;'>Supported Crops | Faslain</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center;color:#555;font-size:1rem;margin-bottom:30px;'>Card par click karein aur seedha us crop ka check karein!</p>", unsafe_allow_html=True)

    cc1, cc2 = st.columns(2)
    with cc1:
        if st.button("🥔 Potato Check Karein →", use_container_width=True, key="crop_potato"):
            st.session_state['nav_override'] = "🥔 Potato (Aloo)"
            st.rerun()
        st.markdown("""
        <div class="crop-card" onclick="void(0)">
            <div style="font-size:4.5rem;margin-bottom:12px;">🥔</div>
            <h3 style="color:#064e3b;font-weight:800;margin:0;">Potato — آلو</h3>
            <p style="color:#666;font-size:0.9rem;margin:6px 0;">3 Diseases | Early Blight, Late Blight, Healthy</p>
            <span class="badge-live">✅ Live — 97% Accuracy</span>
            <div class="crop-arrow">→</div>
        </div>
        """, unsafe_allow_html=True)
    with cc2:
        if st.button("🍅 Tomato Check Karein →", use_container_width=True, key="crop_tomato"):
            st.session_state['nav_override'] = "🍅 Tomato Check"
            st.rerun()
        st.markdown("""
        <div class="crop-card" onclick="void(0)">
            <div style="font-size:4.5rem;margin-bottom:12px;">🍅</div>
            <h3 style="color:#064e3b;font-weight:800;margin:0;">Tomato — ٹماٹر</h3>
            <p style="color:#666;font-size:0.9rem;margin:6px 0;">9 Diseases | Blight, Virus, Mold & more</p>
            <span class="badge-live">✅ Live — 95% Accuracy</span>
            <div class="crop-arrow">→</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    cc3, cc4 = st.columns(2)
    with cc3:
        st.markdown("""
        <div class="crop-card crop-card-soon">
            <div style="font-size:4.5rem;margin-bottom:12px;">🌽</div>
            <h3 style="color:#064e3b;font-weight:800;margin:0;">Corn — مکئی</h3>
            <p style="color:#666;font-size:0.9rem;margin:6px 0;">Model training in progress...</p>
            <span class="badge-soon">🚀 Launching Soon</span>
        </div>
        """, unsafe_allow_html=True)
    with cc4:
        st.markdown("""
        <div class="crop-card crop-card-dev">
            <div style="font-size:4.5rem;margin-bottom:12px;">🫑</div>
            <h3 style="color:#064e3b;font-weight:800;margin:0;">Pepper — مرچ</h3>
            <p style="color:#666;font-size:0.9rem;margin:6px 0;">Dataset preparation underway</p>
            <span class="badge-dev">🛠️ In Development</span>
        </div>
        """, unsafe_allow_html=True)

    # ✅ UPDATED FOOTER — sahi tech stack
    st.markdown("""
    <hr style="border-top:2px solid #a7f3d0;margin-top:80px;">
    <div style="text-align:center;padding:30px;color:#555;">
        <p style="font-weight:700;font-size:1.1rem;">© 2026 Plant Doctor AI — All Rights Reserved</p>
        <p style="font-size:0.9rem;margin-top:10px;">Built with ❤️ using</p>
        <div style="margin-top:8px;">
            <span class="tech-tag" style="background:#fce7f3;color:#be185d;">🎈 Streamlit</span>
            <span class="tech-tag" style="background:#e0e7ff;color:#4338ca;">🤖 Scikit-Learn</span>
            <span class="tech-tag" style="background:#fef3c7;color:#b45309;">🌲 Random Forest</span>
            <span class="tech-tag" style="background:#d1fae5;color:#065f46;">👁️ OpenCV</span>
            <span class="tech-tag" style="background:#ede9fe;color:#5b21b6;">🖼️ Scikit-Image</span>
        </div>
        <p style="font-size:0.8rem;margin-top:15px;opacity:0.8;">Developed by <b>Saqlain Khan</b> (Data Engineer) & <b>Raheel Chishti</b></p>
    </div>
    """, unsafe_allow_html=True)

# Handle nav override from crop cards
if 'nav_override' in st.session_state:
    nav = st.session_state.pop('nav_override')

# ==================== POTATO ====================
elif nav == "🥔 Potato (Aloo)":
    st.header("🥔 Aloo Ki Bimari Check Karein", anchor="alookibimaricheckkarein")
    if not rf_model:
        st.error("⚠️ **Model File Missing!**")
        st.info("Ensure `potato_disease_model.pkl` is in the same folder as `app.py`.")
        st.stop()
    uploaded_file = st.file_uploader("Upload Leaf Photo", type=["jpg","png","jpeg","webp","jfif"])
    if uploaded_file is not None and uploaded_file.size > 5*1024*1024:
        st.error("⚠️ File size too large! Please upload image under 5MB.")
    elif uploaded_file:
        col1, col2 = st.columns([1, 1.5])
        with col1:
            st.image(Image.open(uploaded_file).convert('RGB'), caption="Uploaded Photo", use_column_width=True)
        with col2:
            with st.spinner("Analyzing features (HOG, LBP, Color, GLCM)..."):
                time.sleep(1)
                try:
                    features = extract_all_features(uploaded_file.getvalue())
                    features = np.nan_to_num(features).reshape(1,-1)
                    features_scaled = scaler.transform(features)
                    probs = rf_model.predict_proba(features_scaled)[0]
                    max_idx = np.argmax(probs)
                    conf = probs[max_idx] * 100
                    label = class_names[max_idx].replace("_"," ").title()
                    prob_dict = {l: p*100 for l,p in zip(class_names, probs)}
                except Exception as e:
                    st.error(f"Analysis failed: {e}"); st.stop()
                if conf < 60:
                    st.error("⚠️ **Photo Clear Nahi Hai!**")
                    st.warning(f"Confidence: {conf:.1f}% (Low)\n\nYe Aloo ka patta nahi lag raha. Saaf photo upload karein.")
                    st.stop()
            is_healthy = "healthy" in label.lower()
            bg_color = "#ecfdf5" if is_healthy else "#fef2f2"
            border_color = "#059669" if is_healthy else "#dc2626"
            urdu_name = POTATO_URDU_NAMES.get(label, label)
            local_name = POTATO_LOCAL_NAMES.get(label, label)
            st.markdown(f"""
            <div class='result-box' style='background:{bg_color};border:2px solid {border_color};'>
                <h2 style='color:{border_color};margin:0;font-weight:800;'>{label}</h2>
                <p class='urdu-name' style='color:{border_color};'>{urdu_name}</p>
                <p class='local-name'>🌾 مقامی نام: {local_name}</p>
                <h4 style='color:{border_color};margin-top:10px;font-weight:600;'>Confidence: {conf:.1f}%</h4>
            </div>""", unsafe_allow_html=True)
            st.write("### 📊 Analysis Breakdown")
            for l, p in prob_dict.items():
                st.write(f"**{l.replace('_',' ').title()}**"); st.progress(int(p))
            report_text = f"Plant Doctor AI Report\nDate: {datetime.datetime.now()}\n\nDiagnosis: {label}\nUrdu: {urdu_name}\nConfidence: {conf:.1f}%\nStatus: {'Healthy' if is_healthy else 'Action Needed'}"
            st.download_button(label="📄 Download Report", data=report_text, file_name="potato_report.txt", mime="text/plain")
            if is_healthy:
                st.balloons()
                st.markdown("""<div class='result-box' style='background:white;border-left:5px solid #059669;text-align:left;'><h3 style='color:#059669;font-weight:800;'>🎉 Mubarak Ho!</h3><ul><li>💧 <b>Pani:</b> Waqt par pani dein.</li><li>👀 <b>Nigrani:</b> Rozana pattay check karein.</li></ul></div>""", unsafe_allow_html=True)
            elif "late" in label.lower():
                st.markdown("""<div class='result-box' style='background:white;border-left:5px solid #dc2626;text-align:left;'><h3 style='color:#dc2626;font-weight:800;'>💊 Late Blight Ka Ilaj | پچھیتی جھلس کا علاج</h3><ul><li><b>Spray:</b> Metalaxyl + Mancozeb (2.5g per Liter)</li><li><b>Frequency:</b> Har 7-10 din baad</li><li><b>Organic:</b> Copper Fungicide</li></ul></div>""", unsafe_allow_html=True)
            elif "early" in label.lower():
                st.markdown("""<div class='result-box' style='background:white;border-left:5px solid #d97706;text-align:left;'><h3 style='color:#d97706;font-weight:800;'>💊 Early Blight Ka Ilaj | اگیتی جھلس کا علاج</h3><ul><li><b>Spray:</b> Chlorothalonil ya Azoxystrobin</li><li><b>Organic:</b> Neem Oil spray</li><li><b>Tip:</b> Neeche wale purane patton ko hata dein</li></ul></div>""", unsafe_allow_html=True)

# ==================== TOMATO ====================
elif nav == "🍅 Tomato Check":
    st.header("🍅 Tamatar Ki Bimari Check Karein")
    if not t_model:
        st.error("⚠️ **Tomato Model File Missing!**")
        st.info("Ensure `tomato_disease_model_9_classes.pkl` is in the same folder as `app.py`.")
        st.stop()
    uploaded_file = st.file_uploader("Upload Tomato Leaf Photo", type=["jpg","png","jpeg","webp","jfif"])
    if uploaded_file is not None and uploaded_file.size > 5*1024*1024:
        st.error("⚠️ File size too large!")
    elif uploaded_file:
        col1, col2 = st.columns([1, 1.5])
        with col1:
            st.image(Image.open(uploaded_file).convert('RGB'), caption="Uploaded Photo", use_column_width=True)
        with col2:
            with st.spinner("Analyzing Tomato features..."):
                time.sleep(1)
                try:
                    features = extract_all_features(uploaded_file.getvalue())
                    features = np.nan_to_num(features).reshape(1,-1)
                    features_scaled = t_scaler.transform(features)
                    probs = t_model.predict_proba(features_scaled)[0]
                    max_idx = np.argmax(probs)
                    conf = probs[max_idx] * 100
                    label = t_class_names[max_idx].replace("_"," ").title()
                    prob_dict = {l: p*100 for l,p in zip(t_class_names, probs)}
                except Exception as e:
                    st.error(f"Analysis failed: {e}"); st.stop()
                if conf < 60:
                    st.error("⚠️ **Photo Clear Nahi Hai!**")
                    st.warning(f"Confidence: {conf:.1f}% (Low)\n\nYe Tamatar ka patta nahi lag raha. Saaf photo upload karein.")
                    st.stop()
            is_healthy = "healthy" in label.lower()
            bg_color = "#ecfdf5" if is_healthy else "#fef2f2"
            border_color = "#059669" if is_healthy else "#dc2626"
            urdu_name = TOMATO_URDU_NAMES.get(label, label)
            local_name = TOMATO_LOCAL_NAMES.get(label, label)
            st.markdown(f"""
            <div class='result-box' style='background:{bg_color};border:2px solid {border_color};'>
                <h2 style='color:{border_color};margin:0;font-weight:800;'>{label}</h2>
                <p class='urdu-name' style='color:{border_color};'>{urdu_name}</p>
                <p class='local-name'>🌾 مقامی نام: {local_name}</p>
                <h4 style='color:{border_color};margin-top:10px;font-weight:600;'>Confidence: {conf:.1f}%</h4>
            </div>""", unsafe_allow_html=True)
            st.write("### 📊 Analysis Breakdown")
            for l, p in prob_dict.items():
                st.write(f"**{l.replace('_',' ').title()}**"); st.progress(int(p))
            report_text = f"Plant Doctor AI Report\nDate: {datetime.datetime.now()}\n\nDiagnosis: {label}\nUrdu: {urdu_name}\nConfidence: {conf:.1f}%\nStatus: {'Healthy' if is_healthy else 'Action Needed'}"
            st.download_button(label="📄 Download Report", data=report_text, file_name="tomato_report.txt", mime="text/plain")
            if is_healthy:
                st.balloons()
                st.markdown("""<div class='result-box' style='background:white;border-left:5px solid #059669;text-align:left;'><h3 style='color:#059669;font-weight:800;'>🎉 Mubarak Ho! | مبارک ہو</h3><ul><li>💧 <b>Pani:</b> Waqt par pani dein.</li><li>👀 <b>Nigrani:</b> Rozana pattay check karein.</li></ul></div>""", unsafe_allow_html=True)
            elif "virus" in label.lower() or "mosaic" in label.lower():
                st.markdown("""<div class='result-box' style='background:white;border-left:5px solid #dc2626;text-align:left;'><h3 style='color:#dc2626;font-weight:800;'>⚠️ Alert (Virus) | وائرس خبردار</h3><ul><li><b>Faori Qadam:</b> Mutasira poudon ko ukhad kar jala dein.</li><li><b>Wajah:</b> Safaid makhi (Whitefly) se phailta hai.</li><li><b>Spray:</b> Insecticide ka spray karein.</li></ul></div>""", unsafe_allow_html=True)
            else:
                st.markdown("""<div class='result-box' style='background:white;border-left:5px solid #d97706;text-align:left;'><h3 style='color:#d97706;font-weight:800;'>💊 Fungal/Bacterial Treatment | پھپھوندی علاج</h3><ul><li><b>Spray:</b> Copper Fungicide ya Neem Oil</li><li><b>Ehtiyat:</b> Poudon ke darmiyan fasla rakhein.</li><li><b>Pani:</b> Sirf jaron mein pani dein.</li></ul></div>""", unsafe_allow_html=True)

# ==================== CORN ====================
elif nav == "🌽 Corn Field":
    st.markdown("""
    <div style="text-align:center;padding:60px 20px;">
        <div style="font-size:5rem;">🌽</div>
        <h2 style="color:#064e3b;font-weight:800;">Makki — مکئی</h2>
        <p style="color:#555;font-size:1.1rem;">Model training jari hai — jald aa raha hai!</p>
        <span style="background:linear-gradient(90deg,#f59e0b,#ef4444);color:white;padding:8px 24px;border-radius:20px;font-weight:700;">🚀 Launching Soon</span>
    </div>
    """, unsafe_allow_html=True)

# ==================== PEPPER ====================
elif nav == "🫑 Pepper (Mirch)":
    st.markdown("""
    <div style="text-align:center;padding:60px 20px;">
        <div style="font-size:5rem;">🫑</div>
        <h2 style="color:#064e3b;font-weight:800;">Pepper — مرچ</h2>
        <p style="color:#555;font-size:1.1rem;">Dataset tayyar ho raha hai — abhi development mein hai.</p>
        <span style="background:linear-gradient(90deg,#6366f1,#8b5cf6);color:white;padding:8px 24px;border-radius:20px;font-weight:700;">🛠️ In Development</span>
    </div>
    """, unsafe_allow_html=True)  
    