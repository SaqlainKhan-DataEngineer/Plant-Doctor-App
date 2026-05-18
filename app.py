import streamlit as st 
import google.generativeai as genai
# Code se hardcoded key hata dein, aur Streamlit secrets use karein
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
import xgboost as xgb
genai.configure(api_key=GEMINI_API_KEY)
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

# ==============================================================================
# 🔥 AUTHENTICATION CODE (NEW ADDITION)
# ==============================================================================
# Use cloud backend for production (Railway)
API_URL = "https://plant-doctor-app-production.up.railway.app/api"
# API_URL = "http://localhost:8000/api" # Use this for local testing

# ==============================================================================
# 🔥 FIX #1: REFRESH PE LOGOUT NA HO - URL QUERY PARAMS SE TOKEN PERSIST KARO
# ==============================================================================
def persist_auth_token():
    """Token ko URL query params mein save karo taake refresh pe na jaye"""
    if st.session_state.token:
        st.query_params["token"] = st.session_state.token
        st.query_params["user"] = st.session_state.user or "farmer"
        st.query_params["email"] = st.session_state.user_email or ""

def restore_auth_from_url():
    """URL se token wapas lao agar session empty ho"""
    params = st.query_params
    if not st.session_state.get("token") and params.get("token"):
        st.session_state.token = params.get("token")
        st.session_state.user = params.get("user", "farmer")
        st.session_state.user_email = params.get("email", "")

# Pehle restore karo
restore_auth_from_url()

# Session state for auth (init with restored values if any)
if 'token' not in st.session_state:
    st.session_state.token = None
if 'user' not in st.session_state:
    st.session_state.user = None
if 'user_email' not in st.session_state:
    st.session_state.user_email = None

# Token ko URL mein sync karo
persist_auth_token()

def render_auth_page():
    """Login/Register page - user auth ke bina app nahi khulega"""
    st.markdown("""
    <style>
    .auth-container {
        max-width: 400px;
        margin: 0 auto;
        padding: 40px 20px;
    }
    .auth-title {
        text-align: center;
        color: #064e3b;
        font-size: 2rem;
        font-weight: 900;
        margin-bottom: 10px;
    }
    .auth-subtitle {
        text-align: center;
        color: #6b7280;
        font-size: 0.9rem;
        margin-bottom: 30px;
    }
    </style>
    <div class="auth-container">
        <div style="text-align:center;font-size:4rem;margin-bottom:10px;">🌿</div>
        <h1 class="auth-title">Plant Doctor AI</h1>
        <p class="auth-subtitle">Pakistani Kisanon Ka AI Doctor<br>Login karein ya naya account banayein</p>
    </div>
    """, unsafe_allow_html=True)
    
    # --------------------------------------------------------------------------
    # RESET PASSWORD FLOW (URL mein reset_token ho)
    # --------------------------------------------------------------------------
    if "reset_token" in st.query_params:
        st.subheader("🔑 Reset Password")
        reset_token = st.query_params.get("reset_token")
        with st.form("reset_password_form"):
            new_pass = st.text_input("New Password", type="password")
            confirm_pass = st.text_input("Confirm New Password", type="password")
            submitted = st.form_submit_button("Reset Password", type="primary", use_container_width=True)
            
            if submitted:
                if len(new_pass) < 6:
                    st.error("⚠️ Password kam az kam 6 characters ka hona chahiye!")
                elif new_pass != confirm_pass:
                    st.error("❌ Passwords match nahi kar rahe!")
                else:
                    try:
                        resp = requests.post(
                            f"{API_URL}/auth/reset-password",
                            json={"token": reset_token, "new_password": new_pass},
                            timeout=10
                        )
                        if resp.status_code == 200:
                            st.success("✅ Password successfully reset ho gaya hai! Ab aap login kar sakte hain.")
                            # Remove token from URL so they can login
                            st.query_params.clear()
                            time.sleep(2)
                            st.rerun()
                        else:
                            st.error(f"❌ Error: {resp.json().get('detail', 'Invalid token')}")
                    except Exception as e:
                        st.error(f"❌ API Error: {str(e)}")
                        
        if st.button("⬅️ Back to Login"):
            st.query_params.clear()
            st.rerun()
        return

    # --------------------------------------------------------------------------
    # FORGOT PASSWORD FLOW (Button click se)
    # --------------------------------------------------------------------------
    if st.session_state.get("show_forgot_password"):
        st.subheader("📧 Forgot Password")
        st.info("Apna email daalein, hum aapko password reset karne ka link bhejenge.")
        with st.form("forgot_password_form"):
            forgot_email = st.text_input("Registered Email")
            submitted = st.form_submit_button("Send Reset Link", type="primary", use_container_width=True)
            
            if submitted:
                if not forgot_email:
                    st.error("⚠️ Email zaroori hai!")
                else:
                    try:
                        resp = requests.post(
                            f"{API_URL}/auth/forgot-password",
                            json={"email": forgot_email},
                            timeout=10
                        )
                        if resp.status_code == 200:
                            st.success("✅ " + resp.json().get("message", "Link sent!"))
                        else:
                            st.error(f"❌ Error: {resp.json().get('detail', 'Failed')}")
                    except Exception as e:
                        st.error(f"❌ API Error: {str(e)}")
                        
        if st.button("⬅️ Back to Login"):
            st.session_state.show_forgot_password = False
            st.rerun()
        return

    # --------------------------------------------------------------------------
    # STANDARD LOGIN / REGISTER
    # --------------------------------------------------------------------------
    tab1, tab2 = st.tabs(["🔑 Login", "📝 Register"])
    
    with tab1:
        st.markdown("<br>", unsafe_allow_html=True)
    with tab1:
        st.markdown("<br>", unsafe_allow_html=True)
        with st.form("login_form"):
            email = st.text_input("📧 Email")
            password = st.text_input("🔒 Password", type="password")
            
            submitted = st.form_submit_button("🔓 Login", type="primary", use_container_width=True)
            if submitted:
                if not email or not password:
                    st.error("⚠️ Email aur password dono daalein!")
                else:
                    try:
                        response = requests.post(
                            f"{API_URL}/auth/login", 
                            json={"email": email, "password": password},
                            timeout=5
                        )
                        
                        if response.status_code == 200:
                            data = response.json()
                            st.session_state.token = data['token']
                            st.session_state.user = data['role']
                            st.session_state.user_email = email 
                            persist_auth_token()  # 🔥 URL mein save karo
                            st.success("✅ Login successful!")
                            time.sleep(0.5)
                            st.rerun()
                        elif response.status_code == 401:
                            st.error("❌ Galat email ya password!")
                        else:
                            st.error(f"❌ Error: {response.json().get('detail', 'Unknown error')}")
                    except requests.exceptions.ConnectionError:
                        st.error("❌ Backend server nahi chal raha! Terminal mein `uvicorn main:app --reload --port 8000` run karein.")
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
                        
        if st.button("Forgot Password?", type="tertiary"):
            st.session_state.show_forgot_password = True
            st.rerun()
    
    with tab2:
        st.markdown("<br>", unsafe_allow_html=True)
        with st.form("register_form"):
            name = st.text_input("👤 Full Name")
            email = st.text_input("📧 Email")
            phone = st.text_input("📱 Phone (optional)")
            password = st.text_input("🔒 Password", type="password")
            confirm_password = st.text_input("🔒 Confirm Password", type="password")
            
            submitted = st.form_submit_button("📝 Register", type="primary", use_container_width=True)
            if submitted:
                if not name or not email or not password:
                    st.error("⚠️ Name, email aur password zaroori hain!")
                elif password != confirm_password:
                    st.error("❌ Passwords match nahi kar rahe!")
                else:
                    try:
                        response = requests.post(
                            f"{API_URL}/auth/register",
                            json={
                                "full_name": name,
                                "email": email,
                                "password": password,
                                "phone": phone
                            },
                            timeout=5
                        )
                        
                        if response.status_code == 200:
                            st.success("✅ Account ban gaya! Ab login karein.")
                        elif response.status_code == 400:
                            st.error("❌ Ye email pehle se registered hai!")
                        else:
                            # Parse error details directly to show 500 error messages explicitly
                            try:
                                err_msg = response.json().get('detail', 'Unknown error')
                            except:
                                err_msg = response.text
                            st.error(f"❌ Error: {err_msg}")
                    except requests.exceptions.ConnectionError:
                        st.error("❌ Backend server nahi chal raha! Terminal mein `uvicorn main:app --reload --port 8000` run karein.")
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}") 

def logout():
    """User logout - URL se bhi token hatao"""
    st.session_state.token = None
    st.session_state.user = None
    st.session_state.user_email = None
    st.query_params.clear()  # 🔥 URL se bhi clear karo
    st.rerun()

def fetch_disease_from_kb(crop, disease_label):
    """Backend disease knowledge base se ilaaj lao"""
    try:
        disease_name = disease_label.replace("_", " ").strip()
        resp = requests.get(
            f"{API_URL}/diseases",
            params={"crop": crop, "disease": disease_name},
            timeout=5,
        )
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return None


def save_scan_to_backend(uploaded_file, crop_key, disease, confidence, ai_advice=None):
    """Scan ko backend/database mein save karo"""
    if not st.session_state.token:
        return False, "Login required"
    
    try:
        headers = {"Authorization": f"Bearer {st.session_state.token}"}
        
        files = {"image": ("scan.jpg", uploaded_file.getvalue(), "image/jpeg")}
        data = {
            "crop": crop_key,
            "disease": disease,
            "confidence": str(float(confidence)),
        }
        if ai_advice:
            data["ai_advice"] = ai_advice
        
        response = requests.post(
            f"{API_URL}/scans",
            headers=headers,
            files=files,
            data=data,
            timeout=15,
        )
        
        if response.status_code == 200:
            return True, response.json().get("scan_id")
        try:
            detail = response.json().get("detail", "Save failed")
        except Exception:
            detail = response.text or f"HTTP {response.status_code}"
        return False, detail
    except Exception as e:
        return False, str(e)


def get_scan_history():
    """Database se scan history lao"""
    if not st.session_state.token:
        return []
    
    try:
        headers = {"Authorization": f"Bearer {st.session_state.token}"}
        response = requests.get(
            f"{API_URL}/scans/history",
            headers=headers,
            timeout=10,
        )
        
        if response.status_code == 200:
            return response.json().get("scans", [])
        if "api_error" not in st.session_state:
            try:
                err = response.json().get("detail", response.text)
            except Exception:
                err = response.text
            st.session_state.api_error = f"History load failed ({response.status_code}): {err}"
        return []
    except Exception as e:
        st.session_state.api_error = f"Backend connect error: {e}"
        return []


def get_user_stats_api():
    """Dashboard stats from API"""
    if not st.session_state.token:
        return None
    try:
        headers = {"Authorization": f"Bearer {st.session_state.token}"}
        resp = requests.get(f"{API_URL}/scans/stats", headers=headers, timeout=10)
        if resp.status_code == 200:
            return resp.json()
        return None
    except Exception:
        return None


def compute_stats_from_history(scans):
    """Dashboard stats from scan history (fallback if /scans/stats fails)."""
    from datetime import datetime, timedelta

    total = len(scans)
    crop_breakdown = {}
    disease_count = 0
    confidences = []
    week_ago = datetime.now() - timedelta(days=7)
    weekly_scans = 0

    for s in scans:
        crop = s.get("crop_type") or "unknown"
        crop_breakdown[crop] = crop_breakdown.get(crop, 0) + 1
        disease = (s.get("predicted_disease") or "")
        if "healthy" not in disease.lower():
            disease_count += 1
        confidences.append(float(s.get("confidence") or 0))
        try:
            raw = str(s.get("created_at") or "")[:19]
            if raw:
                dt = datetime.strptime(raw.replace("T", " ")[:19], "%Y-%m-%d %H:%M:%S")
                if dt >= week_ago:
                    weekly_scans += 1
        except Exception:
            pass

    return {
        "total_scans": total,
        "crop_breakdown": crop_breakdown,
        "disease_count": disease_count,
        "healthy_count": total - disease_count,
        "weekly_scans": weekly_scans,
        "avg_confidence": round(sum(confidences) / len(confidences), 1) if confidences else 0,
    }

# ==============================================================================
# 🔥 AUTH CHECK - Agar login nahi hai toh auth page dikhao
# ==============================================================================
if not st.session_state.token:
    render_auth_page()
    st.stop()


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

# Pepper
PEPPER_URDU_NAMES = {"Bacterial Spot": "بیکٹیریل دھبے", "Healthy": "صحت مند"}
PEPPER_LOCAL_NAMES = {"Bacterial Spot": "مرچ تے کالے دھبے", "Healthy": "تندرست فصل"}

# Corn 
CORN_URDU_NAMES = {"Blight": "جھلس روگ", "Common Rust": "کنگی روگ", "Gray Leaf Spot": "سرمئی دھبے", "Healthy": "صحت مند"}
CORN_LOCAL_NAMES = {"Blight": "پتیاں دا سڑنا", "Common Rust": "مکئی دی کنگی", "Gray Leaf Spot": "سرمئی داغ", "Healthy": "تندرست فصل"}

CROP_CONFIG = {
    "potato": {
        "model_file": "potato_disease_model_v3.pkl",
        "urdu_names": POTATO_URDU_NAMES,
        "local_names": POTATO_LOCAL_NAMES,
        "emoji": "🥔",
        "display_name": "Potato — آلو",
        "accuracy": "99%",  # <-- Isay 99% kar lein
        "diseases": 3,
        "nav_key": "🥔 Potato (Aloo)",
        "uploader_label": "Upload Potato Leaf Photo / آلو کا پتہ اپلوڈ کریں",
        "model_missing_msg": "⚠️ **Model File Missing!** Please ensure `potato_disease_model_v3.pkl` is in the project directory.",
        "header_title": "Potato Disease Scan | آلو کی بیماری",
        "header_sub": "XGBoost v3 · HOG+LBP+GLCM+ORB · 99% Accuracy", # <-- Nayi Details
    },
    "tomato": {
        "model_file": "tomato_disease_model_v3.pkl",
        "urdu_names": TOMATO_URDU_NAMES,
        "local_names": TOMATO_LOCAL_NAMES,
        "emoji": "🍅",
        "display_name": "Tomato — ٹماٹر",
        "accuracy": "95%",
        "diseases": 9,
        "nav_key": "🍅 Tomato Check",
        "uploader_label": "Upload Tomato Leaf Photo / ٹماٹر کا پتہ اپلوڈ کریں",
        "model_missing_msg": "⚠️ **Tomato Model File Missing!** Please ensure `tomato_disease_model_v3.pkl` is in the project directory.",
        "header_title": "Tomato Disease Scan | ٹماٹر کی بیماری",
        "header_sub": "Random Forest · HOG + LBP + GLCM + Color · 95% Accuracy · 9 Classes",
    },
    "pepper": {
        "model_file": "pepper_disease_model_v3.pkl",
        "urdu_names": PEPPER_URDU_NAMES,
        "local_names": PEPPER_LOCAL_NAMES,
        "emoji": "🫑",
        "display_name": "Pepper — مرچ",
        "accuracy": "99%",
        "diseases": 2,
        "nav_key": "🫑 Pepper (Mirch)",
        "uploader_label": "Upload Pepper Leaf Photo / مرچ کا پتہ اپلوڈ کریں",
        "model_missing_msg": "⚠️ **Pepper Model File Missing!** Please ensure `pepper_disease_model_v3.pkl` is in the project directory.",
        "header_title": "Pepper Disease Scan | مرچ کی بیماری",
        "header_sub": "XGBoost v3 · HOG+LBP+GLCM+ORB · 99% Accuracy",
    },
    "corn": {
        "model_file": "corn_disease_model_v3.pkl",
        "urdu_names": CORN_URDU_NAMES,
        "local_names": CORN_LOCAL_NAMES,
        "emoji": "🌽",
        "display_name": "Corn — مکئی",
        "accuracy": "87%",
        "diseases": 4,
        "nav_key": "🌽 Corn Field",
        "uploader_label": "Upload Corn Leaf Photo / مکئی کا پتہ اپلوڈ کریں",
        "model_missing_msg": "⚠️ **Corn Model File Missing!** Please ensure `corn_disease_model_v3.pkl` is in the project directory.",
        "header_title": "Corn Disease Scan | مکئی کی بیماری",
        "header_sub": "XGBoost v3 · HOG+LBP+GLCM+ORB · 87% Accuracy",
    },
}

# --- 4. MODEL LOADING — Graceful degradation (v3 improvement) ---
@st.cache_resource
def safe_load_models():
    """Load all crop models + master crop detector. Missing models don't crash app."""
    models = {}
    model_files = {
        "potato": ("potato_disease_model_v3.pkl",        "class_names"),
        "tomato": ("tomato_disease_model_v3.pkl", "class_names"),
        "pepper": ("pepper_disease_model_v3.pkl",        "class_names"),
        "corn":   ("corn_disease_model_v3.pkl",          "class_names"),
        "master": ("crop_detector_v3_ultimate.pkl",      "classes"),
    }
    for crop_key, (file_path, cls_key) in model_files.items():
        try:
            data = joblib.load(file_path)
            # ✅ Extract ALL pipeline components (model, scaler, vt, pca, selector, class_names)
            models[crop_key] = (
                data.get('model'),              # 0
                data.get('scaler'),             # 1
                data.get('variance_threshold'), # 2 — VarianceThreshold
                data.get('pca'),                # 3 — PCA
                data.get('selector'),           # 4 — SelectKBest
                data.get(cls_key)               # 5 — class names
            )
        except Exception:
            models[crop_key] = (None, None, None, None, None, None)
    return models

MODELS = safe_load_models()

# Keep these for any legacy references
_potato_data = MODELS.get("potato", (None, None, None, None, None, None))
rf_model, scaler = _potato_data[0], _potato_data[1]
selector, class_names = _potato_data[4], _potato_data[5]
_tomato_data = MODELS.get("tomato", (None, None, None, None, None, None))
t_model, t_scaler = _tomato_data[0], _tomato_data[1]
t_selector, t_class_names = _tomato_data[4], _tomato_data[5]

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
    if len(image_bytes) > 10 * 1024 * 1024:
        raise ValueError("Image too large. Please use images under 10MB.")

    nparr = np.frombuffer(image_bytes, np.uint8)
    if nparr.size == 0:
        raise ValueError("Empty image data received.")

    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise cv2.error("Could not decode image.")

    img = cv2.resize(img, (128, 128))

    # ✅ STEP 1: CLAHE — lighting normalize karo
    # Real photos mein lighting uneven hoti hai
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    lab[:, :, 0] = clahe.apply(lab[:, :, 0])
    img = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

    # ✅ STEP 2: Color Normalization
    # Dataset images ka color balance alag hota hai real se
    img = img.astype(np.float32)
    for c in range(3):
        ch = img[:, :, c]
        mn, mx = ch.min(), ch.max()
        if mx > mn:
            img[:, :, c] = (ch - mn) / (mx - mn) * 255
    img = img.astype(np.uint8)

    gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Features — same as before
    hist_bgr = cv2.calcHist([img], [0,1,2], None,
                             [8,8,8], [0,256,0,256,0,256])
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    hist_hsv = cv2.calcHist([hsv], [0,1,2], None,
                             [8,8,8], [0,180,0,256,0,256])
    f_color = np.hstack([hist_bgr.flatten(), hist_hsv.flatten()])

    f_hog = hog(gray_img, orientations=9,
                pixels_per_cell=(8, 8),
                cells_per_block=(2, 2),
                visualize=False)

    radius, n_points = 2, 16
    lbp = local_binary_pattern(gray_img, n_points, radius, method='uniform')
    hist, _ = np.histogram(lbp.ravel(),
                           bins=np.arange(0, n_points + 3),
                           range=(0, n_points + 2))
    hist = hist.astype("float")
    f_lbp = hist / (hist.sum() + 1e-7)

    glcm = graycomatrix(gray_img, distances=[1, 2],
                        angles=[0, np.pi/4, np.pi/2, 3*np.pi/4],
                        levels=256, symmetric=True, normed=True)
    f_glcm = np.array([
        graycoprops(glcm, p).mean()
        for p in ['contrast','correlation','energy',
                  'homogeneity','dissimilarity']
    ])

    result = np.hstack([f_color, f_hog, f_lbp, f_glcm])
    del img, gray_img, hsv, lbp, glcm
    gc.collect()

    return result

# ==============================================================================
# --- V3 FEATURE EXTRACTION (Specially for Potato v3 and future models)
# ==============================================================================
def extract_gabor(gray):
    feats = []
    for theta in range(4):
        theta_rad = theta * np.pi / 4
        for freq in [0.1, 0.3, 0.5]:
            lam = 1.0/freq if freq > 0 else 1.0
            kernel = cv2.getGaborKernel((21,21), 5.0, theta_rad, lam, 0.5, 0, ktype=cv2.CV_32F)
            filtered = cv2.filter2D(gray, cv2.CV_32F, kernel)
            feats.extend([filtered.mean(), filtered.std(), np.percentile(filtered, 25), np.percentile(filtered, 75)])
    return np.array(feats)

def extract_orb(img):
    orb  = cv2.ORB_create(nfeatures=300)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, des = orb.detectAndCompute(gray, None)
    if des is None or len(des) == 0:
        return np.zeros(32)
    return np.mean(des, axis=0).astype(np.float32)

@safe_analysis
def extract_features_v3(image_bytes):
    if len(image_bytes) > 10 * 1024 * 1024: raise ValueError("Image too large.")
    nparr = np.frombuffer(image_bytes, np.uint8)
    if nparr.size == 0: raise ValueError("Empty image data received.")
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None: raise cv2.error("Could not decode image.")

    img = cv2.resize(img, (128, 128))
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    lower = np.array([15, 20, 20])
    upper = np.array([100, 255, 255])
    mask  = cv2.inRange(hsv, lower, upper)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5,5))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN,  kernel)

    mean_color = cv2.mean(img, mask=mask)[:3]
    background = np.ones_like(img, dtype=np.uint8)
    background[:] = [int(c) for c in mean_color]
    img = np.where(mask[:,:,None] == 0, background, img).astype(np.uint8)

    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8,8))
    lab[:,:,0] = clahe.apply(lab[:,:,0])
    img = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

    img_f = img.astype(np.float32)
    avg   = [img_f[:,:,c].mean() for c in range(3)]
    avg_gray = sum(avg) / 3.0
    for c in range(3):
        if avg[c] > 0: img_f[:,:,c] *= avg_gray / avg[c]
    img = np.clip(img_f, 0, 255).astype(np.uint8)

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    hsv  = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    hist_bgr = cv2.calcHist([img],[0,1,2],None,[16,16,16],[0,256,0,256,0,256])
    hist_bgr = cv2.normalize(hist_bgr, hist_bgr).flatten()
    hist_hsv = cv2.calcHist([hsv],[0,1,2],None,[16,16,16],[0,180,0,256,0,256])
    hist_hsv = cv2.normalize(hist_hsv, hist_hsv).flatten()

    color_moments = []
    for c in range(3):
        ch = img[:,:,c].astype(np.float32)
        color_moments.extend([ch.mean(), ch.std(), np.percentile(ch,25), np.percentile(ch,75)])
    f_color = np.hstack([hist_bgr, hist_hsv, color_moments])

    f_hog = []
    f_hog.extend(hog(gray, orientations=9, pixels_per_cell=(8,8), cells_per_block=(2,2), visualize=False))
    f_hog.extend(hog(gray, orientations=9, pixels_per_cell=(16,16), cells_per_block=(2,2), visualize=False))
    small = cv2.resize(gray, (64, 64))
    f_hog.extend(hog(small, orientations=9, pixels_per_cell=(8,8), cells_per_block=(2,2), visualize=False))
    f_hog = np.array(f_hog)

    f_lbp = []
    for r, p in [(1,8),(2,16),(3,24)]:
        lbp = local_binary_pattern(gray, p, r, method='uniform')
        h, _ = np.histogram(lbp.ravel(), bins=np.arange(0,p+3), range=(0,p+2))
        h = h.astype("float"); h /= (h.sum()+1e-7)
        f_lbp.extend(h)
    f_lbp = np.array(f_lbp)

    glcm = graycomatrix(gray, distances=[1,2,3], angles=[0,np.pi/4,np.pi/2,3*np.pi/4], levels=256, symmetric=True, normed=True)
    f_glcm = np.array([graycoprops(glcm,p).mean() for p in ['contrast','correlation','energy','homogeneity','dissimilarity','ASM']])

    f_gabor = extract_gabor(gray)
    f_orb   = extract_orb(img)

    result = np.hstack([f_color, f_hog, f_lbp, f_glcm, f_gabor, f_orb])
    del img, gray, hsv, lbp, glcm
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
        # ✅ FIX #4: Handle 6 items from pipeline
        master_data = MODELS.get("master", (None, None, None, None, None, None))
        if len(master_data) == 6:
            master_model, master_scaler, master_vt, master_pca, master_sel, master_classes = master_data
        else:
            master_model = master_data[0] if master_data else None
            master_scaler = master_vt = master_pca = master_sel = master_classes = None

        if master_model:
            try:
                # ✅ FIX #5: Use extract_features_v3 — SAME as training!
                features = extract_features_v3(image_bytes)
                if features is not None:
                    features = np.nan_to_num(features).reshape(1, -1)
                    # ✅ Apply full 4-step pipeline
                    if master_scaler:
                        features = master_scaler.transform(features)
                    if master_vt:
                        features = master_vt.transform(features)
                    if master_pca:
                        features = master_pca.transform(features)
                    if master_sel:
                        features = master_sel.transform(features)
                    probs = master_model.predict_proba(features)[0]
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
# --- call api 
def get_ai_doctor_advice(disease_name):
    if "healthy" in disease_name.lower():
        return "✅ **Fasal bilkul theek hai!** Waqat par paani dein aur khet ko saaf rakhein taake koi aane wali bimari se bacha ja sake."
    
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"""
        Tum ek expert Pakistani Agricultural Doctor ho. 
        Kisan ki fasal mein '{disease_name}' ki bimari aayi hai.
        Mujhe Roman Urdu mein 3 points par mabni ilaj (treatment) batao:
        1. 🧪 Best Chemical Spray (Medicine ka naam aur istemal ka tarika)
        2. 🌱 Desi/Organic ilaj (Gharelu totka)
        3. ✂️ Ehtiyati tadabeer (Precautions/Field Management)
        
        Jawab bohot lamba na ho, short aur bullet points mein ho.
        """
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        # Agar internet band ho ya API issue ho toh yeh emergency text chalega
        return f"⚠️ **{disease_name} ka Ilaj:**\n- Fauran kisi qareebi zaraee markaz (agriculture center) se rabta karein.\n- Mutasira patton ko kaat kar khet se door phenk dein taake bimari phelne se ruk jaye."

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
    color: #064e3b !important; /* YEH LINE ADD KI HAI - Dark Green Text */
    border: 1px solid rgba(6,78,59,0.2) !important;
} 

[data-testid="stSidebar"] .stButton > button:hover {
    background-color: #d1fae5 !important;
}
.stButton > button[kind="primary"] {
    background: linear-gradient(90deg, var(--emerald-700), var(--emerald-500)) !important;
    border: none !important;
    color: #ffffff !important; /* YEH LINE ADD KI HAI - White Text sirf primary ke liye */
    box-shadow: 0 4px 20px rgba(16,185,129,0.35) !important;
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

/* SIDEBAR BUTTONS - FINAL FIX */
[data-testid="stSidebar"] .stButton > button {
    background-color: #f8fafc !important;
    color: #064e3b !important;
    border: 2px solid #064e3b !important;
    font-weight: 900 !important;
}

[data-testid="stSidebar"] .stButton > button p,
[data-testid="stSidebar"] .stButton > button span,
[data-testid="stSidebar"] .stButton > button div {
    color: #064e3b !important;
}

[data-testid="stSidebar"] .stButton > button:hover {
    background-color: #d1fae5 !important;
    color: #047857 !important;
    border-color: #047857 !important;
}

[data-testid="stSidebar"] .stButton > button:hover p,
[data-testid="stSidebar"] .stButton > button:hover span,
[data-testid="stSidebar"] .stButton > button:hover div {
    color: #047857 !important;
} 
/* SELECTBOX ARROW - ULTIMATE FIX */
[data-testid="stSidebar"] .stSelectbox div[role="button"] svg,
[data-testid="stSidebar"] .stSelectbox div[role="combobox"] svg,
[data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] svg {
    fill: #064e3b !important;
    stroke: #064e3b !important;
    width: 20px !important;
    height: 20px !important;
}

/* Arrow ke parent container ko bhi style karo */
[data-testid="stSidebar"] .stSelectbox div[role="button"],
[data-testid="stSidebar"] .stSelectbox div[role="combobox"] {
    color: #064e3b !important;
} 

/* Selectbox ke andar ka text (jo selected dikhta hai) */
[data-testid="stSidebar"] .stSelectbox > div[data-baseweb="select"] span,
[data-testid="stSidebar"] .stSelectbox > div[data-baseweb="select"] div {
    color: #064e3b !important;
    font-weight: 700 !important;
}

/* Dropdown menu ke options (jo neeche khulta hai) */
[data-testid="stSidebar"] div[role="listbox"] div,
[data-testid="stSidebar"] div[role="option"] {
    color: #064e3b !important;
    background-color: #f8fafc !important;
}

/* Dropdown option hover par */
[data-testid="stSidebar"] div[role="option"]:hover {
    background-color: #d1fae5 !important;
    color: #047857 !important;
}
/* ==============================================================================
   🔥 FIX #3: SELECTBOX ARROW + HAND CURSOR FIX
   ============================================================================== */
[data-testid="stSidebar"] .stSelectbox > div[data-baseweb="select"] { cursor: pointer !important; }
[data-testid="stSidebar"] .stSelectbox div[role="button"],
[data-testid="stSidebar"] .stSelectbox div[role="combobox"] { cursor: pointer !important; color: #064e3b !important; }
[data-testid="stSidebar"] .stSelectbox svg,
[data-testid="stSidebar"] .stSelectbox [data-testid="stIcon"] svg {
    fill: #064e3b !important; stroke: #064e3b !important; color: #064e3b !important;
    opacity: 1 !important; width: 20px !important; height: 20px !important; cursor: pointer !important;
}

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
.slide img { width:100%; height:100%; object-fit:cover; border-radius:14px; transition:transform 0.5s, filter 0.5s; background: linear-gradient(135deg, #ecfdf5, #d1fae5); }
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
<div style="background:rgba(255,255,255,0.1);border-radius:12px;padding:15px;margin-bottom:20px;border:1px solid rgba(255,255,255,0.2);">
    <h3 style="margin:0 0 10px;font-size:1rem;color:white;display:flex;align-items:center;gap:6px;">📱 Install App (PWA)</h3>
    <p style="font-size:0.8rem;color:#d1d5db;margin:0 0 10px;">Aap isay apne mobile ki home screen par laga sakte hain:</p>
    <ul style="font-size:0.75rem;color:#d1d5db;margin:0;padding-left:15px;">
        <li>Mobile Browser mein menu (⋮) dabayen</li>
        <li>"Add to Home Screen" ya "Install App" par click karein</li>
    </ul>
    <a href="/pwa/index.html" target="_blank" style="display:block;margin-top:10px;text-align:center;background:#10b981;color:white;text-decoration:none;padding:6px;border-radius:6px;font-size:0.8rem;font-weight:bold;">Test App Experience</a>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown("""
<h1 style='text-align:center;color:white;font-weight:900;margin-top:-6px;font-size:1.9rem;letter-spacing:-0.5px;'>Plant Doctor</h1>
<p style='text-align:center;font-size:0.72rem;opacity:0.7;margin-bottom:22px;letter-spacing:3px;font-weight:600;'>AI DIAGNOSTICS v2.0</p>
""", unsafe_allow_html=True)

st.sidebar.write("---")
# Build nav list dynamically based on role
nav_options = ["🏠 Home Page", "🥔 Potato (Aloo)", "🍅 Tomato Check", "🫑 Pepper (Mirch)", "🌽 Corn Field", "👤 My Profile", "📊 Dashboard", "💬 Expert Chat"]
if st.session_state.user and st.session_state.user.lower() == "admin":
    nav_options.append("🛡️ Admin Panel")

# Ensure nav_default is valid
if nav_default not in nav_options:
    nav_default = "🏠 Home Page"

nav = st.sidebar.radio("", nav_options, index=nav_options.index(nav_default))

st.sidebar.write("---")



# Logout button
if st.sidebar.button("🚪 Logout", use_container_width=True):
    logout()

# ==============================================================================
# 🔥 SIDEBAR HISTORY — Premium Card UI
# ==============================================================================

st.sidebar.write("---")
st.sidebar.markdown("<p style='font-size:0.75rem;opacity:0.7;text-transform:uppercase;letter-spacing:1px;font-weight:700;'>📊 Scan History</p>", unsafe_allow_html=True)

if st.session_state.get("api_error"):
    st.sidebar.warning(st.session_state.api_error[:120])

history_scans = get_scan_history()

if history_scans:
    emoji_map = {"potato": "🥔", "tomato": "🍅", "pepper": "🫑", "corn": "🌽"}
    
    # Show last 5 scans as styled cards
    for i, s in enumerate(history_scans[:5]):
        crop = s.get('crop_type', s.get('crop', 'unknown'))
        disease = s.get('predicted_disease', s.get('disease', 'Unknown'))
        conf = s.get('confidence', 0)
        raw_date = str(s.get('created_at', ''))
        # Format date nicely
        try:
            date_str = raw_date[:16].replace('T', ' · ')
        except:
            date_str = raw_date[:16]
        
        is_healthy = 'healthy' in disease.lower()
        border_color = "rgba(16,185,129,0.6)" if is_healthy else "rgba(239,68,68,0.5)"
        emoji = emoji_map.get(crop, "🌿")
        conf_bg = "rgba(16,185,129,0.3)" if is_healthy else "rgba(239,68,68,0.25)"
        
        st.sidebar.markdown(f"""
        <div style="background:rgba(255,255,255,0.06);border-radius:12px;padding:10px 12px;margin-bottom:8px;border-left:3px solid {border_color};cursor:pointer;transition:all 0.2s;">
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;">
                <span style="font-size:1.1rem;">{emoji}</span>
                <span style="font-weight:700;font-size:0.82rem;color:#ecfdf5;">{disease}</span>
            </div>
            <div style="display:flex;justify-content:space-between;align-items:center;">
                <span style="font-size:0.65rem;opacity:0.5;">{date_str}</span>
                <span style="background:{conf_bg};padding:2px 8px;border-radius:10px;font-size:0.65rem;font-weight:700;">{conf:.0f}%</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # Dropdown for detail view (cleaner labels)
    scan_labels = []
    for i, s in enumerate(history_scans):
        crop = s.get('crop_type', s.get('crop', 'unknown')).title()
        disease = s.get('predicted_disease', s.get('disease', 'Unknown'))
        raw_date = str(s.get('created_at', ''))[:10]
        scan_labels.append(f"{crop} · {disease} · {raw_date}")
    
    selected_idx = st.sidebar.selectbox("Detail dekhein:", range(len(scan_labels)), format_func=lambda i: scan_labels[i], key="hist_select")

    if st.sidebar.button("🔍 Detail Report Dekhein", use_container_width=True):
        st.session_state['view_history_detail'] = history_scans[selected_idx]
    
    # Total count
    if len(history_scans) > 5:
        st.sidebar.markdown(f"<p style='font-size:0.7rem;opacity:0.5;text-align:center;'>+ {len(history_scans)-5} more scans · Dashboard mein dekhein</p>", unsafe_allow_html=True)
else:
    st.sidebar.markdown("""
    <div style="background:rgba(255,255,255,0.04);border-radius:12px;padding:16px;text-align:center;border:1px dashed rgba(255,255,255,0.1);">
        <div style="font-size:1.5rem;margin-bottom:6px;">📭</div>
        <div style="font-size:0.78rem;opacity:0.5;font-weight:600;">Koi scan nahi kiya abhi</div>
        <div style="font-size:0.68rem;opacity:0.35;margin-top:3px;">Home page se pehla scan karein!</div>
    </div>
    """, unsafe_allow_html=True)

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

    infer_badge = ""
    if inference_time is not None:
        infer_badge = f'<div class="infer-badge">⚡ {inference_time:.2f}s inference time</div>'

    # WARNING: Do NOT add spaces before the HTML tags inside this string!
    html_1 = f"""
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
"""
    st.markdown(html_1, unsafe_allow_html=True)

    st.markdown('<div class="breakdown-section"><div class="breakdown-title">📊 Probability Distribution</div>', unsafe_allow_html=True)
    sorted_probs = sorted(prob_dict.items(), key=lambda x: x[1], reverse=True)
    for i, (lbl, pct) in enumerate(sorted_probs):
        clean_lbl = lbl.replace('_', ' ').title()
        fill_color = bar_color if i == 0 else "#d1d5db"
        row_html = f"""
<div class="breakdown-row">
<div class="breakdown-lbl">{clean_lbl}</div>
<div class="breakdown-track"><div class="breakdown-fill" style="width:{pct:.1f}%;background:{'linear-gradient(90deg,'+bar_color+','+bar_color+'aa)' if i==0 else '#d1d5db'};"></div></div>
<div class="breakdown-pct">{pct:.1f}%</div>
</div>
"""
        st.markdown(row_html, unsafe_allow_html=True)
    st.markdown('</div></div>', unsafe_allow_html=True)

    return is_healthy, sev

def render_treatment(label, is_healthy, crop="potato"):
    kb = fetch_disease_from_kb(crop, label)
    if kb:
        sev = kb.get("severity_level", 3)
        st.markdown(f"### Disease Guide: {kb.get('disease_name', label)}")
        st.markdown(f"**Symptoms:** {kb.get('symptoms', 'N/A')}")
        st.markdown(f"**Chemical:** {kb.get('chemical_treatment', 'N/A')}")
        st.markdown(f"**Organic:** {kb.get('organic_treatment', 'N/A')}")
        st.markdown(f"**Prevention:** {kb.get('prevention', 'N/A')}")
        return


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
    # ✅ FIX #3: Unpack 6 items from pipeline
    model_data = MODELS.get(crop_key, (None, None, None, None, None, None))
    if len(model_data) == 6:
        model, scaler, vt, pca, sel, crop_class_names = model_data
    else:
        # Fallback for old models
        model, scaler, crop_class_names = model_data[0], model_data[1], model_data[-1]
        vt = pca = sel = None

    if not model:
        st.error(CROP_CONFIG[crop_key]['model_missing_msg'])
        return None

    start_time = time.time()

    # ✅ FIX #5: Use extract_features_v3 for ALL crops (matches training pipeline)
    features = extract_features_v3(uploaded_file.getvalue())

    if features is None:
        return None

    features = np.nan_to_num(features).reshape(1, -1)

    # ✅ FIX #3: Apply FULL 4-step pipeline
    if scaler is not None:
        features = scaler.transform(features)
    if vt is not None:
        features = vt.transform(features)
    if pca is not None:
        features = pca.transform(features)
    if sel is not None:
        features = sel.transform(features)

    probs = model.predict_proba(features)[0]
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
    """Render report + AI treatment from a result dict. Used by both pages."""
    if result['conf'] < 46:
        show_low_confidence_warning()
        return None
        
    ts = datetime.datetime.now().strftime("%d %b %Y · %H:%M")
    urdu_name = config['urdu_names'].get(result['label'], result['label'])
    local_name = config['local_names'].get(result['label'], result['label'])
    
    # 1. Pehle result ka Meter aur Report Card print karega
    is_healthy, _ = render_report(
        result['label'], result['conf'], result['prob_dict'],
        urdu_name, local_name, config['display_name'], ts, result['inference_time']
    )
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    if is_healthy:
        st.balloons()
        
    # --- YAHAN SE AI DOCTOR KA MAGIC SHURU HOTA HAI ---
    
    st.markdown("<h3 style='color:#064e3b;font-weight:800;margin-bottom:10px;'>👨‍⚕️ AI Doctor Ki Tajaweez (Live Advice)</h3>", unsafe_allow_html=True)
    
    # Spinner lagaya taake jab tak API se jawab aaye, user ko lage doctor soch raha hai
    with st.spinner('AI Doctor aapki fasal ka nuskha tayyar kar raha hai... (Is mein 2-3 sec lagenge)'):
        ai_advice = get_ai_doctor_advice(result['label'])
        
    # AI ka jawab ek khoobsurat green box mein show hoga
    st.info(ai_advice)

    render_treatment(result['label'], is_healthy, crop_key)
    return ai_advice


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
            st.image(pil_img, caption="📷 Uploaded Leaf Photo", use_container_width=True)
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
            ai_advice = show_result(result, crop_key, config)
            
            # ==============================================================================
            # 🔥 SCAN SAVE KARO (NEW - Single file scan ke baad)
            # ==============================================================================
            with st.spinner("💾 Scan database mein save ho raha hai..."):
                success, msg = save_scan_to_backend(
                    uploaded_file, 
                    crop_key, 
                    result['label'], 
                    result['conf'],
                    ai_advice=ai_advice,
                )
                
                if success:
                    st.success("Scan history mein save ho gaya!")
                    st.rerun()
                else:
                    st.error(f"Scan save nahi hua: {msg}")

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
                            
                            # ==============================================================================
                            # 🔥 BATCH SCAN SAVE (NEW)
                            # ==============================================================================
                            save_scan_to_backend(uploaded_file, crop_key, label, conf)
            progress_bar.progress((i + 1) / len(uploaded_files), text=f"Scanning {i+1}/{len(uploaded_files)}...")
        progress_bar.empty()
        st.toast(f"Batch complete! {len(uploaded_files)} pattay scan ho gaye.", icon="📦") 

# ==============================================================================
# 🔥 HISTORY DETAIL VIEW (Main Screen par dikhane ke liye)
# ==============================================================================

if 'view_history_detail' in st.session_state and st.session_state['view_history_detail'] is not None:
    scan = st.session_state['view_history_detail']
    
    st.markdown("---")
    if st.button("⬅️ Back to Main App"):
        st.session_state['view_history_detail'] = None
        st.rerun()
        
    st.subheader("📜 Purani Diagnostic Report")
    
    # Data nikalna
    crop_key = scan.get('crop_type', 'potato')
    disease = scan.get('predicted_disease', 'Unknown')
    conf = scan.get('confidence', 0)
    
    # Report dikhane ke liye config nikalna
    config = CROP_CONFIG.get(crop_key, CROP_CONFIG['potato'])
    urdu_name = config['urdu_names'].get(disease, disease)
    local_name = config['local_names'].get(disease, disease)
    ts = scan.get('created_at', 'N/A')

    # Re-render report UI
    render_report(
        disease, conf, {disease: conf}, 
        urdu_name, local_name, config['display_name'], ts
    )
    
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<h3 style='color:#064e3b;font-weight:800;'>👨‍⚕️ AI Doctor Ka Purana Mashwara</h3>", unsafe_allow_html=True)
    
    saved_advice = scan.get('ai_advice')
    if saved_advice:
        st.info(saved_advice)
    else:
        with st.spinner('Puraana nuskha nikal raha hoon...'):
            ai_advice = get_ai_doctor_advice(disease)
        st.info(ai_advice)
    render_treatment(disease, 'healthy' in disease.lower(), crop_key)
    
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("""
    <div style="background:linear-gradient(135deg,#e0f2fe,#bae6fd);border-radius:16px;padding:20px;border:1px solid rgba(14,165,233,0.2);">
        <h3 style="color:#0369a1;font-weight:800;margin:0 0 10px;">👨‍🌾 Zaraat ke Mahir se Puchiye (Ask Expert)</h3>
        <p style="color:#0c4a6e;font-size:0.85rem;margin:0 0 15px;">Agar AI ki report se mutmain nahi hain, toh apne sawal agricultural expert ko bhejein.</p>
    </div>
    """, unsafe_allow_html=True)
    
    expert_msg = st.text_area("Aap ka sawal:", placeholder="Mera sawal hai ke...", key="exp_msg")
    if st.button("📤 Expert Ko Bhejein", type="primary"):
        if not expert_msg.strip():
            st.warning("⚠️ Sawal likhna zaroori hai!")
        else:
            try:
                headers = {"Authorization": f"Bearer {st.session_state.token}"}
                resp = requests.post(f"{API_URL}/consultations", headers=headers, json={"scan_id": str(scan['id']), "message": expert_msg}, timeout=5)
                if resp.status_code == 200:
                    st.toast("✅ Sawal expert ko bhej diya gaya hai!", icon="📤")
                else:
                    st.error(f"❌ Error: {resp.json().get('detail', 'Failed')}")
            except Exception as e:
                st.error("❌ Backend error!")
    
    st.stop() # <--- YEH MAGIC LINE HAI (Baaki app ko render hone se rok degi)


# ==============================================================================
# 👤 PROFILE PAGE
# ==============================================================================
def render_profile_page():
    st.markdown("""
    <div style="background:linear-gradient(135deg,#ecfdf5,#d1fae5);border-radius:24px;padding:32px;margin-bottom:24px;border:1px solid rgba(52,211,153,0.2);">
        <h2 style="color:#064e3b;font-weight:900;margin:0 0 6px;">👤 Meri Profile</h2>
        <p style="color:#6b7280;margin:0;font-size:0.9rem;">Apni info update karein aur password change karein</p>
    </div>
    """, unsafe_allow_html=True)

    # Fetch current user data
    user_data = None
    try:
        headers = {"Authorization": f"Bearer {st.session_state.token}"}
        resp = requests.get(f"{API_URL}/auth/me", headers=headers, timeout=5)
        if resp.status_code == 200:
            user_data = resp.json()
    except:
        pass

    if not user_data:
        st.warning("⚠️ Profile load nahi ho saki. Backend server check karein.")
        return

    col1, col2 = st.columns([1.2, 1])

    with col1:
        st.markdown(f"""
        <div style="background:white;border-radius:20px;padding:28px;box-shadow:0 4px 20px rgba(6,78,59,0.08);border:1px solid rgba(52,211,153,0.15);">
            <div style="display:flex;align-items:center;gap:16px;margin-bottom:20px;">
                <div style="width:64px;height:64px;border-radius:50%;background:linear-gradient(135deg,#10b981,#059669);display:flex;align-items:center;justify-content:center;font-size:1.8rem;color:white;font-weight:900;">{(user_data.get('full_name') or '?')[0].upper()}</div>
                <div>
                    <div style="font-size:1.3rem;font-weight:800;color:#064e3b;">{user_data['full_name']}</div>
                    <div style="font-size:0.82rem;color:#6b7280;">{user_data['email']}</div>
                    <span style="background:#d1fae5;color:#065f46;padding:3px 12px;border-radius:20px;font-size:0.7rem;font-weight:700;text-transform:uppercase;">{user_data['role']}</span>
                </div>
            </div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
                <div style="background:#f8fafc;border-radius:12px;padding:12px;"><span style="font-size:0.7rem;color:#6b7280;font-weight:600;">📱 Phone</span><br><b style="color:#064e3b;">{user_data.get('phone') or 'Not set'}</b></div>
                <div style="background:#f8fafc;border-radius:12px;padding:12px;"><span style="font-size:0.7rem;color:#6b7280;font-weight:600;">📍 Location</span><br><b style="color:#064e3b;">{user_data.get('location') or 'Not set'}</b></div>
                <div style="background:#f8fafc;border-radius:12px;padding:12px;"><span style="font-size:0.7rem;color:#6b7280;font-weight:600;">📅 Member Since</span><br><b style="color:#064e3b;">{str(user_data.get('created_at',''))[:10]}</b></div>
                <div style="background:#f8fafc;border-radius:12px;padding:12px;"><span style="font-size:0.7rem;color:#6b7280;font-weight:600;">🛡️ Role</span><br><b style="color:#064e3b;">{user_data['role'].title()}</b></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("#### ✏️ Profile Update Karein")
        new_name = st.text_input("Full Name", value=user_data['full_name'], key="prof_name")
        new_phone = st.text_input("Phone", value=user_data.get('phone') or '', key="prof_phone")
        new_location = st.text_input("Location", value=user_data.get('location') or '', key="prof_loc")

        if st.button("💾 Save Changes", type="primary", use_container_width=True, key="prof_save"):
            try:
                headers = {"Authorization": f"Bearer {st.session_state.token}"}
                resp = requests.put(f"{API_URL}/auth/profile", headers=headers, json={
                    "full_name": new_name, "phone": new_phone, "location": new_location
                }, timeout=5)
                if resp.status_code == 200:
                    st.success("✅ Profile updated!")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error(f"❌ {resp.json().get('detail','Error')}")
            except:
                st.error("❌ Backend se connect nahi ho saka!")

        st.markdown("---")
        st.markdown("#### 🔐 Password Change")
        old_pw = st.text_input("Current Password", type="password", key="old_pw")
        new_pw = st.text_input("New Password", type="password", key="new_pw")

        if st.button("🔒 Change Password", use_container_width=True, key="pw_change"):
            if not old_pw or not new_pw:
                st.error("Dono passwords daalein!")
            elif len(new_pw) < 6:
                st.error("New password kam az kam 6 characters ka hona chahiye!")
            else:
                try:
                    headers = {"Authorization": f"Bearer {st.session_state.token}"}
                    resp = requests.put(f"{API_URL}/auth/password", headers=headers,
                        json={"old_password": old_pw, "new_password": new_pw}, timeout=5)
                    if resp.status_code == 200:
                        st.success("✅ Password changed!")
                    else:
                        st.error(f"❌ {resp.json().get('detail','Error')}")
                except:
                    st.error("❌ Backend error!")


# ==============================================================================
# 📊 DASHBOARD PAGE
# ==============================================================================
def render_dashboard_page():
    st.markdown("""
    <div style="background:linear-gradient(135deg,#ecfdf5,#d1fae5);border-radius:24px;padding:32px;margin-bottom:24px;border:1px solid rgba(52,211,153,0.2);">
        <h2 style="color:#064e3b;font-weight:900;margin:0 0 6px;">📊 Mera Dashboard</h2>
        <p style="color:#6b7280;margin:0;font-size:0.9rem;">Apne scan history, crop stats aur trends dekhein</p>
    </div>
    """, unsafe_allow_html=True)

    stats = get_user_stats_api()
    stats_from_history = False

    if not stats:
        history = get_scan_history()
        if history:
            stats = compute_stats_from_history(history)
            stats_from_history = True
        else:
            api_err = st.session_state.pop("api_error", None)
            if api_err:
                st.error(api_err)
            else:
                st.info("Abhi tak koi scan nahi kiya. Pehle ek crop scan karein!")
            return

    if stats_from_history:
        st.caption("ℹ️ Stats aapki scan history se calculate kiye gaye.")

    # Stats cards
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""<div style="background:white;border-radius:16px;padding:20px;text-align:center;box-shadow:0 4px 16px rgba(6,78,59,0.08);border-top:3px solid #10b981;">
            <div style="font-size:2rem;font-weight:900;color:#064e3b;">{stats['total_scans']}</div>
            <div style="font-size:0.75rem;color:#6b7280;font-weight:600;text-transform:uppercase;">Total Scans</div></div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""<div style="background:white;border-radius:16px;padding:20px;text-align:center;box-shadow:0 4px 16px rgba(6,78,59,0.08);border-top:3px solid #059669;">
            <div style="font-size:2rem;font-weight:900;color:#064e3b;">{stats['healthy_count']}</div>
            <div style="font-size:0.75rem;color:#6b7280;font-weight:600;text-transform:uppercase;">Healthy Scans</div></div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""<div style="background:white;border-radius:16px;padding:20px;text-align:center;box-shadow:0 4px 16px rgba(6,78,59,0.08);border-top:3px solid #dc2626;">
            <div style="font-size:2rem;font-weight:900;color:#dc2626;">{stats['disease_count']}</div>
            <div style="font-size:0.75rem;color:#6b7280;font-weight:600;text-transform:uppercase;">Diseases Found</div></div>""", unsafe_allow_html=True)
    with c4:
        st.markdown(f"""<div style="background:white;border-radius:16px;padding:20px;text-align:center;box-shadow:0 4px 16px rgba(6,78,59,0.08);border-top:3px solid #f59e0b;">
            <div style="font-size:2rem;font-weight:900;color:#064e3b;">{stats['avg_confidence']}%</div>
            <div style="font-size:0.75rem;color:#6b7280;font-weight:600;text-transform:uppercase;">Avg Confidence</div></div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Crop breakdown
    col_left, col_right = st.columns(2)
    with col_left:
        st.markdown("### 🌾 Crop-wise Breakdown")
        crop_data = stats.get('crop_breakdown', {})
        if crop_data:
            emoji_map = {"potato": "🥔", "tomato": "🍅", "pepper": "🫑", "corn": "🌽"}
            for crop, count in crop_data.items():
                emoji = emoji_map.get(crop, "🌿")
                pct = (count / max(stats['total_scans'], 1)) * 100
                st.markdown(f"""
                <div style="background:white;border-radius:12px;padding:14px 18px;margin-bottom:8px;box-shadow:0 2px 8px rgba(0,0,0,0.04);display:flex;align-items:center;justify-content:space-between;">
                    <div style="display:flex;align-items:center;gap:10px;">
                        <span style="font-size:1.5rem;">{emoji}</span>
                        <span style="font-weight:700;color:#064e3b;">{crop.title()}</span>
                    </div>
                    <div style="text-align:right;">
                        <span style="font-weight:800;color:#064e3b;font-size:1.1rem;">{count}</span>
                        <span style="font-size:0.75rem;color:#6b7280;margin-left:4px;">({pct:.0f}%)</span>
                    </div>
                </div>""", unsafe_allow_html=True)
        else:
            st.info("Koi data nahi hai abhi.")

    with col_right:
        st.markdown("### 📅 Is Hafte Ki Activity")
        st.markdown(f"""
        <div style="background:white;border-radius:16px;padding:24px;box-shadow:0 4px 16px rgba(6,78,59,0.08);">
            <div style="font-size:3rem;font-weight:900;color:#064e3b;text-align:center;">{stats['weekly_scans']}</div>
            <div style="font-size:0.85rem;color:#6b7280;text-align:center;font-weight:600;">Scans pichle 7 din mein</div>
        </div>
        """, unsafe_allow_html=True)

    # Full scan history table
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### 📋 Full Scan History")
    history = get_scan_history()
    if history:
        for s in history:
            crop = s.get('crop_type', 'unknown')
            disease = s.get('predicted_disease', 'Unknown')
            conf = s.get('confidence', 0)
            date = str(s.get('created_at', ''))[:16]
            is_healthy = 'healthy' in disease.lower()
            color = "#059669" if is_healthy else "#dc2626"
            emoji_map = {"potato": "🥔", "tomato": "🍅", "pepper": "🫑", "corn": "🌽"}
            st.markdown(f"""
            <div style="background:white;border-radius:14px;padding:16px 20px;margin-bottom:8px;box-shadow:0 2px 8px rgba(0,0,0,0.04);border-left:4px solid {color};display:flex;align-items:center;justify-content:space-between;">
                <div style="display:flex;align-items:center;gap:12px;">
                    <span style="font-size:1.6rem;">{emoji_map.get(crop,'🌿')}</span>
                    <div>
                        <div style="font-weight:700;color:#064e3b;">{disease}</div>
                        <div style="font-size:0.75rem;color:#6b7280;">{crop.title()} · {date}</div>
                    </div>
                </div>
                <div style="background:{'#d1fae5' if is_healthy else '#fee2e2'};color:{color};padding:4px 14px;border-radius:20px;font-weight:700;font-size:0.82rem;">
                    {conf:.0f}%
                </div>
            </div>""", unsafe_allow_html=True)
    else:
        st.info("📭 Koi scan history nahi hai.")


# ==============================================================================
# 🛡️ ADMIN PANEL PAGE
# ==============================================================================
def render_admin_page():
    if not st.session_state.user or st.session_state.user.lower() != "admin":
        st.error("🚫 Access Denied — Sirf Admin access kar sakta hai!")
        return

    st.markdown("""
    <div style="background:linear-gradient(135deg,#fef3c7,#fde68a);border-radius:24px;padding:32px;margin-bottom:24px;border:1px solid rgba(245,158,11,0.3);">
        <h2 style="color:#92400e;font-weight:900;margin:0 0 6px;">🛡️ Admin Control Panel</h2>
        <p style="color:#78350f;margin:0;font-size:0.9rem;">Platform stats, user management aur scan analytics</p>
    </div>
    """, unsafe_allow_html=True)

    headers = {"Authorization": f"Bearer {st.session_state.token}"}

    # Fetch admin stats
    stats = None
    try:
        resp = requests.get(f"{API_URL}/admin/stats", headers=headers, timeout=15)
        if resp.status_code == 200:
            stats = resp.json()
        elif resp.status_code == 403:
            st.error("🚫 Admin access required! Dobara login karein — JWT mein purana role ho sakta hai.")
            return
        elif resp.status_code == 401:
            st.error("🔑 Session expire ho gaya. Logout karke dubara login karein.")
            return
        else:
            try:
                detail = resp.json().get("detail", resp.text)
            except Exception:
                detail = resp.text
            st.error(f"❌ Stats load nahi hui (HTTP {resp.status_code}): {detail}")
            return
    except requests.exceptions.RequestException as e:
        st.error(f"❌ Backend se connect nahi ho saka: {e}")
        return

    if not stats:
        st.warning("Stats load nahi hui — koi data nahi aaya.")
        return

    # Stats cards
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""<div style="background:linear-gradient(135deg,#059669,#10b981);border-radius:16px;padding:20px;text-align:center;color:white;">
            <div style="font-size:2.2rem;font-weight:900;">{stats['total_users']}</div>
            <div style="font-size:0.75rem;font-weight:600;opacity:0.85;text-transform:uppercase;">Total Users</div></div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""<div style="background:linear-gradient(135deg,#2563eb,#3b82f6);border-radius:16px;padding:20px;text-align:center;color:white;">
            <div style="font-size:2.2rem;font-weight:900;">{stats['total_scans']}</div>
            <div style="font-size:0.75rem;font-weight:600;opacity:0.85;text-transform:uppercase;">Total Scans</div></div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""<div style="background:linear-gradient(135deg,#d97706,#f59e0b);border-radius:16px;padding:20px;text-align:center;color:white;">
            <div style="font-size:2.2rem;font-weight:900;">{stats['today_scans']}</div>
            <div style="font-size:0.75rem;font-weight:600;opacity:0.85;text-transform:uppercase;">Today Scans</div></div>""", unsafe_allow_html=True)
    with c4:
        st.markdown(f"""<div style="background:linear-gradient(135deg,#dc2626,#ef4444);border-radius:16px;padding:20px;text-align:center;color:white;">
            <div style="font-size:2.2rem;font-weight:900;">{stats['pending_consultations']}</div>
            <div style="font-size:0.75rem;font-weight:600;opacity:0.85;text-transform:uppercase;">Pending Consults</div></div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Tabs for admin sections
    tab_users, tab_scans, tab_diseases = st.tabs(["👥 Users", "🔬 Scans", "📊 Analytics"])

    with tab_users:
        st.markdown("### 👥 User Management")
        try:
            resp = requests.get(f"{API_URL}/admin/users", headers=headers, timeout=5)
            if resp.status_code == 200:
                users = resp.json().get('users', [])
                for u in users:
                    role_color = {"admin": "#dc2626", "expert": "#2563eb", "farmer": "#059669"}.get(u['role'], '#6b7280')
                    active = "✅" if u.get('is_active', True) else "❌"
                    st.markdown(f"""
                    <div style="background:white;border-radius:14px;padding:14px 20px;margin-bottom:8px;box-shadow:0 2px 8px rgba(0,0,0,0.04);display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;">
                        <div style="display:flex;align-items:center;gap:12px;">
                            <div style="width:40px;height:40px;border-radius:50%;background:linear-gradient(135deg,#10b981,#059669);display:flex;align-items:center;justify-content:center;color:white;font-weight:800;">{(u.get('full_name') or '?')[0].upper()}</div>
                            <div>
                                <div style="font-weight:700;color:#064e3b;">{u['full_name']} {active}</div>
                                <div style="font-size:0.75rem;color:#6b7280;">{u['email']} · {u.get('scan_count',0)} scans</div>
                            </div>
                        </div>
                        <span style="background:{role_color};color:white;padding:4px 14px;border-radius:20px;font-weight:700;font-size:0.72rem;text-transform:uppercase;">{u['role']}</span>
                    </div>""", unsafe_allow_html=True)

                # Role change section
                st.markdown("---")
                st.markdown("#### 🔄 Change User Role")
                user_emails = [u['email'] for u in users]
                sel_email = st.selectbox("User select karein:", user_emails, key="admin_role_email")
                sel_user = next((u for u in users if u['email'] == sel_email), None)
                new_role = st.selectbox("Naya role:", ["farmer", "expert", "admin"], key="admin_new_role")
                if st.button("🔄 Role Change Karein", type="primary", key="admin_role_btn"):
                    if sel_user:
                        resp = requests.put(f"{API_URL}/admin/users/{sel_user['id']}/role",
                            headers=headers, json={"role": new_role}, timeout=5)
                        if resp.status_code == 200:
                            st.success(f"✅ {sel_email} ka role {new_role} ho gaya!")
                            time.sleep(0.5)
                            st.rerun()
                        else:
                            st.error(f"❌ {resp.json().get('detail','Error')}")
        except Exception as e:
            st.error(f"❌ Users load nahi hui: {e}")

    with tab_scans:
        st.markdown("### 🔬 Recent Scans (All Users)")
        try:
            resp = requests.get(f"{API_URL}/admin/scans?limit=30", headers=headers, timeout=5)
            if resp.status_code == 200:
                scans = resp.json().get('scans', [])
                for s in scans:
                    disease = s.get('predicted_disease', 'Unknown')
                    is_healthy = 'healthy' in disease.lower()
                    color = "#059669" if is_healthy else "#dc2626"
                    st.markdown(f"""
                    <div style="background:white;border-radius:12px;padding:12px 18px;margin-bottom:6px;box-shadow:0 2px 6px rgba(0,0,0,0.03);border-left:3px solid {color};display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:6px;">
                        <div>
                            <span style="font-weight:700;color:#064e3b;">{disease}</span>
                            <span style="color:#6b7280;font-size:0.8rem;"> · {s.get('crop_type','?').title()}</span>
                        </div>
                        <div style="font-size:0.75rem;color:#6b7280;">
                            {s.get('full_name','?')} · {s.get('confidence',0):.0f}% · {str(s.get('created_at',''))[:16]}
                        </div>
                    </div>""", unsafe_allow_html=True)
            else:
                st.warning("Scans load nahi hui.")
        except Exception as e:
            st.error(f"❌ Error: {e}")

    with tab_diseases:
        st.markdown("### 📊 Platform Analytics")
        # Crop distribution
        crops = stats.get('scans_by_crop', {})
        if crops:
            st.markdown("#### 🌾 Crop Distribution")
            for crop, cnt in sorted(crops.items(), key=lambda x: -x[1]):
                pct = (cnt / max(stats['total_scans'], 1)) * 100
                bar_width = max(pct, 5)
                st.markdown(f"""
                <div style="margin-bottom:8px;">
                    <div style="display:flex;justify-content:space-between;margin-bottom:3px;">
                        <span style="font-weight:700;color:#064e3b;font-size:0.85rem;">{crop.title()}</span>
                        <span style="color:#6b7280;font-size:0.8rem;">{cnt} ({pct:.0f}%)</span>
                    </div>
                    <div style="background:#e5e7eb;border-radius:8px;height:8px;overflow:hidden;">
                        <div style="background:linear-gradient(90deg,#10b981,#059669);width:{bar_width}%;height:100%;border-radius:8px;"></div>
                    </div>
                </div>""", unsafe_allow_html=True)

        # Top diseases
        diseases = stats.get('top_diseases', {})
        if diseases:
            st.markdown("#### 🦠 Top Diseases Detected")
            for disease, cnt in diseases.items():
                st.markdown(f"""
                <div style="background:#fee2e2;border-radius:10px;padding:10px 16px;margin-bottom:6px;display:flex;justify-content:space-between;align-items:center;">
                    <span style="font-weight:700;color:#991b1b;">{disease}</span>
                    <span style="background:#dc2626;color:white;padding:2px 12px;border-radius:14px;font-weight:700;font-size:0.8rem;">{cnt}</span>
                </div>""", unsafe_allow_html=True)

        # Role distribution
        roles = stats.get('users_by_role', {})
        if roles:
            st.markdown("#### 👥 Users by Role")
            for role, cnt in roles.items():
                st.markdown(f"- **{role.title()}**: {cnt} users")


# ===================== HOME PAGE =====================
if nav == "🏠 Home Page":
    render_persistent_header()
    # ==============================================================================
    # 🔥 FIX #2: COMPACT LOGGED IN USER BADGE - TOP RIGHT CORNER
    # ==============================================================================
    col_user_left, col_user_right = st.columns([6, 1])
    with col_user_right:
        st.markdown(f"""
        <div style="display:flex;align-items:center;justify-content:flex-end;gap:8px;margin-bottom:10px;">
            <div style="background:linear-gradient(135deg,#059669,#10b981);color:white;padding:6px 14px;border-radius:20px;font-size:0.78rem;font-weight:700;display:flex;align-items:center;gap:6px;box-shadow:0 2px 8px rgba(16,185,129,0.3);">
                <span>👤</span>
                <span>{st.session_state.user_email}</span>
                <span style="background:rgba(255,255,255,0.25);padding:2px 8px;border-radius:10px;font-size:0.65rem;">{st.session_state.user or "Farmer"}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)



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
        <div class="stat-card" style="animation-delay:0.1s"><div class="stat-val">97%</div><div class="stat-lbl">Accuracy</div></div>
        <div class="stat-card" style="animation-delay:0.2s"><div class="stat-val">18K+</div><div class="stat-lbl">Images Trained</div></div>
        <div class="stat-card" style="animation-delay:0.3s"><div class="stat-val">4</div><div class="stat-lbl">Crops</div></div>
        <div class="stat-card" style="animation-delay:0.4s"><div class="stat-val">&lt;3s</div><div class="stat-lbl">Result Time</div></div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([2, 1])
    with col1:
                st.markdown("""
        <div class="slider-container">
            <div class="slide-track">
                <!-- 🔥 FIX #4: ZYADA AUR BEHTREEN PICTURES -->
                <div class="slide"><img src="https://images.unsplash.com/photo-1500382017468-9049fed747ef?w=800&q=80"></div>
                <div class="slide"><img src="https://images.unsplash.com/photo-1625246333195-78d9c38ad449?w=800&q=80"></div>
                <div class="slide"><img src="https://images.unsplash.com/photo-1592982537447-6f2a6a0c7c18?w=800&q=80"></div>
                <div class="slide"><img src="https://images.unsplash.com/photo-1464226184884-fa280b87c399?w=800&q=80"></div>
                <div class="slide"><img src="https://images.unsplash.com/photo-1416879595882-3373a0480b5b?w=800&q=80"></div>
                <div class="slide"><img src="https://images.unsplash.com/photo-1500937386664-56d1dfef3854?w=800&q=80"></div>
                <div class="slide"><img src="https://images.unsplash.com/photo-1592419044706-39796d40f98c?w=800&q=80"></div>
                <div class="slide"><img src="https://images.unsplash.com/photo-1574323347407-f5e1ad6d020b?w=800&q=80"></div>
                <div class="slide"><img src="https://images.unsplash.com/photo-1591857177580-dc82b9ac4e1e?w=800&q=80"></div>
                <div class="slide"><img src="https://images.unsplash.com/photo-1560493676-04071c5f467b?w=800&q=80"></div>
                <div class="slide"><img src="https://images.unsplash.com/photo-1586771107445-d3ca888129ff?w=800&q=80"></div>
                <div class="slide"><img src="https://images.unsplash.com/photo-1530836369250-ef72a3f5cda8?w=800&q=80"></div>
                <!-- Duplicate for infinite scroll -->
                <div class="slide"><img src="https://images.unsplash.com/photo-1500382017468-9049fed747ef?w=800&q=80"></div>
                <div class="slide"><img src="https://images.unsplash.com/photo-1625246333195-78d9c38ad449?w=800&q=80"></div>
                <div class="slide"><img src="https://images.unsplash.com/photo-1592982537447-6f2a6a0c7c18?w=800&q=80"></div>
                <div class="slide"><img src="https://images.unsplash.com/photo-1464226184884-fa280b87c399?w=800&q=80"></div>
                <div class="slide"><img src="https://images.unsplash.com/photo-1416879595882-3373a0480b5b?w=800&q=80"></div>
                <div class="slide"><img src="https://images.unsplash.com/photo-1500937386664-56d1dfef3854?w=800&q=80"></div>
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

    st.markdown("""
    <div class="scan-cta-wrap">
        <p style="color:rgba(255,255,255,0.65);font-size:0.75rem;font-weight:700;letter-spacing:3px;text-transform:uppercase;margin-bottom:10px;">🔬 Quick Scan</p>
        <h2 style="color:white;font-size:1.9rem;font-weight:900;margin:0 0 10px;letter-spacing:-0.5px;">Koi bhi fasal — ek hi jagah scan karein</h2>
        <p style="color:rgba(255,255,255,0.7);font-size:0.95rem;max-width:500px;margin:0 auto 24px;line-height:1.6;">Seedha yahan patta upload karein — AI khud crop detect karega</p>
    </div>
    """, unsafe_allow_html=True)

    # Universal upload zone — AI auto-detects crop
    uploaded_file, detected_crop = render_universal_upload()
    if uploaded_file and detected_crop:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(f"<h3 style='color:#064e3b;font-weight:800;'>📊 {detected_crop.title()} Analysis Result</h3>", unsafe_allow_html=True)
        with st.spinner("🔬 Analyzing..."):
            result = analyze_image(uploaded_file, detected_crop)
        if result:
            ai_advice = show_result(result, detected_crop, CROP_CONFIG[detected_crop])
            # ==============================================================================
            # 🔥 UNIVERSAL SCAN SAVE (NEW)
            # ==============================================================================
            with st.spinner("💾 Scan database mein save ho raha hai..."):
                success, msg = save_scan_to_backend(
                    uploaded_file, 
                    detected_crop, 
                    result['label'], 
                    result['conf'],
                    ai_advice=ai_advice,
                )
                if success:
                    st.success("Scan history mein save ho gaya!")
                    st.rerun()
                else:
                    st.error(f"Scan save nahi hua: {msg}")

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


# ===================== PROFILE PAGE =====================
elif nav == "👤 My Profile":
    render_persistent_header()
    render_profile_page()


# ===================== DASHBOARD PAGE =====================
elif nav == "📊 Dashboard":
    render_persistent_header()
    render_dashboard_page()


# ===================== EXPERT CHAT PAGE =====================
elif nav == "💬 Expert Chat":
    render_persistent_header()
    
    st.markdown("""
    <div style="background:linear-gradient(135deg,#e0f2fe,#bae6fd);border-radius:24px;padding:32px;margin-bottom:24px;border:1px solid rgba(14,165,233,0.3);">
        <h2 style="color:#0369a1;font-weight:900;margin:0 0 6px;">💬 Expert Consultations</h2>
        <p style="color:#0c4a6e;margin:0;font-size:0.9rem;">Kisan aur Agricultural Experts ke darmiyan rabta</p>
    </div>
    """, unsafe_allow_html=True)

    headers = {"Authorization": f"Bearer {st.session_state.token}"}
    try:
        resp = requests.get(f"{API_URL}/consultations", headers=headers, timeout=5)
        if resp.status_code == 200:
            consults = resp.json().get('consultations', [])
            
            if not consults:
                st.info("📭 Abhi koi consultation nahi hai.")
            else:
                for c in consults:
                    status_color = "#10b981" if c['status'] == 'resolved' else "#f59e0b"
                    status_text = "Resolved" if c['status'] == 'resolved' else "Pending"
                    
                    st.markdown(f"""
                    <div style="background:white;border-radius:16px;padding:20px;margin-bottom:12px;box-shadow:0 4px 16px rgba(0,0,0,0.05);border-left:4px solid {status_color};">
                        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
                            <div>
                                <span style="font-weight:800;color:#0369a1;font-size:1.1rem;">{c.get('crop_type', '').title()} · {c.get('predicted_disease', '')}</span>
                                <div style="font-size:0.75rem;color:#6b7280;margin-top:2px;">{str(c.get('created_at', ''))[:16]}</div>
                            </div>
                            <span style="background:{status_color}20;color:{status_color};padding:4px 12px;border-radius:12px;font-weight:800;font-size:0.7rem;text-transform:uppercase;">{status_text}</span>
                        </div>
                        
                        <div style="background:#f8fafc;padding:12px 16px;border-radius:12px;margin-bottom:10px;">
                            <div style="font-size:0.7rem;font-weight:700;color:#64748b;margin-bottom:4px;text-transform:uppercase;">👨‍🌾 {c.get('farmer_name', 'Kisan')} ka Sawal:</div>
                            <div style="color:#334155;font-size:0.95rem;">{c['message']}</div>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    if c['status'] == 'resolved':
                        st.markdown(f"""
                        <div style="background:#ecfdf5;padding:12px 16px;border-radius:12px;border:1px solid #a7f3d0;">
                            <div style="font-size:0.7rem;font-weight:700;color:#059669;margin-bottom:4px;text-transform:uppercase;">👨‍⚕️ Expert ka Jawab:</div>
                            <div style="color:#064e3b;font-size:0.95rem;">{c['expert_reply']}</div>
                        </div>
                        """, unsafe_allow_html=True)
                    elif st.session_state.user and st.session_state.user.lower() in ['expert', 'admin']:
                        # Expert can reply
                        reply_msg = st.text_area("Aap ka Jawab:", key=f"reply_{c['id']}")
                        if st.button("📤 Jawab Bhejein", key=f"btn_{c['id']}", type="primary"):
                            if reply_msg.strip():
                                r_resp = requests.put(f"{API_URL}/consultations/{c['id']}/reply", headers=headers, json={"reply": reply_msg})
                                if r_resp.status_code == 200:
                                    st.toast("✅ Jawab bhej diya gaya!", icon="📤")
                                    time.sleep(0.5)
                                    st.rerun()
                                else:
                                    st.error("Error sending reply")
                            else:
                                st.warning("Jawab likhein")
                    
                    st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.error("❌ Failed to load consultations")
    except Exception as e:
        st.error(f"❌ Backend error: {e}") 

# ===================== ADMIN PANEL =====================
elif nav == "🛡️ Admin Panel":
    render_persistent_header()
    render_admin_page() 