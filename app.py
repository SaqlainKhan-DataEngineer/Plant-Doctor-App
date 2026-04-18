import streamlit as st
from PIL import Image
import cv2
import numpy as np
import joblib
import time
import datetime
import requests
import os
import gc
import traceback
import functools
from skimage.feature import hog, local_binary_pattern, graycomatrix, graycoprops

# --- 1. PAGE SETUP ---
st.set_page_config(
    page_title="Plant Doctor AI",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Handle nav override from crop cards
if 'nav_override' in st.session_state:
    nav_default = st.session_state.pop('nav_override')
else:
    nav_default = "🏠 Home Page"

# Handle quick scan target
quick_scan_target = st.session_state.pop('quick_scan_target', None)

# --- 2. WEATHER ---
def get_real_weather():
    """Fetch live temperature, wind speed, AND real humidity from Open-Meteo."""
    try:
        url = (
            "https://api.open-meteo.com/v1/forecast"
            "?latitude=31.5204&longitude=74.3587"
            "&current_weather=true"
            "&hourly=relative_humidity_2m"
            "&forecast_days=1"
        )
        response = requests.get(url, timeout=3)
        data = response.json()
        temp = data['current_weather']['temperature']
        wind = data['current_weather']['windspeed']
        # Pick current hour's humidity from hourly array
        humidity = data['hourly']['relative_humidity_2m'][datetime.datetime.now().hour]
        return temp, wind, humidity
    except:
        return 28, 12, 65   # sensible fallbacks

temp, wind, humidity = get_real_weather()

# --- 3. CROP CONFIG (IMPROVEMENT #1: Centralized config instead of scattered hardcoded values) ---
TOMATO_URDU_NAMES = {"Bacterial Spot": "بیکٹیریل دھبے", "Early Blight": "اگیتی جھلس", "Late Blight": "پچھیتی جھلس", "Leaf Mold": "پتے کی پھپھوندی", "Septoria Leaf Spot": "سیپٹوریا دھبے", "Target Spot": "ہدف دھبے", "Yellow Leaf Curl Virus": "پیلا پتہ مروڑ وائرس", "Mosaic Virus": "موزیک وائرس", "Healthy": "صحت مند"}
TOMATO_LOCAL_NAMES = {"Bacterial Spot": "ٹماٹر تے کالے داغ", "Early Blight": "اگیتی سڑن", "Late Blight": "پچھیتی سڑن", "Leaf Mold": "پتیاں تے پھپھوند", "Septoria Leaf Spot": "پتیاں تے چھوٹے داغ", "Target Spot": "گول داغ روگ", "Yellow Leaf Curl Virus": "پیلا پتہ وائرس", "Mosaic Virus": "چتکبری بیماری", "Healthy": "تندرست فصل"}
POTATO_URDU_NAMES = {"Early Blight": "اگیتی جھلس", "Late Blight": "پچھیتی جھلس", "Healthy": "صحت مند"}
POTATO_LOCAL_NAMES = {"Early Blight": "اگیتی سڑن", "Late Blight": "پچھیتی سڑن", "Healthy": "تندرست فصل"}

# Pepper — Gemini ne model train kiya, yeh names add ki hain
PEPPER_URDU_NAMES = {"Bacterial Spot": "بیکٹیریل دھبے", "Healthy": "صحت مند"}
PEPPER_LOCAL_NAMES = {"Bacterial Spot": "مرچ تے کالے دھبے", "Healthy": "تندرست فصل"}

# Corn — Gemini ne model train kiya, yeh names add ki hain
CORN_URDU_NAMES = {"Blight": "جھلس روگ", "Common Rust": "کنگی روگ", "Gray Leaf Spot": "سرمئی دھبے", "Healthy": "صحت مند"}
CORN_LOCAL_NAMES = {"Blight": "پتیاں دا سڑنا", "Common Rust": "مکئی دی کنگی", "Gray Leaf Spot": "سرمئی داغ", "Healthy": "تندرست فصل"}

CROP_CONFIG = {
    "potato": {
        "model_file": "potato_disease_model.pkl",
        "urdu_names": POTATO_URDU_NAMES,
        "local_names": POTATO_LOCAL_NAMES,
        "emoji": "🥔",
        "display_name": "Potato — آلو",
        "accuracy": "97%",
        "diseases": 3,
        "nav_key": "🥔 Potato (Aloo)",
        "uploader_label": "Upload Potato Leaf Photo / آلو کا پتہ اپلوڈ کریں",
        "model_missing_msg": "⚠️ **Model File Missing!** Please ensure `potato_disease_model.pkl` is in the project directory.",
        "header_title": "Potato Disease Scan | آلو کی بیماری",
        "header_sub": "Random Forest · HOG + LBP + GLCM + Color · 97% Accuracy",
    },
    "tomato": {
        "model_file": "tomato_disease_model_9_classes.pkl",
        "urdu_names": TOMATO_URDU_NAMES,
        "local_names": TOMATO_LOCAL_NAMES,
        "emoji": "🍅",
        "display_name": "Tomato — ٹماٹر",
        "accuracy": "95%",
        "diseases": 9,
        "nav_key": "🍅 Tomato Check",
        "uploader_label": "Upload Tomato Leaf Photo / ٹماٹر کا پتہ اپلوڈ کریں",
        "model_missing_msg": "⚠️ **Tomato Model File Missing!** Please ensure `tomato_disease_model_9_classes.pkl` is in the project directory.",
        "header_title": "Tomato Disease Scan | ٹماٹر کی بیماری",
        "header_sub": "Random Forest · HOG + LBP + GLCM + Color · 95% Accuracy · 9 Classes",
    },
    "pepper": {
        "model_file": "pepper_disease_model.pkl",
        "urdu_names": PEPPER_URDU_NAMES,
        "local_names": PEPPER_LOCAL_NAMES,
        "emoji": "🫑",
        "display_name": "Pepper — مرچ",
        "accuracy": "99%",
        "diseases": 2,
        "nav_key": "🫑 Pepper (Mirch)",
        "uploader_label": "Upload Pepper Leaf Photo / مرچ کا پتہ اپلوڈ کریں",
        "model_missing_msg": "⚠️ **Pepper Model File Missing!** Please ensure `pepper_disease_model.pkl` is in the project directory.",
        "header_title": "Pepper Disease Scan | مرچ کی بیماری",
        "header_sub": "Random Forest · HOG + LBP + GLCM + Color · 99% Accuracy",
    },
    "corn": {
        "model_file": "corn_disease_model.pkl",
        "urdu_names": CORN_URDU_NAMES,
        "local_names": CORN_LOCAL_NAMES,
        "emoji": "🌽",
        "display_name": "Corn — مکئی",
        "accuracy": "87%",
        "diseases": 4,
        "nav_key": "🌽 Corn Field",
        "uploader_label": "Upload Corn Leaf Photo / مکئی کا پتہ اپلوڈ کریں",
        "model_missing_msg": "⚠️ **Corn Model File Missing!** Please ensure `corn_disease_model.pkl` is in the project directory.",
        "header_title": "Corn Disease Scan | مکئی کی بیماری",
        "header_sub": "Random Forest · HOG + LBP + GLCM + Color · 87% Accuracy",
    },
}

# --- 4. MODEL LOADING — Graceful degradation (v3 improvement) ---
# App starts even if one or both model files are missing.
@st.cache_resource
def safe_load_models():
    """Load all crop models + master crop detector. Missing models don't crash app."""
    models = {}
    model_files = {
        "potato": ("potato_disease_model.pkl",          "class_names"),
        "tomato": ("tomato_disease_model_9_classes.pkl", "class_names"),
        "pepper": ("pepper_disease_model.pkl",           "class_names"),
        "corn":   ("corn_disease_model.pkl",             "class_names"),
        "master": ("robust_crop_detector_model.pkl", "class_names"),# ML crop detector
    }
    for crop_key, (file_path, cls_key) in model_files.items():
        try:
            data = joblib.load(file_path)
            models[crop_key] = (data['model'], data['scaler'], data[cls_key])
        except FileNotFoundError:
            models[crop_key] = (None, None, None)
        except Exception:
            models[crop_key] = (None, None, None)
    return models

MODELS = safe_load_models()

# Keep these for any legacy references
rf_model, scaler, class_names = MODELS.get("potato", (None, None, None))
t_model, t_scaler, t_class_names = MODELS.get("tomato", (None, None, None))

# --- 6. ERROR HANDLING DECORATOR (IMPROVEMENT #2: Defensive programming) ---
def safe_analysis(func):
    """Decorator for safe analysis execution"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except cv2.error as e:
            st.error("📷 **Image Processing Error** — Please upload a clear, uncorrupted image file (JPG/PNG).")
            return None
        except ValueError as e:
            st.error(f"⚠️ **Validation Error** — {str(e)}")
            return None
        except Exception as e:
            st.error("⚠️ **Unexpected Error during analysis.**")
            with st.expander("Technical Details (for debugging)"):
                st.code(traceback.format_exc())
            return None
    return wrapper

# --- 7. FEATURE EXTRACTION WITH ERROR HANDLING (IMPROVEMENT #3) ---
@safe_analysis
def extract_all_features(image_bytes):
    # Input validation
    if len(image_bytes) > 10 * 1024 * 1024:
        raise ValueError("Image too large. Please use images under 10MB.")

    nparr = np.frombuffer(image_bytes, np.uint8)
    if nparr.size == 0:
        raise ValueError("Empty image data received.")

    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise cv2.error("Could not decode image. File may be corrupted.")

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

    result = np.hstack([f_color, f_hog, f_lbp, f_glcm])

    # Explicit memory cleanup (IMPROVEMENT #2)
    del img, gray_img, hsv, lbp, glcm
    gc.collect()

    return result

# --- 8. CROP AUTO-DETECTOR (v3: Universal upload, AI detects crop type) ---
class CropAutoDetector:
    """
    ML-based crop detection using the Master Crop Detector model (93% accuracy).
    Falls back to color/shape heuristics if master model is unavailable.
    """

    @staticmethod
    def detect(image_bytes):
        """
        Returns (detected_crop_key, confidence_float, message_str).
        First tries ML master model, then falls back to heuristics.
        """
        # --- Try ML Master Model first ---
        master_model, master_scaler, master_classes = MODELS.get("master", (None, None, None))
        if master_model:
            try:
                features = extract_all_features(image_bytes)
                if features is not None:
                    features = np.nan_to_num(features).reshape(1, -1)
                    features_scaled = master_scaler.transform(features)
                    probs = master_model.predict_proba(features_scaled)[0]
                    max_idx = np.argmax(probs)
                    conf = float(probs[max_idx])
                    best_crop = master_classes[max_idx]

                    if conf >= 0.5:
                        crop_names = {"potato": "Aloo (Potato)", "tomato": "Tamatar (Tomato)",
                                      "pepper": "Mirch (Pepper)", "corn": "Makki (Corn)"}
                        msg = f"{crop_names.get(best_crop, best_crop.title())} detect hua — {conf:.0%} confidence"
                        return best_crop, conf, msg
            except Exception:
                pass  # Fall through to heuristics

        # --- Fallback: Color + Shape Heuristics ---
        try:
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is None:
                return None, 0.0, "Image decode failed."

            img_resized = cv2.resize(img, (128, 128))
            hsv = cv2.cvtColor(img_resized, cv2.COLOR_BGR2HSV)
            mean_hue = float(np.mean(hsv[:, :, 0]))
            mean_sat = float(np.mean(hsv[:, :, 1])) / 255.0
            mean_val = float(np.mean(hsv[:, :, 2])) / 255.0
            h, w = img.shape[:2]
            aspect = w / max(h, 1)

            scores = {"potato": 0.0, "tomato": 0.0, "pepper": 0.0, "corn": 0.0}

            if 30 <= mean_hue <= 90 and 0.8 <= aspect <= 1.6:
                scores["potato"] += 0.5
            if mean_sat > 0.2:   scores["potato"] += 0.2
            if mean_val > 0.3:   scores["potato"] += 0.1

            if 30 <= mean_hue <= 80 and mean_sat > 0.28:
                scores["tomato"] += 0.5
            if 0.9 <= aspect <= 1.7: scores["tomato"] += 0.15
            if mean_val > 0.35:      scores["tomato"] += 0.1

            if 35 <= mean_hue <= 85 and 0.7 <= aspect <= 1.5:
                scores["pepper"] += 0.4
            if mean_sat > 0.3:   scores["pepper"] += 0.15
            if mean_val > 0.2:   scores["pepper"] += 0.15

            if 30 <= mean_hue <= 85 and (aspect > 1.8 or aspect < 0.6):
                scores["corn"] += 0.6
            if mean_sat > 0.15:  scores["corn"] += 0.1

            best = max(scores, key=scores.get)
            conf = round(min(scores[best], 0.95), 2)

            if conf < 0.5:
                return None, conf, "Could not confidently detect crop. Please select manually."

            crop_names = {"potato": "Aloo (Potato)", "tomato": "Tamatar (Tomato)",
                          "pepper": "Mirch (Pepper)", "corn": "Makki (Corn)"}
            msg = f"{crop_names[best]} detect hua — {conf:.0%} confidence"
            return best, conf, msg

        except Exception:
            return None, 0.0, "Detection error. Please select crop manually."


def render_universal_upload():
    """
    Single drag-and-drop zone for any leaf.
    AI auto-detects crop; user can override manually.
    Returns (uploaded_file, crop_key) or (None, None).
    """
    st.markdown("""
    <style>
    .univ-upload-box {
        border: 3px dashed #34d399;
        border-radius: 24px;
        padding: 40px 32px;
        text-align: center;
        background: linear-gradient(135deg, #ecfdf5, #f0fdf4);
        transition: all 0.3s ease;
        margin-bottom: 20px;
    }
    .univ-upload-box:hover {
        border-color: #059669;
        background: linear-gradient(135deg, #d1fae5, #ecfdf5);
    }
    .univ-upload-title { font-size: 1.2rem; font-weight: 800; color: #064e3b; margin-bottom: 6px; }
    .univ-upload-sub   { color: #6b7280; font-size: 0.88rem; }
    .detect-result-box {
        background: white; border-radius: 16px; padding: 18px 22px;
        border: 2px solid #d1fae5; margin-top: 14px;
        box-shadow: 0 4px 16px rgba(16,185,129,0.1);
    }
    .detect-label  { font-size: 0.65rem; color: #6b7280; font-weight: 700;
                     text-transform: uppercase; letter-spacing: 1px; margin-bottom: 6px; }
    .detect-crop   { font-size: 1.4rem; font-weight: 900; color: #064e3b; }
    .detect-conf   { font-size: 0.82rem; color: #059669; font-weight: 600; margin-top: 2px; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="univ-upload-box">
        <div style="font-size:3rem;margin-bottom:10px;">🌿</div>
        <div class="univ-upload-title">Koi bhi fasal ka patta drop karein</div>
        <div class="univ-upload-sub">AI khud detect karega — Potato, Tomato, Pepper, Corn · Ya manually select karein</div>
        <div style="display:flex;gap:10px;justify-content:center;margin-top:14px;flex-wrap:wrap;">
            <span style="background:#d1fae5;color:#065f46;padding:4px 12px;border-radius:20px;font-size:0.75rem;font-weight:700;">🥔 Potato</span>
            <span style="background:#fee2e2;color:#991b1b;padding:4px 12px;border-radius:20px;font-size:0.75rem;font-weight:700;">🍅 Tomato</span>
            <span style="background:#ede9fe;color:#4c1d95;padding:4px 12px;border-radius:20px;font-size:0.75rem;font-weight:700;">🫑 Pepper</span>
            <span style="background:#fef3c7;color:#92400e;padding:4px 12px;border-radius:20px;font-size:0.75rem;font-weight:700;">🌽 Corn</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    uploaded_file = st.file_uploader(
        "Patta upload karein / Drop leaf photo here",
        type=["jpg", "png", "jpeg", "webp", "jfif"],
        key="universal_uploader"
    )

    if not uploaded_file:
        return None, None

    # Auto-detect crop
    detected_crop, conf, msg = CropAutoDetector.detect(uploaded_file.getvalue())

    col_img, col_detect = st.columns([1, 1.4])
    with col_img:
        pil_img = Image.open(uploaded_file).convert('RGB')
        st.image(pil_img, caption="📷 Uploaded Leaf", use_column_width=True)

    with col_detect:
        if detected_crop and conf >= 0.5:
            emoji_map = {"potato": "🥔", "tomato": "🍅", "pepper": "🫑", "corn": "🌽"}
            emoji = emoji_map.get(detected_crop, "🌿")
            st.markdown(f"""
            <div class="detect-result-box">
                <div class="detect-label">🤖 AI Detection Result</div>
                <div class="detect-crop">{emoji} {detected_crop.title()} Detect Hua!</div>
                <div class="detect-conf">✅ Confidence: {conf:.0%}</div>
                <div style="font-size:0.78rem;color:#6b7280;margin-top:6px;">{msg}</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="detect-result-box" style="border-color:#fde68a;">
                <div class="detect-label">⚠️ Manual Selection Required</div>
                <div style="font-size:0.88rem;color:#6b7280;margin-top:4px;">AI confidently detect nahi kar saka. Neeche se crop chunein.</div>
            </div>
            """, unsafe_allow_html=True)

        # Manual override — always visible
        st.markdown("<div style='margin-top:14px;'></div>", unsafe_allow_html=True)
        options = ["🥔 Potato (Aloo)", "🍅 Tomato (Tamatar)", "🫑 Pepper (Mirch)", "🌽 Corn (Makki)"]
        default_idx = 0
        if detected_crop == "tomato": default_idx = 1
        elif detected_crop == "pepper": default_idx = 2
        elif detected_crop == "corn": default_idx = 3
        manual = st.selectbox(
            "Crop confirm karein ya change karein:",
            options,
            index=default_idx,
            key="universal_crop_select"
        )
        if "Potato" in manual: final_crop = "potato"
        elif "Tomato" in manual: final_crop = "tomato"
        elif "Pepper" in manual: final_crop = "pepper"
        else: final_crop = "corn"

        if st.button("🔬 Is Patte Ka Analysis Karein", type="primary", use_container_width=True, key="universal_analyze_btn"):
            return uploaded_file, final_crop

    return None, None


# --- 10. CSS (Split into critical + component CSS) ---
def get_critical_css():
    """Critical above-the-fold styles"""
    return """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800;900&family=Noto+Nastaliq+Urdu&family=Space+Mono:wght@400;700&display=swap');

:root {
    --emerald-900: #064e3b;
    --emerald-800: #065f46;
    --emerald-700: #047857;
    --emerald-600: #059669;
    --emerald-500: #10b981;
    --emerald-400: #34d399;
    --emerald-300: #6ee7b7;
    --emerald-100: #d1fae5;
    --emerald-50:  #ecfdf5;
    --amber-500:   #f59e0b;
    --red-600:     #dc2626;
    --red-500:     #ef4444;
    --glass-white: rgba(255,255,255,0.85);
    --glass-border: rgba(255,255,255,0.6);
    --shadow-soft: 0 8px 32px rgba(6,78,59,0.12);
    --shadow-card: 0 20px 60px rgba(6,78,59,0.15);
    --shadow-glow: 0 0 40px rgba(16,185,129,0.25);
    --radius-xl:   28px;
    --radius-lg:   20px;
    --radius-md:   14px;
    --radius-sm:   10px;
}

html, body, [class*="css"] {
    font-family: 'Plus Jakarta Sans', sans-serif;
    scroll-behavior: smooth;
}

@keyframes fadeInUp    { from { opacity:0; transform:translateY(24px); } to { opacity:1; transform:translateY(0); } }
@keyframes fadeInScale { from { opacity:0; transform:scale(0.92); } to { opacity:1; transform:scale(1); } }
@keyframes floatY      { 0%,100% { transform:translateY(0); } 50% { transform:translateY(-10px); } }
@keyframes floatLogo   { 0%,100% { transform:translateY(0); box-shadow:0 0 20px rgba(16,185,129,0.35); } 50% { transform:translateY(-8px); box-shadow:0 0 40px rgba(16,185,129,0.6); } }
@keyframes pulseRed    { 0% { box-shadow:0 0 0 0 rgba(239,68,68,0.7); } 70% { box-shadow:0 0 0 10px rgba(239,68,68,0); } 100% { box-shadow:0 0 0 0 rgba(239,68,68,0); } }
@keyframes shimmer     { 0% { background-position:-200% center; } 100% { background-position:200% center; } }
@keyframes scroll      { 0% { transform:translateX(0); } 100% { transform:translateX(calc(-600px * 6)); } }
@keyframes gradBG      { 0% { background-position:0% 50%; } 50% { background-position:100% 50%; } 100% { background-position:0% 50%; } }
@keyframes particleDrift { 0% { transform:translateY(0) translateX(0) rotate(0deg); opacity:0.6; } 100% { transform:translateY(120px) translateX(-80px) rotate(180deg); opacity:0; } }
@keyframes rotateOrbit { from { transform:rotate(0deg); } to { transform:rotate(360deg); } }
@keyframes scanLine    { 0% { top:-5%; } 100% { top:105%; } }
@keyframes reportSlide { from { opacity:0; transform:translateX(-20px); } to { opacity:1; transform:translateX(0); } }
@keyframes pulseDot    { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }

/* Respect user's reduced-motion preference (IMPROVEMENT #5) */
@media (prefers-reduced-motion: reduce) {
    *, *::before, *::after {
        animation-duration: 0.01ms !important;
        animation-iteration-count: 1 !important;
        transition-duration: 0.01ms !important;
    }
}

.stApp::before {
    content:""; position:fixed; top:-50%; left:-50%; width:200%; height:200%;
    background-image:
        radial-gradient(circle at 20px 30px,  rgba(16,185,129,0.35) 0, transparent 2px),
        radial-gradient(circle at 60px 90px,  rgba(52,211,153,0.45) 0, transparent 2px),
        radial-gradient(circle at 100px 50px, rgba(6,78,59,0.4)     0, transparent 3px),
        radial-gradient(circle at 140px 130px,rgba(4,120,87,0.35)   0, transparent 2px),
        radial-gradient(circle at 30px 160px, rgba(110,231,183,0.3) 0, transparent 2px);
    background-repeat:repeat; background-size:200px 200px;
    animation:particleDrift 30s linear infinite; pointer-events:none; z-index:0;
}

[data-testid="stSidebar"] {
    background: linear-gradient(160deg, #022c22 0%, #064e3b 50%, #047857 100%);
    border-right: 1px solid rgba(52,211,153,0.15);
}
[data-testid="stSidebar"] * { color: #ecfdf5 !important; }
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label {
    background: rgba(255,255,255,0.06);
    padding: 14px 18px; border-radius: 14px; margin-bottom: 10px !important;
    border: 1px solid rgba(255,255,255,0.08); width:100%; display:flex; align-items:center;
    transition: all 0.3s ease; cursor:pointer; letter-spacing:0.3px;
}
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label:hover {
    background: rgba(52,211,153,0.15); border-color:rgba(52,211,153,0.4);
    transform:translateX(4px);
}
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] div[aria-checked="true"] + div + label {
    background: linear-gradient(90deg, rgba(5,150,105,0.7), rgba(16,185,129,0.5)) !important;
    border:1px solid rgba(110,231,183,0.5) !important; font-weight:700;
    box-shadow:0 4px 20px rgba(16,185,129,0.3) !important;
}
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] div[role="radio"] { display:none; }
[data-testid="stSidebar"] hr { border-color: rgba(52,211,153,0.2) !important; }

/* Global buttons */
.stButton > button {
    border-radius: var(--radius-md) !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-weight: 700 !important; letter-spacing: 0.3px !important;
    transition: all 0.3s ease !important;
    min-height: 44px !important;
}
.stButton > button[kind="primary"] {
    background: linear-gradient(90deg, var(--emerald-700), var(--emerald-500)) !important;
    border: none !important;
    box-shadow: 0 4px 20px rgba(16,185,129,0.35) !important;
}
.stButton > button[kind="primary"]:hover {
    transform: translateY(-3px) !important;
    box-shadow: 0 8px 30px rgba(16,185,129,0.45) !important;
}

img { border-radius: var(--radius-lg); box-shadow: var(--shadow-soft); transition: transform 0.3s; }
</style>
"""

def get_home_css():
    """Home page specific styles"""
    return """
<style>
.hero-wrapper {
    position:relative; border-radius:var(--radius-xl); overflow:hidden;
    margin-bottom:24px; animation:fadeInScale 0.9s ease-out both;
    border:1px solid rgba(255,255,255,0.7);
    box-shadow:var(--shadow-card), inset 0 1px 0 rgba(255,255,255,0.8);
}
.hero-bg {
    background: linear-gradient(-45deg, #a7f3d0, #d1fae5, #ecfdf5, #6ee7b7, #34d399);
    background-size:400% 400%; animation:gradBG 12s ease infinite;
    padding:56px 32px 48px; text-align:center; position:relative;
}
.hero-badge {
    display:inline-flex; align-items:center; gap:8px;
    background:rgba(4,120,87,0.12); border:1px solid rgba(5,150,105,0.3);
    color:var(--emerald-800); padding:6px 18px; border-radius:50px;
    font-size:0.78rem; font-weight:700; letter-spacing:2px; text-transform:uppercase;
    margin-bottom:18px; backdrop-filter:blur(10px);
}
.hero-title {
    font-size:clamp(2.8rem, 6vw, 5rem); font-weight:900; color:var(--emerald-900);
    line-height:1.05; margin:0 0 14px; letter-spacing:-1.5px;
    text-shadow:0 2px 20px rgba(255,255,255,0.8), 0 4px 40px rgba(6,78,59,0.15);
}
.hero-sub { font-size:clamp(1rem,2vw,1.2rem); color:var(--emerald-800); font-weight:600; margin:0 0 8px; }
.hero-desc { font-size:0.95rem; color:var(--emerald-700); max-width:520px; margin:0 auto; line-height:1.7; opacity:0.85; }
.hero-orb { position:absolute; border-radius:50%; pointer-events:none; background:radial-gradient(circle, rgba(52,211,153,0.25), transparent 70%); }
.orb-1 { width:300px; height:300px; top:-80px; right:-60px; animation:rotateOrbit 20s linear infinite; }
.orb-2 { width:200px; height:200px; bottom:-40px; left:-40px; animation:rotateOrbit 15s linear infinite reverse; }

.stat-grid { display:grid; grid-template-columns:repeat(4,1fr); gap:16px; margin-bottom:28px; }
.stat-card {
    background:var(--glass-white); backdrop-filter:blur(20px);
    border:1px solid var(--glass-border); border-radius:var(--radius-lg);
    padding:20px 16px; text-align:center;
    box-shadow:var(--shadow-soft); transition:all 0.3s ease;
    animation:fadeInUp 0.8s ease-out both; position:relative; overflow:hidden;
}
.stat-card::before {
    content:""; position:absolute; top:0; left:0; right:0; height:3px;
    background:linear-gradient(90deg, var(--emerald-500), var(--emerald-300));
    border-radius:var(--radius-lg) var(--radius-lg) 0 0;
}
.stat-card:hover { transform:translateY(-6px); box-shadow:var(--shadow-card); }
.stat-val { font-size:2.2rem; font-weight:900; color:var(--emerald-900); letter-spacing:-1px; }
.stat-lbl { font-size:0.78rem; color:var(--emerald-700); font-weight:600; text-transform:uppercase; letter-spacing:1px; margin-top:4px; }

.slider-container {
    width:100%; overflow:hidden; border-radius:var(--radius-xl);
    box-shadow:var(--shadow-card); border:2px solid rgba(255,255,255,0.7);
    background:#000; height:400px; position:relative;
}
.slider-container::after {
    content:""; position:absolute; top:0; left:0; right:0; bottom:0;
    background:linear-gradient(90deg,rgba(0,0,0,0.3) 0%, transparent 15%, transparent 85%, rgba(0,0,0,0.3) 100%);
    pointer-events:none; border-radius:var(--radius-xl); z-index:1;
}
.slide-track { display:flex; width:calc(600px * 12); animation:scroll 60s linear infinite; }
.slide-track:hover { animation-play-state:paused; }
.slide { width:600px; height:400px; flex-shrink:0; padding:0 4px; }
.slide img { width:100%; height:100%; object-fit:cover; border-radius:14px; transition:transform 0.5s, filter 0.5s; }
.slide img:hover { transform:scale(1.05); filter:brightness(1.08) saturate(1.1); }

.scan-cta-wrap {
    background:linear-gradient(135deg, var(--emerald-900), var(--emerald-700));
    border-radius:var(--radius-xl); padding:40px 32px; text-align:center;
    box-shadow:var(--shadow-card); position:relative; overflow:hidden;
    border:1px solid rgba(52,211,153,0.2); margin:32px 0;
    animation:fadeInUp 0.8s ease-out both;
}
.scan-cta-wrap::before {
    content:""; position:absolute; top:-40%; right:-10%; width:350px; height:350px;
    border-radius:50%; background:radial-gradient(circle, rgba(52,211,153,0.15), transparent 70%);
    pointer-events:none;
}
.scan-cta-wrap::after {
    content:""; position:absolute; bottom:-50%; left:-5%; width:280px; height:280px;
    border-radius:50%; background:radial-gradient(circle, rgba(110,231,183,0.1), transparent 70%);
    pointer-events:none;
}

.crop-card {
    background:var(--glass-white); backdrop-filter:blur(25px);
    padding:32px 24px 28px; border-radius:var(--radius-xl);
    border:1.5px solid var(--glass-border);
    box-shadow:var(--shadow-soft); min-height:200px;
    display:flex; flex-direction:column; align-items:center; justify-content:center;
    transition:all 0.35s cubic-bezier(0.175,0.885,0.32,1.275);
    position:relative; overflow:hidden; text-align:center;
}
.crop-card::after {
    content:""; position:absolute; bottom:0; left:0; right:0; height:4px;
    background:linear-gradient(90deg, var(--emerald-500), var(--emerald-300));
    transform:scaleX(0); transition:transform 0.35s ease; border-radius:0 0 var(--radius-xl) var(--radius-xl);
}
.crop-card:hover { transform:translateY(-10px); box-shadow:var(--shadow-card), var(--shadow-glow); border-color:rgba(52,211,153,0.5); }
.crop-card:hover::after { transform:scaleX(1); }
.crop-card-soon  { border:2px dashed rgba(245,158,11,0.5); background:rgba(255,251,235,0.85); }
.crop-card-dev   { border:2px dashed rgba(139,92,246,0.5); background:rgba(245,243,255,0.85); }
.crop-emoji { font-size:3.8rem; margin-bottom:12px; filter:drop-shadow(0 6px 12px rgba(0,0,0,0.1)); transition:transform 0.3s; }
.crop-card:hover .crop-emoji { transform:scale(1.15) rotate(-5deg); }

.hiw-card {
    background:var(--glass-white); backdrop-filter:blur(25px);
    padding:32px 24px; border-radius:var(--radius-xl); text-align:center;
    border:1px solid var(--glass-border); box-shadow:var(--shadow-soft);
    height:100%; display:flex; flex-direction:column; align-items:center;
    transition:all 0.4s cubic-bezier(0.175,0.885,0.32,1.275);
    animation:fadeInUp 0.8s ease-out both; position:relative; overflow:hidden;
}
.hiw-card::before {
    content:""; position:absolute; inset:0; border-radius:var(--radius-xl);
    background:linear-gradient(135deg, rgba(52,211,153,0.06), transparent);
    opacity:0; transition:opacity 0.4s;
}
.hiw-card:hover { transform:translateY(-14px) scale(1.02); box-shadow:var(--shadow-card), var(--shadow-glow); }
.hiw-card:hover::before { opacity:1; }
.hiw-icon-wrap {
    width:72px; height:72px; border-radius:24px; display:flex; align-items:center; justify-content:center;
    background:linear-gradient(135deg, var(--emerald-100), var(--emerald-50));
    border:2px solid rgba(52,211,153,0.3); font-size:2rem; margin-bottom:18px;
    box-shadow:0 8px 24px rgba(16,185,129,0.15);
    transition:transform 0.3s, box-shadow 0.3s;
}
.hiw-card:hover .hiw-icon-wrap { transform:scale(1.1) rotate(-5deg); box-shadow:0 12px 32px rgba(16,185,129,0.3); }
.hiw-step { position:absolute; top:16px; right:18px; font-family:'Space Mono', monospace; font-size:0.7rem; color:var(--emerald-400); font-weight:700; letter-spacing:2px; }
</style>
"""

def get_report_css():
    """Report/diagnosis page specific styles"""
    return """
<style>
.page-header {
    background:var(--glass-white); backdrop-filter:blur(20px);
    border:1px solid var(--glass-border); border-radius:var(--radius-xl);
    padding:28px 32px; margin-bottom:28px;
    box-shadow:var(--shadow-soft); animation:fadeInUp 0.6s ease-out both;
    display:flex; align-items:center; gap:20px;
}
.page-header-icon {
    width:64px; height:64px; border-radius:20px; display:flex; align-items:center;
    justify-content:center; font-size:2rem;
    background:linear-gradient(135deg, var(--emerald-100), var(--emerald-50));
    border:2px solid rgba(52,211,153,0.3); flex-shrink:0;
    box-shadow:0 8px 24px rgba(16,185,129,0.15);
}

.report-wrapper {
    background:white; border-radius:var(--radius-xl);
    box-shadow:var(--shadow-card); overflow:hidden;
    animation:reportSlide 0.6s ease-out both;
    border:1px solid rgba(6,78,59,0.08);
}
.report-header { padding:28px 32px; position:relative; overflow:hidden; }
.report-header::before {
    content:""; position:absolute; top:0; right:0; width:200px; height:200px;
    border-radius:50%; background:radial-gradient(circle, rgba(255,255,255,0.15), transparent 70%);
    transform:translate(40%, -40%);
}
.report-scan-line {
    position:absolute; left:0; right:0; height:2px;
    background:linear-gradient(90deg, transparent, rgba(255,255,255,0.8), transparent);
    animation:scanLine 2s ease-in-out 0.5s;
}
.report-id { font-family:'Space Mono', monospace; font-size:0.68rem; color:rgba(255,255,255,0.7); letter-spacing:2px; text-transform:uppercase; margin-bottom:8px; }
.report-disease { font-size:1.8rem; font-weight:900; color:white; margin:0 0 4px; letter-spacing:-0.5px; }
.report-urdu { font-family:'Noto Nastaliq Urdu', serif; font-size:1.5rem; direction:rtl; color:rgba(255,255,255,0.9); line-height:2; }
.report-local { font-family:'Noto Nastaliq Urdu', serif; font-size:1rem; direction:rtl; color:rgba(255,255,255,0.75); }
.conf-bar-wrap { margin-top:16px; }
.conf-label { font-size:0.72rem; color:rgba(255,255,255,0.8); font-weight:600; text-transform:uppercase; letter-spacing:1px; margin-bottom:6px; }
.conf-bar-bg { background:rgba(255,255,255,0.2); border-radius:50px; height:10px; overflow:hidden; }
.conf-bar-fill { height:100%; border-radius:50px; background:rgba(255,255,255,0.9); transition:width 1.5s cubic-bezier(0.4,0,0.2,1); }
.conf-pct { font-size:2rem; font-weight:900; color:white; margin-top:8px; font-family:'Space Mono', monospace; }

.report-body { padding:24px 32px; }
.report-meta { display:grid; grid-template-columns:1fr 1fr 1fr; gap:14px; margin-bottom:24px; }
.report-meta-item { background:var(--emerald-50); border-radius:var(--radius-md); padding:14px 16px; border:1px solid rgba(52,211,153,0.15); }
.report-meta-label { font-size:0.65rem; color:var(--emerald-700); font-weight:700; text-transform:uppercase; letter-spacing:1.5px; }
.report-meta-val { font-size:0.92rem; font-weight:700; color:var(--emerald-900); margin-top:4px; }

.breakdown-section { margin-bottom:24px; }
.breakdown-title { font-size:0.75rem; font-weight:700; color:var(--emerald-800); text-transform:uppercase; letter-spacing:2px; margin-bottom:14px; display:flex; align-items:center; gap:8px; }
.breakdown-title::after { content:""; flex:1; height:1px; background:rgba(6,78,59,0.1); }
.breakdown-row { display:flex; align-items:center; gap:12px; margin-bottom:10px; }
.breakdown-lbl { font-size:0.82rem; font-weight:600; color:#374151; min-width:180px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.breakdown-track { flex:1; background:#f3f4f6; border-radius:50px; height:8px; overflow:hidden; }
.breakdown-fill { height:100%; border-radius:50px; transition:width 1.2s cubic-bezier(0.4,0,0.2,1); }
.breakdown-pct { font-family:'Space Mono', monospace; font-size:0.75rem; font-weight:700; color:#6b7280; min-width:42px; text-align:right; }

.treatment-section {
    background:linear-gradient(135deg, #f8fffe, #ecfdf5); border-radius:var(--radius-lg); padding:24px 28px;
    border:1.5px solid rgba(52,211,153,0.25); box-shadow:0 4px 20px rgba(16,185,129,0.08);
}
.treatment-section.danger { background:linear-gradient(135deg, #fff8f8, #fef2f2); border-color:rgba(220,38,38,0.2); box-shadow:0 4px 20px rgba(220,38,38,0.06); }
.treatment-section.warning { background:linear-gradient(135deg, #fffbf0, #fef3c7); border-color:rgba(245,158,11,0.2); box-shadow:0 4px 20px rgba(245,158,11,0.06); }
.treatment-title { font-size:1.05rem; font-weight:800; margin-bottom:16px; display:flex; align-items:center; gap:10px; }
.treatment-item { display:flex; gap:12px; align-items:flex-start; padding:12px 0; border-bottom:1px solid rgba(0,0,0,0.05); }
.treatment-item:last-child { border-bottom:none; padding-bottom:0; }
.treat-icon { width:32px; height:32px; border-radius:10px; display:flex; align-items:center; justify-content:center; font-size:0.95rem; flex-shrink:0; }
.treat-label { font-size:0.72rem; font-weight:700; text-transform:uppercase; letter-spacing:1px; opacity:0.6; margin-bottom:2px; }
.treat-val { font-size:0.88rem; font-weight:600; line-height:1.5; }

/* Inference time badge */
.infer-badge {
    display:inline-flex; align-items:center; gap:6px;
    background:var(--emerald-50); border:1px solid rgba(52,211,153,0.3);
    color:var(--emerald-800); padding:4px 12px; border-radius:50px;
    font-size:0.72rem; font-weight:700; font-family:'Space Mono', monospace;
    margin-top:8px;
}
</style>
"""

def get_badge_css():
    """Badge and misc component styles"""
    return """
<style>
.badge-live {
    display:inline-flex; align-items:center; gap:6px;
    background:linear-gradient(90deg, var(--emerald-600), var(--emerald-500));
    color:white; padding:5px 16px; border-radius:50px;
    font-size:0.78rem; font-weight:700; margin-top:12px;
    box-shadow:0 4px 14px rgba(16,185,129,0.35);
}
.badge-soon {
    display:inline-flex; align-items:center; gap:6px;
    background:linear-gradient(90deg, #f59e0b, #ef4444); background-size:200% auto;
    color:white; padding:5px 16px; border-radius:50px;
    font-size:0.78rem; font-weight:700; margin-top:12px;
    animation:shimmer 2s infinite linear;
}
.badge-dev {
    display:inline-flex; align-items:center; gap:6px;
    background:linear-gradient(90deg, #6366f1, #8b5cf6);
    color:white; padding:5px 16px; border-radius:50px;
    font-size:0.78rem; font-weight:700; margin-top:12px;
}
.weather-container {
    border-radius:var(--radius-xl); padding:24px; overflow:hidden;
    transition:transform 0.3s ease, box-shadow 0.3s ease; height:400px;
    display:flex; flex-direction:column; justify-content:space-between;
    position:relative;
}
.weather-container:hover { transform:translateY(-6px); box-shadow:0 30px 70px rgba(0,0,0,0.2); }
.weather-glow { position:absolute; top:-50%; left:-50%; width:200%; height:200%; background:radial-gradient(circle, rgba(255,255,255,0.18) 0%, transparent 60%); pointer-events:none; }
.weather-content { position:relative; z-index:2; display:flex; flex-direction:column; align-items:center; height:100%; }
.live-badge { background:rgba(0,0,0,0.25); padding:5px 14px; border-radius:50px; font-size:0.72rem; font-weight:700; letter-spacing:1.5px; display:flex; align-items:center; gap:7px; border:1px solid rgba(255,255,255,0.12); }
.live-dot { width:7px; height:7px; background:#ef4444; border-radius:50%; animation:pulseRed 1.5s infinite; }
.temp-big { font-size:4.8rem; font-weight:900; line-height:1; letter-spacing:-3px; background:linear-gradient(180deg,#fff 20%, rgba(255,255,255,0.55) 100%); -webkit-background-clip:text; -webkit-text-fill-color:transparent; filter:drop-shadow(0 4px 12px rgba(0,0,0,0.2)); margin:12px 0 4px; }
.weather-icon-3d { font-size:3.2rem; filter:drop-shadow(0 8px 16px rgba(0,0,0,0.25)); animation:floatY 5s ease-in-out infinite; }
.details-grid { display:grid; grid-template-columns:1fr 1fr; gap:10px; width:100%; margin-top:auto; }
.detail-item { background:rgba(255,255,255,0.14); border-radius:12px; padding:10px 8px; text-align:center; border:1px solid rgba(255,255,255,0.1); transition:background 0.2s; }
.detail-item:hover { background:rgba(255,255,255,0.22); }
.detail-label { font-size:0.65rem; color:rgba(255,255,255,0.75); text-transform:uppercase; letter-spacing:1px; }
.detail-val { font-size:1.05rem; font-weight:700; color:white; margin-top:3px; }
.tech-tag { display:inline-block; padding:5px 13px; border-radius:8px; font-size:0.82rem; font-weight:600; margin:3px; }
.coming-page { min-height:60vh; display:flex; flex-direction:column; align-items:center; justify-content:center; text-align:center; padding:60px 20px; animation:fadeInScale 0.8s ease-out both; }
.coming-pulse { font-size:5rem; margin-bottom:20px; animation:floatY 4s ease-in-out infinite; filter:drop-shadow(0 10px 20px rgba(0,0,0,0.1)); }

/* IMPROVEMENT #6: Persistent top header bar */
.top-header-bar {
    position: sticky; top: 0; z-index: 999;
    background: rgba(255,255,255,0.92); backdrop-filter: blur(20px);
    border-bottom: 1px solid rgba(6,78,59,0.1);
    padding: 10px 24px; margin: -1rem -1rem 1.5rem -1rem;
    display: flex; align-items: center; justify-content: space-between;
    box-shadow: 0 2px 20px rgba(6,78,59,0.08);
}
.top-header-brand { display:flex; align-items:center; gap:10px; }
.top-header-brand img { width:34px; height:34px; border-radius:50%; box-shadow:none; }
.top-header-brand-name { font-weight:900; color:#064e3b; font-size:1rem; line-height:1; }
.top-header-brand-sub { font-size:0.6rem; color:#6b7280; font-weight:600; letter-spacing:1.5px; text-transform:uppercase; }
.top-header-status {
    background:linear-gradient(90deg, #059669, #10b981); color:white;
    padding:5px 12px; border-radius:20px; font-size:0.7rem; font-weight:700;
    display:flex; align-items:center; gap:5px;
}
.status-dot { width:5px; height:5px; background:white; border-radius:50%; animation:pulseDot 2s infinite; }

/* IMPROVEMENT #7: Mobile responsive improvements */
@media (max-width: 768px) {
    .hero-title { font-size: 2.4rem !important; }
    .stat-grid  { grid-template-columns: repeat(2, 1fr); }
    .report-meta { grid-template-columns: 1fr 1fr; }
    .slider-container { height: 280px; }
    .weather-container { height: auto; min-height: 360px; }
    .breakdown-lbl { min-width: 130px; }
    .top-header-bar { margin: -1rem -1rem 1rem -1rem; padding: 8px 16px; }
    .hero-bg { padding: 32px 16px 28px; }
    .report-body { padding: 16px 20px; }
    .report-header { padding: 20px 24px; }
    .stButton > button { padding: 12px 16px !important; font-size: 0.9rem !important; }
}
</style>
"""

# Apply all CSS
st.markdown(get_critical_css(), unsafe_allow_html=True)
st.markdown(get_home_css(), unsafe_allow_html=True)
st.markdown(get_report_css(), unsafe_allow_html=True)
st.markdown(get_badge_css(), unsafe_allow_html=True)

# --- 9. PERSISTENT HEADER (IMPROVEMENT #6) ---
def render_persistent_header():
    st.markdown("""
    <div class="top-header-bar">
        <div class="top-header-brand">
            <img src="https://cdn-icons-png.flaticon.com/512/11698/11698467.png">
            <div>
                <div class="top-header-brand-name">Plant Doctor AI</div>
                <div class="top-header-brand-sub">v2.0 · Punjab Edition</div>
            </div>
        </div>
        <div class="top-header-status">
            <div class="status-dot"></div>
            ONLINE
        </div>
    </div>
    """, unsafe_allow_html=True)

# ===== SIDEBAR =====
st.sidebar.markdown("""
<div style="display:flex;justify-content:center;margin:10px 0 22px;">
    <img src="https://cdn-icons-png.flaticon.com/512/11698/11698467.png"
         style="width:120px;border-radius:50%;padding:10px;background:rgba(255,255,255,0.1);border:2px solid rgba(255,255,255,0.25);animation:floatLogo 3s ease-in-out infinite;">
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown("""
<h1 style='text-align:center;color:white;font-weight:900;margin-top:-6px;font-size:1.9rem;letter-spacing:-0.5px;'>Plant Doctor</h1>
<p style='text-align:center;font-size:0.72rem;opacity:0.7;margin-bottom:22px;letter-spacing:3px;font-weight:600;'>AI DIAGNOSTICS v2.0</p>
""", unsafe_allow_html=True)

st.sidebar.write("---")
nav = st.sidebar.radio("", ["🏠 Home Page", "🥔 Potato (Aloo)", "🍅 Tomato Check", "🫑 Pepper (Mirch)", "🌽 Corn Field"],
    index=["🏠 Home Page", "🥔 Potato (Aloo)", "🍅 Tomato Check", "🫑 Pepper (Mirch)", "🌽 Corn Field"].index(nav_default))

st.sidebar.write("---")

if temp > 30:  sw_color = "#f59e0b"; sw_icon = "☀️"
elif temp < 20: sw_color = "#6366f1"; sw_icon = "❄️"
else:           sw_color = "#10b981"; sw_icon = "⛅"
st.sidebar.markdown(f"""
<div style="background:rgba(255,255,255,0.07);border-radius:14px;padding:14px 16px;border:1px solid rgba(255,255,255,0.1);margin-bottom:16px;">
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:10px;">
        <span style="font-size:0.7rem;opacity:0.7;letter-spacing:1px;font-weight:600;text-transform:uppercase;">📍 Punjab Live</span>
        <div style="display:flex;align-items:center;gap:5px;"><div class="live-dot" style="width:6px;height:6px;background:#ef4444;border-radius:50%;animation:pulseRed 1.5s infinite;"></div><span style="font-size:0.65rem;opacity:0.7;font-weight:700;">LIVE</span></div>
    </div>
    <div style="display:flex;align-items:center;gap:10px;">
        <span style="font-size:2rem;">{sw_icon}</span>
        <div>
            <div style="font-size:1.6rem;font-weight:900;color:white;line-height:1;">{temp}°C</div>
            <div style="font-size:0.72rem;opacity:0.65;margin-top:2px;">💨 {wind} km/h wind</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

with st.sidebar.expander("📸 Tips for Best Results"):
    st.markdown("* ☀️ **Lighting:** Bright daylight\n* 🍃 **Focus:** Leaf only\n* 🖼️ **Background:** Plain\n* 📏 **Distance:** 20–30 cm")
st.sidebar.write("---")
st.sidebar.markdown("""
<div style="background:rgba(255,255,255,0.06);border-radius:12px;padding:14px 16px;border:1px solid rgba(255,255,255,0.08);">
    <p style="font-size:0.72rem;opacity:0.6;text-transform:uppercase;letter-spacing:1px;margin:0 0 10px;font-weight:700;">Developers</p>
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">
        <div style="width:32px;height:32px;border-radius:50%;background:linear-gradient(135deg,#10b981,#059669);display:flex;align-items:center;justify-content:center;font-size:0.8rem;font-weight:800;color:white;">SK</div>
        <div><div style="font-size:0.85rem;font-weight:700;color:white;">Saqlain Khan</div><div style="font-size:0.7rem;opacity:0.6;">Data Engineer</div></div>
    </div>
    <div style="display:flex;align-items:center;gap:10px;">
        <div style="width:32px;height:32px;border-radius:50%;background:linear-gradient(135deg,#6366f1,#8b5cf6);display:flex;align-items:center;justify-content:center;font-size:0.8rem;font-weight:800;color:white;">RC</div>
        <div><div style="font-size:0.85rem;font-weight:700;color:white;">Raheel Chishti</div><div style="font-size:0.7rem;opacity:0.6;">Team Member</div></div>
    </div>
</div>
""", unsafe_allow_html=True)


# ===== HELPER: RENDER DIAGNOSTIC REPORT =====
def render_report(label, conf, prob_dict, urdu_name, local_name, crop_name, timestamp_str, inference_time=None):
    is_healthy = "healthy" in label.lower()

    if is_healthy:
        hdr_bg = "linear-gradient(135deg, #059669, #10b981)"
        sev = "✅ Sehat Mand"; sev_color = "#059669"
    elif any(k in label.lower() for k in ["late blight", "virus", "mosaic", "curl"]):
        hdr_bg = "linear-gradient(135deg, #dc2626, #ef4444)"
        sev = "🔴 High Severity"; sev_color = "#dc2626"
    else:
        hdr_bg = "linear-gradient(135deg, #d97706, #f59e0b)"
        sev = "🟡 Moderate Severity"; sev_color = "#d97706"

    bar_color = "#059669" if is_healthy else ("#dc2626" if "high" in sev.lower() else "#d97706")

    # IMPROVEMENT #8: Show actual inference time instead of fake sleep
    infer_badge = ""
    if inference_time is not None:
        infer_badge = f'<div class="infer-badge">⚡ {inference_time:.2f}s inference time</div>'

    st.markdown(f"""
    <div class="report-wrapper">
        <div class="report-header" style="background:{hdr_bg};">
            <div class="report-scan-line"></div>
            <div class="report-id">🔬 DIAGNOSTIC REPORT · {timestamp_str} · {crop_name.upper()}</div>
            <div class="report-disease">{label}</div>
            <div class="report-urdu">{urdu_name}</div>
            <div class="report-local">🌾 مقامی نام: {local_name}</div>
            <div class="conf-bar-wrap">
                <div class="conf-label">Detection Confidence</div>
                <div class="conf-pct">{conf:.1f}%</div>
                <div class="conf-bar-bg"><div class="conf-bar-fill" style="width:{conf}%;background:rgba(255,255,255,0.9);"></div></div>
            </div>
            {infer_badge}
        </div>
        <div class="report-body">
            <div class="report-meta">
                <div class="report-meta-item">
                    <div class="report-meta-label">Crop / فصل</div>
                    <div class="report-meta-val">{crop_name}</div>
                </div>
                <div class="report-meta-item">
                    <div class="report-meta-label">Severity</div>
                    <div class="report-meta-val" style="color:{sev_color};">{sev}</div>
                </div>
                <div class="report-meta-item">
                    <div class="report-meta-label">Method</div>
                    <div class="report-meta-val">HOG+LBP+GLCM</div>
                </div>
            </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="breakdown-section"><div class="breakdown-title">📊 Probability Distribution</div>', unsafe_allow_html=True)
    sorted_probs = sorted(prob_dict.items(), key=lambda x: x[1], reverse=True)
    for i, (lbl, pct) in enumerate(sorted_probs):
        clean_lbl = lbl.replace('_', ' ').title()
        fill_color = bar_color if i == 0 else "#d1d5db"
        st.markdown(f"""
        <div class="breakdown-row">
            <div class="breakdown-lbl">{clean_lbl}</div>
            <div class="breakdown-track"><div class="breakdown-fill" style="width:{pct:.1f}%;background:{'linear-gradient(90deg,'+bar_color+','+bar_color+'aa)' if i==0 else '#d1d5db'};"></div></div>
            <div class="breakdown-pct">{pct:.1f}%</div>
        </div>
        """, unsafe_allow_html=True)
    st.markdown('</div></div>', unsafe_allow_html=True)

    return is_healthy, sev


def render_treatment(label, is_healthy, crop="potato"):
    if is_healthy:
        st.markdown("""
        <div class="treatment-section">
            <div class="treatment-title" style="color:#059669;">🎉 Mubarak Ho! | مبارک ہو — Fasal Sehat Mand Hai</div>
            <div class="treatment-item">
                <div class="treat-icon" style="background:#d1fae5;">💧</div>
                <div><div class="treat-label">Aabpashi / Irrigation</div><div class="treat-val">Regular pani dein — mitti dry na honay dein. Drip irrigation best hai.</div></div>
            </div>
            <div class="treatment-item">
                <div class="treat-icon" style="background:#d1fae5;">👁️</div>
                <div><div class="treat-label">Monitoring / Nigrani</div><div class="treat-val">Rozana subah pattay check karein. Koi daag diken to foran scan karein.</div></div>
            </div>
            <div class="treatment-item">
                <div class="treat-icon" style="background:#d1fae5;">🌿</div>
                <div><div class="treat-label">Prevention / Ehtiaat</div><div class="treat-val">Potassium-rich fertilizer use karein. Poudon ke darmiyan hawa aane dein.</div></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    elif crop == "potato" and "late" in label.lower():
        st.markdown("""
        <div class="treatment-section danger">
            <div class="treatment-title" style="color:#dc2626;">💊 Late Blight Ka Ilaj | پچھیتی جھلس کا علاج</div>
            <div class="treatment-item">
                <div class="treat-icon" style="background:#fee2e2;">🧪</div>
                <div><div class="treat-label">Chemical Spray / Kimiyai Spray</div><div class="treat-val">Metalaxyl + Mancozeb — 2.5g per Liter pani mein milaen. Subah ya sham spray karein.</div></div>
            </div>
            <div class="treatment-item">
                <div class="treat-icon" style="background:#fee2e2;">🔁</div>
                <div><div class="treat-label">Frequency / Waqfah</div><div class="treat-val">Har 7–10 din baad spray dohraen. Barish ke baad dobara zaroor karein.</div></div>
            </div>
            <div class="treatment-item">
                <div class="treat-icon" style="background:#fee2e2;">🌿</div>
                <div><div class="treat-label">Organic Option</div><div class="treat-val">Copper Fungicide (Bordeaux Mixture) bhi kaafi effective hai.</div></div>
            </div>
            <div class="treatment-item">
                <div class="treat-icon" style="background:#fee2e2;">⚠️</div>
                <div><div class="treat-label">Important / Zaroori</div><div class="treat-val">Mutasira (affected) pattay hata kar jala dein. Khet mein paani khari na honay dein.</div></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    elif crop == "potato" and "early" in label.lower():
        st.markdown("""
        <div class="treatment-section warning">
            <div class="treatment-title" style="color:#d97706;">💊 Early Blight Ka Ilaj | اگیتی جھلس کا علاج</div>
            <div class="treatment-item">
                <div class="treat-icon" style="background:#fef3c7;">🧪</div>
                <div><div class="treat-label">Fungicide Spray</div><div class="treat-val">Chlorothalonil ya Azoxystrobin — label ki hidayat ke mutabiq use karein.</div></div>
            </div>
            <div class="treatment-item">
                <div class="treat-icon" style="background:#fef3c7;">🌱</div>
                <div><div class="treat-label">Organic Option</div><div class="treat-val">Neem Oil (5ml per Liter) — 10–14 din ke waqfe par spray karein.</div></div>
            </div>
            <div class="treatment-item">
                <div class="treat-icon" style="background:#fef3c7;">✂️</div>
                <div><div class="treat-label">Field Management</div><div class="treat-val">Neeche ke purane, mutasira pattay kaat kar hatayein. Hawa ki rawani badhayein.</div></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    elif crop == "tomato" and ("virus" in label.lower() or "mosaic" in label.lower() or "curl" in label.lower()):
        st.markdown("""
        <div class="treatment-section danger">
            <div class="treatment-title" style="color:#dc2626;">⚠️ Viral Disease Alert | وائرس بیماری</div>
            <div class="treatment-item">
                <div class="treat-icon" style="background:#fee2e2;">🚨</div>
                <div><div class="treat-label">Emergency Action / Faori Qadam</div><div class="treat-val">Mutasira poudon ko fauran ukhad kar jala dein. Virus spread rokna zaroori hai.</div></div>
            </div>
            <div class="treatment-item">
                <div class="treat-icon" style="background:#fee2e2;">🦟</div>
                <div><div class="treat-label">Vector Control</div><div class="treat-val">Safaid Makhi (Whitefly) se phailta hai — Imidacloprid ya Yellow Sticky Traps use karein.</div></div>
            </div>
            <div class="treatment-item">
                <div class="treat-icon" style="background:#fee2e2;">🛡️</div>
                <div><div class="treat-label">Prevention Next Season</div><div class="treat-val">Virus-resistant varieties lagaen. Neem oil spray preventive ke tor par karein.</div></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    elif crop == "pepper" and "bacterial" in label.lower():
        st.markdown("""
        <div class="treatment-section warning">
            <div class="treatment-title" style="color:#d97706;">💊 Bacterial Spot Ka Ilaj | بیکٹیریل دھبوں کا علاج</div>
            <div class="treatment-item">
                <div class="treat-icon" style="background:#fef3c7;">🧪</div>
                <div><div class="treat-label">Copper Spray</div><div class="treat-val">Copper-based bactericide (Copper Hydroxide) — 3g per Liter pani mein milaen. Har 7 din baad spray karein.</div></div>
            </div>
            <div class="treatment-item">
                <div class="treat-icon" style="background:#fef3c7;">✂️</div>
                <div><div class="treat-label">Pruning</div><div class="treat-val">Mutasira pattay aur tehniyan kaat dein. Kaat ke baad auzon ko disinfect zaroor karein.</div></div>
            </div>
            <div class="treatment-item">
                <div class="treat-icon" style="background:#fef3c7;">💧</div>
                <div><div class="treat-label">Irrigation</div><div class="treat-val">Upar se pani dena band karein — sirf jaron mein pani dein. Pattay gelay na hon.</div></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    elif crop == "corn" and "rust" in label.lower():
        st.markdown("""
        <div class="treatment-section warning">
            <div class="treatment-title" style="color:#d97706;">💊 Common Rust Ka Ilaj | کنگی روگ کا علاج</div>
            <div class="treatment-item">
                <div class="treat-icon" style="background:#fef3c7;">🧪</div>
                <div><div class="treat-label">Fungicide Spray</div><div class="treat-val">Pyraclostrobin ya Azoxystrobin — jab bimari shuru ho foran spray karein.</div></div>
            </div>
            <div class="treatment-item">
                <div class="treat-icon" style="background:#fef3c7;">🛡️</div>
                <div><div class="treat-label">Prevention</div><div class="treat-val">Agle saal kungi ke khilaf resistant beej istemal karein.</div></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    elif crop == "corn" and "blight" in label.lower():
        st.markdown("""
        <div class="treatment-section danger">
            <div class="treatment-title" style="color:#dc2626;">💊 Blight Ka Ilaj | جھلس روگ کا علاج</div>
            <div class="treatment-item">
                <div class="treat-icon" style="background:#fee2e2;">🧪</div>
                <div><div class="treat-label">Fungicide Spray</div><div class="treat-val">Mancozeb ya Chlorothalonil ka fori spray karein. 10 din ke waqfe par dohraen.</div></div>
            </div>
            <div class="treatment-item">
                <div class="treat-icon" style="background:#fee2e2;">🔄</div>
                <div><div class="treat-label">Crop Rotation</div><div class="treat-val">Fasal ki katai ke baad baqiyat zameen mein daba dein. Agli baar alag jagah lagaen.</div></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    elif crop == "corn" and "gray" in label.lower():
        st.markdown("""
        <div class="treatment-section warning">
            <div class="treatment-title" style="color:#d97706;">💊 Gray Leaf Spot Ka Ilaj | سرمئی دھبوں کا علاج</div>
            <div class="treatment-item">
                <div class="treat-icon" style="background:#fef3c7;">🧪</div>
                <div><div class="treat-label">Fungicide</div><div class="treat-val">Strobilurin-based fungicide use karein. Early season mein spray zyada effective hoti hai.</div></div>
            </div>
            <div class="treatment-item">
                <div class="treat-icon" style="background:#fef3c7;">🌬️</div>
                <div><div class="treat-label">Air Circulation</div><div class="treat-val">Poudon ke darmiyan fasla rakhein. Bheed hone se nami zyada hoti hai jo is bimari ko badhati hai.</div></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    else:
        st.markdown("""
        <div class="treatment-section warning">
            <div class="treatment-title" style="color:#d97706;">💊 Fungal / Bacterial Treatment | پھپھوندی علاج</div>
            <div class="treatment-item">
                <div class="treat-icon" style="background:#fef3c7;">🧪</div>
                <div><div class="treat-label">Fungicide / Spray</div><div class="treat-val">Copper Fungicide ya Neem Oil (5ml/L) — 10 din ke waqfe par spray karein.</div></div>
            </div>
            <div class="treatment-item">
                <div class="treat-icon" style="background:#fef3c7;">💧</div>
                <div><div class="treat-label">Irrigation / Aabpashi</div><div class="treat-val">Sirf jaron (roots) mein pani dein. Pattay bilkul gelay na karein.</div></div>
            </div>
            <div class="treatment-item">
                <div class="treat-icon" style="background:#fef3c7;">🌱</div>
                <div><div class="treat-label">Spacing / Fasla</div><div class="treat-val">Poudon ke darmiyan fasla rakhein taake hawa aata rahe. Bheed na ho.</div></div>
            </div>
        </div>
        """, unsafe_allow_html=True)


# ===== IMPROVEMENT #9: GENERIC CROP PAGE FUNCTION (eliminates duplicate Potato/Tomato code) =====
# --- UNIFIED ANALYSIS PIPELINE (v4: single source of truth, no duplication) ---
def analyze_image(uploaded_file, crop_key):
    """
    Single function used by BOTH render_crop_page() and render_universal_upload().
    Fixes the v3 DRY violation — one bug fix here fixes everywhere.
    Returns a result dict, or None on failure.
    """
    model, crop_scaler, crop_class_names = MODELS.get(crop_key, (None, None, None))
    if not model:
        st.error(CROP_CONFIG[crop_key]['model_missing_msg'])
        return None

    start_time = time.time()
    features = extract_all_features(uploaded_file.getvalue())
    if features is None:
        return None

    features = np.nan_to_num(features).reshape(1, -1)
    features_scaled = crop_scaler.transform(features)
    probs = model.predict_proba(features_scaled)[0]
    inference_time = time.time() - start_time

    max_idx = np.argmax(probs)
    conf = probs[max_idx] * 100
    label = crop_class_names[max_idx].replace("_", " ").title()

    return {
        'conf': conf,
        'label': label,
        'prob_dict': {l: p * 100 for l, p in zip(crop_class_names, probs)},
        'inference_time': inference_time,
    }


def show_low_confidence_warning():
    st.markdown("""
    <div style="background:#fef2f2;border:1.5px solid #dc2626;border-radius:16px;padding:24px;text-align:center;">
        <div style="font-size:2rem;margin-bottom:8px;">⚠️</div>
        <h3 style="color:#dc2626;font-weight:800;margin:0 0 8px;">Photo Clear Nahi Hai!</h3>
        <p style="color:#6b7280;font-size:0.9rem;">Confidence bohat kam hai. Ye is fasal ka patta nahi lagta ya photo blur hai. Saaf aur roshan jagah mein dobara try karein.</p>
    </div>
    """, unsafe_allow_html=True)


def show_result(result, crop_key, config):
    """Render report + treatment from a result dict. Used by both pages."""
    if result['conf'] < 50:
        show_low_confidence_warning()
        return
    ts = datetime.datetime.now().strftime("%d %b %Y · %H:%M")
    urdu_name = config['urdu_names'].get(result['label'], result['label'])
    local_name = config['local_names'].get(result['label'], result['label'])
    is_healthy, _ = render_report(
        result['label'], result['conf'], result['prob_dict'],
        urdu_name, local_name, config['display_name'], ts, result['inference_time']
    )
    st.markdown("<br>", unsafe_allow_html=True)
    if is_healthy:
        st.balloons()
    render_treatment(result['label'], is_healthy, crop=crop_key)


def render_crop_page(crop_key):
    """Crop-specific scan page — uses unified analyze_image()."""
    config = CROP_CONFIG[crop_key]
    model = MODELS[crop_key][0]

    render_persistent_header()

    st.markdown(f"""
    <div class="page-header">
        <div class="page-header-icon">{config['emoji']}</div>
        <div>
            <h2 style="color:#064e3b;font-weight:900;margin:0 0 4px;font-size:1.6rem;">{config['header_title']}</h2>
            <p style="color:#6b7280;margin:0;font-size:0.88rem;">{config['header_sub']}</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if not model:
        st.error(config['model_missing_msg'])
        st.stop()

    # --- Batch upload (v4: accept_multiple_files) ---
    uploaded_files = st.file_uploader(
        config['uploader_label'],
        type=["jpg", "png", "jpeg", "webp", "jfif"],
        accept_multiple_files=True
    )

    if not uploaded_files:
        return

    # Single file — full detailed report
    if len(uploaded_files) == 1:
        uploaded_file = uploaded_files[0]
        col1, col2 = st.columns([1, 1.6])
        with col1:
            pil_img = Image.open(uploaded_file).convert('RGB')
            st.image(pil_img, caption="📷 Uploaded Leaf Photo", use_column_width=True)
            w, h = pil_img.size
            st.markdown(f"""
            <div style="background:var(--emerald-50);border-radius:12px;padding:14px 16px;border:1px solid rgba(52,211,153,0.2);margin-top:12px;">
                <div style="font-size:0.65rem;color:var(--emerald-700);font-weight:700;text-transform:uppercase;letter-spacing:1px;margin-bottom:8px;">Image Info</div>
                <div style="display:flex;gap:16px;flex-wrap:wrap;">
                    <div><span style="font-size:0.75rem;color:#6b7280;">Size:</span> <span style="font-size:0.8rem;font-weight:700;color:#064e3b;">{w}×{h}px</span></div>
                    <div><span style="font-size:0.75rem;color:#6b7280;">File:</span> <span style="font-size:0.8rem;font-weight:700;color:#064e3b;">{uploaded_file.name}</span></div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            with st.spinner("🔬 Extracting features & running diagnostics..."):
                result = analyze_image(uploaded_file, crop_key)
        if result:
            show_result(result, crop_key, config)

    # Multiple files — compact batch results table
    else:
        st.markdown(f"""
        <div style="background:var(--emerald-50);border-radius:14px;padding:14px 18px;border:1px solid rgba(52,211,153,0.2);margin-bottom:18px;">
            <span style="font-weight:700;color:#064e3b;">📦 Batch Mode:</span>
            <span style="color:#6b7280;font-size:0.9rem;"> {len(uploaded_files)} pattay upload hue — ek ek scan ho raha hai</span>
        </div>
        """, unsafe_allow_html=True)

        progress_bar = st.progress(0, text="Scanning leaves...")
        for i, uploaded_file in enumerate(uploaded_files):
            with st.container():
                col_img, col_res = st.columns([1, 3])
                with col_img:
                    st.image(uploaded_file, width=120)
                with col_res:
                    result = analyze_image(uploaded_file, crop_key)
                    if result:
                        conf = result['conf']
                        label = result['label']
                        is_healthy = "healthy" in label.lower()
                        if conf < 60:
                            st.warning(f"**{uploaded_file.name}** — ⚠️ Low confidence ({conf:.0f}%)")
                        else:
                            color = "#059669" if is_healthy else ("#dc2626" if any(k in label.lower() for k in ["late","virus","mosaic","curl"]) else "#d97706")
                            st.markdown(f"""
                            <div style="padding:12px 16px;background:white;border-radius:12px;border-left:4px solid {color};box-shadow:0 2px 8px rgba(0,0,0,0.06);margin-bottom:4px;">
                                <div style="font-weight:800;color:{color};font-size:1rem;">{label}</div>
                                <div style="font-size:0.78rem;color:#6b7280;margin-top:2px;">
                                    Confidence: <b>{conf:.1f}%</b> &nbsp;·&nbsp; ⚡ {result['inference_time']:.2f}s
                                    &nbsp;·&nbsp; {uploaded_file.name}
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
            progress_bar.progress((i + 1) / len(uploaded_files), text=f"Scanning {i+1}/{len(uploaded_files)}...")
        progress_bar.empty()
        st.success(f"✅ Batch complete! {len(uploaded_files)} pattay scan ho gaye.")


# ===================== HOME PAGE =====================
if nav == "🏠 Home Page":
    render_persistent_header()

    st.markdown("""
    <div class="hero-wrapper">
        <div class="hero-bg">
            <div class="hero-orb orb-1"></div>
            <div class="hero-orb orb-2"></div>
            <div class="hero-badge">🌿 AI-Powered Agriculture</div>
            <h1 class="hero-title">Plant Doctor AI</h1>
            <p class="hero-sub">Apni Fasal Ki Bimari Seconds Mein Pehchanein</p>
            <p class="hero-desc">Pattay ki photo upload karein — AI fauran bimari detect karke ilaj batayega. Punjab ke kisan ke liye, Urdu mein.</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="stat-grid">
        <div class="stat-card" style="animation-delay:0.1s"><div class="stat-val">95%</div><div class="stat-lbl">Accuracy</div></div>
        <div class="stat-card" style="animation-delay:0.2s"><div class="stat-val">24K+</div><div class="stat-lbl">Images Trained</div></div>
        <div class="stat-card" style="animation-delay:0.3s"><div class="stat-val">4</div><div class="stat-lbl">Crops</div></div>
        <div class="stat-card" style="animation-delay:0.4s"><div class="stat-val">&lt;3s</div><div class="stat-lbl">Result Time</div></div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown("""
        <div class="slider-container">
            <div class="slide-track">
                <div class="slide"><img src="https://images.unsplash.com/photo-1625246333195-78d9c38ad449?w=800"></div>
                <div class="slide"><img src="https://images.unsplash.com/photo-1586771107445-d3ca888129ff?w=800"></div>
                <div class="slide"><img src="https://images.unsplash.com/photo-1530836369250-ef72a3f5cda8?w=800"></div>
                <div class="slide"><img src="https://images.unsplash.com/photo-1587334274328-64186a80aeee?w=800"></div>
                <div class="slide"><img src="https://images.unsplash.com/photo-1551754655-cd27e38d2076?w=800"></div>
                <div class="slide"><img src="https://images.unsplash.com/photo-1464226184884-fa280b87c399?w=800"></div>
                <div class="slide"><img src="https://images.unsplash.com/photo-1500382017468-9049fed747ef?w=800"></div>
                <div class="slide"><img src="https://images.unsplash.com/photo-1416879595882-3373a0480b5b?w=800"></div>
                <div class="slide"><img src="https://images.unsplash.com/photo-1592087046781-3070b59e4c14?w=800"></div>
                <div class="slide"><img src="https://images.unsplash.com/photo-1625246333195-78d9c38ad449?w=800"></div>
                <div class="slide"><img src="https://images.unsplash.com/photo-1586771107445-d3ca888129ff?w=800"></div>
                <div class="slide"><img src="https://images.unsplash.com/photo-1530836369250-ef72a3f5cda8?w=800"></div>
            </div>
        </div>
        <p style="text-align:center;font-size:0.78rem;color:#aaa;margin-top:8px;font-style:italic;">🖱️ Hover to pause the gallery</p>
        """, unsafe_allow_html=True)

    with col2:
        if temp > 30:
            card_bg = "linear-gradient(145deg, #ea580c, #f59e0b)"; weather_icon = "☀️"; condition = "Sunny / Dhoop"
        elif temp < 20:
            card_bg = "linear-gradient(145deg, #3b82f6, #6366f1)"; weather_icon = "❄️"; condition = "Chilly / Thanda"
        else:
            card_bg = "linear-gradient(145deg, #059669, #10b981)"; weather_icon = "⛅"; condition = "Pleasant / Khushgawar"

        st.markdown(f"""
        <div class="weather-container" style="background:{card_bg};">
            <div class="weather-glow"></div>
            <div class="weather-content">
                <div style="width:100%;display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
                    <div class="live-badge"><div class="live-dot"></div> LIVE</div>
                    <div style="font-weight:600;font-size:0.82rem;color:rgba(255,255,255,0.85);">📍 Punjab, PK</div>
                </div>
                <div class="weather-icon-3d">{weather_icon}</div>
                <div class="temp-big">{temp}°C</div>
                <div style="font-size:1rem;font-weight:700;color:rgba(255,255,255,0.95);margin-bottom:3px;">{condition}</div>
                <div style="font-size:0.75rem;color:rgba(255,255,255,0.65);margin-bottom:12px;">Fasal ke liye mausam ki report</div>
                <div class="details-grid">
                    <div class="detail-item"><div class="detail-label">Wind / Hawa</div><div class="detail-val">{wind} km/h</div></div>
                    <div class="detail-item"><div class="detail-label">Humidity / Nam</div><div class="detail-val">{humidity}%</div></div>
                    <div class="detail-item"><div class="detail-label">Spray Safe?</div><div class="detail-val">{"❌ Na Karein" if wind > 20 else "✅ Theek Hai"}</div></div>
                    <div class="detail-item"><div class="detail-label">Bimari Risk</div><div class="detail-val">{"🔴 Zyada" if temp > 28 else "🟢 Kam"}</div></div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Universal upload zone — AI auto-detects crop
    uploaded_file, detected_crop = render_universal_upload()
    if uploaded_file and detected_crop:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(f"<h3 style='color:#064e3b;font-weight:800;'>📊 {detected_crop.title()} Analysis Result</h3>", unsafe_allow_html=True)
        with st.spinner("🔬 Analyzing..."):
            result = analyze_image(uploaded_file, detected_crop)
        if result:
            show_result(result, detected_crop, CROP_CONFIG[detected_crop])

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<h2 style='text-align:center;color:#064e3b;font-weight:900;font-size:2rem;margin-bottom:6px;'>Supported Crops | Faslain</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center;color:#6b7280;font-size:0.9rem;margin-bottom:24px;'>Apni fasal chunein — AI fauran diagnose karega</p>", unsafe_allow_html=True)

    cc1, cc2 = st.columns(2)
    with cc1:
        st.markdown("""
        <div class="crop-card" style="animation-delay:0.1s;">
            <div class="crop-emoji">🥔</div>
            <h3 style="color:#064e3b;font-weight:800;margin:0 0 4px;font-size:1.3rem;">Potato — آلو</h3>
            <p style="color:#6b7280;font-size:0.85rem;margin:0 0 6px;">3 Diseases Detected</p>
            <p style="color:#9ca3af;font-size:0.78rem;margin:0 0 12px;line-height:1.5;">Early Blight · Late Blight · Healthy</p>
            <span class="badge-live">✅ Live &nbsp;|&nbsp; 97% Accuracy</span>
        </div>
        """, unsafe_allow_html=True)
        if st.button("🥔 Potato Scan Karein →", use_container_width=True, type="primary", key="btn_potato"):
            st.session_state['nav_override'] = "🥔 Potato (Aloo)"
            st.rerun()

    with cc2:
        st.markdown("""
        <div class="crop-card" style="animation-delay:0.2s;">
            <div class="crop-emoji">🍅</div>
            <h3 style="color:#064e3b;font-weight:800;margin:0 0 4px;font-size:1.3rem;">Tomato — ٹماٹر</h3>
            <p style="color:#6b7280;font-size:0.85rem;margin:0 0 6px;">9 Diseases Detected</p>
            <p style="color:#9ca3af;font-size:0.78rem;margin:0 0 12px;line-height:1.5;">Blight · Virus · Mold · Bacterial Spot & more</p>
            <span class="badge-live">✅ Live &nbsp;|&nbsp; 95% Accuracy</span>
        </div>
        """, unsafe_allow_html=True)
        if st.button("🍅 Tomato Scan Karein →", use_container_width=True, type="primary", key="btn_tomato"):
            st.session_state['nav_override'] = "🍅 Tomato Check"
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    cc3, cc4 = st.columns(2)
    with cc3:
        st.markdown("""
        <div class="crop-card" style="animation-delay:0.3s;">
            <div class="crop-emoji">🫑</div>
            <h3 style="color:#064e3b;font-weight:800;margin:0 0 4px;font-size:1.3rem;">Pepper — مرچ</h3>
            <p style="color:#6b7280;font-size:0.85rem;margin:0 0 6px;">2 Diseases Detected</p>
            <p style="color:#9ca3af;font-size:0.78rem;margin:0 0 12px;line-height:1.5;">Bacterial Spot · Healthy</p>
            <span class="badge-live">✅ Live &nbsp;|&nbsp; 99% Accuracy</span>
        </div>
        """, unsafe_allow_html=True)
        if st.button("🫑 Pepper Scan Karein →", use_container_width=True, type="primary", key="btn_pepper"):
            st.session_state['nav_override'] = "🫑 Pepper (Mirch)"
            st.rerun()

    with cc4:
        st.markdown("""
        <div class="crop-card" style="animation-delay:0.4s;">
            <div class="crop-emoji">🌽</div>
            <h3 style="color:#064e3b;font-weight:800;margin:0 0 4px;font-size:1.3rem;">Corn — مکئی</h3>
            <p style="color:#6b7280;font-size:0.85rem;margin:0 0 6px;">4 Diseases Detected</p>
            <p style="color:#9ca3af;font-size:0.78rem;margin:0 0 12px;line-height:1.5;">Blight · Common Rust · Gray Leaf Spot · Healthy</p>
            <span class="badge-live">✅ Live &nbsp;|&nbsp; 87% Accuracy</span>
        </div>
        """, unsafe_allow_html=True)
        if st.button("🌽 Corn Scan Karein →", use_container_width=True, type="primary", key="btn_corn"):
            st.session_state['nav_override'] = "🌽 Corn Field"
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown("<h2 style='text-align:center;color:#064e3b;font-weight:900;font-size:2rem;margin-bottom:6px;'>How It Works | Kaise Kaam Karta Hai</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center;color:#6b7280;font-size:0.9rem;margin-bottom:28px;'>Teen aasan qadam — aur result haazir</p>", unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    steps = [
        ("📸", "01", "Photo Upload Karein", "Pattay ki saaf tasveer lein aur upload karein. Roshan jagah mein photo lein, background sada hona chahiye."),
        ("🤖", "02", "AI Analysis", "Random Forest model HOG, LBP, GLCM aur Color features extract karke bimari identify karta hai."),
        ("💊", "03", "Ilaj Payein", "Fauran result + Urdu mein mukammal ilaj ki hidayat. Spray schedule bhi bataya jayega.")
    ]
    for col, (icon, num, title, desc) in zip([c1, c2, c3], steps):
        with col:
            st.markdown(f"""
            <div class="hiw-card">
                <span class="hiw-step">STEP {num}</span>
                <div class="hiw-icon-wrap">{icon}</div>
                <h3 style="color:#064e3b;font-weight:800;margin:0 0 10px;font-size:1.05rem;">{title}</h3>
                <p style="color:#6b7280;font-size:0.87rem;line-height:1.7;margin:0;">{desc}</p>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("""
    <hr style="border:none;border-top:1px solid rgba(6,78,59,0.12);margin:60px 0 30px;">
    <div style="text-align:center;padding-bottom:40px;">
        <p style="font-weight:800;font-size:1rem;color:#064e3b;margin-bottom:4px;">© 2026 Plant Doctor AI — All Rights Reserved</p>
        <p style="font-size:0.85rem;color:#9ca3af;margin-bottom:12px;">Built with ❤️ for Pakistani farmers | پاکستانی کسانوں کے لیے</p>
        <div style="margin-top:10px;">
            <span class="tech-tag" style="background:#fce7f3;color:#be185d;">🎈 Streamlit</span>
            <span class="tech-tag" style="background:#e0e7ff;color:#4338ca;">🤖 Scikit-Learn</span>
            <span class="tech-tag" style="background:#fef3c7;color:#b45309;">🌲 Random Forest</span>
            <span class="tech-tag" style="background:#d1fae5;color:#065f46;">👁️ OpenCV</span>
            <span class="tech-tag" style="background:#ede9fe;color:#5b21b6;">🖼️ Scikit-Image</span>
        </div>
        <p style="font-size:0.75rem;margin-top:14px;color:#cbd5e1;">Developed by <b>Saqlain Khan</b> (Data Engineer) & <b>Raheel Chishti</b></p>
    </div>
    """, unsafe_allow_html=True)


# ===================== POTATO — now uses generic function =====================
elif nav == "🥔 Potato (Aloo)":
    render_crop_page("potato")


# ===================== TOMATO — now uses generic function =====================
elif nav == "🍅 Tomato Check":
    render_crop_page("tomato")


# ===================== PEPPER — uses generic function =====================
elif nav == "🫑 Pepper (Mirch)":
    render_crop_page("pepper")


# ===================== CORN — uses generic function =====================
elif nav == "🌽 Corn Field":
    render_crop_page("corn") 
 