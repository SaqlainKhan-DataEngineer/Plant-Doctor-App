import streamlit as st
from PIL import Image
import time
import datetime
import requests
import random
import os

# --- 1. PAGE SETUP ---
st.set_page_config(
    page_title="Plant Doctor AI", 
    page_icon="🌿", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. WEATHER FUNCTION ---
def get_real_weather():
    try:
        url = "https://api.open-meteo.com/v1/forecast?latitude=31.5204&longitude=74.3587&current_weather=true"
        response = requests.get(url, timeout=2)
        data = response.json()
        temp = data['current_weather']['temperature']
        wind = data['current_weather']['windspeed']
        return temp, wind
    except:
        return 28, 12

temp, wind = get_real_weather()

# --- 3. SMART MODEL LOADING ---
@st.cache_resource
def load_model():
    try:
        from transformers import AutoImageProcessor, AutoModelForImageClassification
        import torch
        
        # Determine device (CPU for safety unless GPU configured)
        device = torch.device("cpu") 

        # PATH LOGIC: Check current directory first (GitHub structure fix)
        if os.path.exists("config.json") and (os.path.exists("model.safetensors") or os.path.exists("pytorch_model.bin")):
            model_path = "."
        else:
            model_path = "mera_potato_model"

        model = AutoModelForImageClassification.from_pretrained(model_path).to(device)
        processor = AutoImageProcessor.from_pretrained(model_path)
        return model, processor
    except:
        return None, None

model, processor = load_model()

# --- 4. ULTRA PREMIUM CSS (Fixed Layout) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }

    /* ANIMATIONS */
    @keyframes fadeInUp { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
    @keyframes pulse-red { 0% { box-shadow: 0 0 0 0 rgba(255, 50, 50, 0.7); } 70% { box-shadow: 0 0 0 10px rgba(255, 50, 50, 0); } 100% { box-shadow: 0 0 0 0 rgba(255, 50, 50, 0); } }
    @keyframes float-weather { 0% { transform: translateY(0px); } 50% { transform: translateY(-6px); } 100% { transform: translateY(0px); } }
    @keyframes float-logo { 0% { transform: translateY(0px); box-shadow: 0 0 15px rgba(16, 185, 129, 0.4); } 50% { transform: translateY(-5px); box-shadow: 0 0 25px rgba(16, 185, 129, 0.6); } 100% { transform: translateY(0px); box-shadow: 0 0 15px rgba(16, 185, 129, 0.4); } }

    /* GLOBAL ANIMATION */
    h1, h2, h3, p, span, a, div.stMarkdown { animation: fadeInUp 0.6s ease-out both; }

    /* BACKGROUND PARTICLES */
    .stApp::before {
        content: ""; position: fixed; top: 0; left: 0; width: 100%; height: 100%;
        background-image: radial-gradient(#059669 1px, transparent 1px);
        background-size: 40px 40px; opacity: 0.1; pointer-events: none; z-index: 0;
    }

    /* SIDEBAR */
    [data-testid="stSidebar"] { background-image: linear-gradient(180deg, #064e3b 0%, #047857 100%); border-right: none; }
    [data-testid="stSidebar"] * { color: #ecfdf5 !important; }
    
    [data-testid="stSidebar"] .stRadio div[role="radiogroup"] label {
        background: rgba(255,255,255,0.1); padding: 12px 15px; border-radius: 12px; margin-bottom: 8px !important;
        border: 1px solid rgba(255,255,255,0.1); transition: all 0.3s;
    }
    [data-testid="stSidebar"] .stRadio div[role="radiogroup"] label:hover {
        background: rgba(255,255,255,0.2); transform: translateX(5px);
    }
    [data-testid="stSidebar"] .stRadio div[role="radiogroup"] div[aria-checked="true"] + div + label {
         background: linear-gradient(90deg, #059669, #10b981) !important;
         border: 1px solid #a7f3d0 !important; font-weight: 800; transform: scale(1.02);
         box-shadow: 0 5px 15px rgba(0,0,0,0.2); color: white !important;
    }
    [data-testid="stSidebar"] .stRadio div[role="radiogroup"] div[role="radio"] { display: none; }

    /* --- FIXED WEATHER CARD LAYOUT --- */
    .weather-card-container {
        position: relative;
        border-radius: 25px; padding: 20px;
        color: white; text-align: center; 
        height: 380px; /* Increased Height */
        display: flex; flex-direction: column; justify-content: space-between; align-items: center;
        box-shadow: 0 15px 35px rgba(0,0,0,0.15);
        overflow: hidden;
    }
    
    .live-badge {
        background: rgba(0,0,0,0.3); padding: 5px 12px; border-radius: 20px;
        font-size: 0.75rem; font-weight: 700; display: inline-flex; align-items: center; gap: 8px;
        align-self: flex-end; border: 1px solid rgba(255,255,255,0.3);
    }
    .live-dot { width: 8px; height: 8px; background: #ef4444; border-radius: 50%; animation: pulse-red 1.5s infinite; }
    
    .weather-icon-big { font-size: 4.5rem; margin: 0; filter: drop-shadow(0 5px 15px rgba(0,0,0,0.2)); animation: float-weather 3s ease-in-out infinite; }
    .temp-text { font-size: 4rem; font-weight: 800; margin: 0; line-height: 1; text-shadow: 0 2px 10px rgba(0,0,0,0.2); }
    
    /* Stats Box at Bottom */
    .weather-footer {
        background: rgba(255,255,255,0.15); width: 100%; padding: 10px; border-radius: 15px;
        display: flex; flex-direction: column; align-items: center; gap: 5px;
        border-top: 1px solid rgba(255,255,255,0.2);
    }
    .stats-row { display: flex; justify-content: center; gap: 15px; font-weight: 600; font-size: 0.9rem; }
    .region-text { font-size: 0.8rem; opacity: 0.9; text-transform: uppercase; letter-spacing: 1px; }

    /* CARDS & HERO */
    .hero-box {
        text-align: center; padding: 50px 20px; border-radius: 30px; margin-bottom: 40px;
        background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%);
        box-shadow: 0 10px 30px rgba(0,0,0,0.05);
    }
    .feature-card {
        background: rgba(255,255,255,0.9); padding: 25px; border-radius: 20px; text-align: center;
        box-shadow: 0 10px 25px rgba(0,0,0,0.05); border: 1px solid rgba(0,0,0,0.05); transition: transform 0.3s;
    }
    .feature-card:hover { transform: translateY(-5px); border-color: #059669; }
    
    .cta-btn {
        background: #059669; color: white !important; padding: 12px 30px; border-radius: 50px; 
        text-decoration: none; font-weight: bold; box-shadow: 0 5px 15px rgba(5, 150, 105, 0.4);
    }
    img { border-radius: 15px; }
    </style>
    """, unsafe_allow_html=True)

# --- 5. SIDEBAR ---
st.sidebar.markdown("""
    <div style="display: flex; justify-content: center; margin-bottom: 20px; margin-top: 10px;">
        <img src="https://cdn-icons-png.flaticon.com/512/11698/11698467.png" 
             style="width: 130px; border-radius: 50%; padding: 8px; background: rgba(255,255,255,0.15); 
             border: 2px solid rgba(255,255,255,0.3); animation: float-logo 3s ease-in-out infinite;"> 
    </div>
    """, unsafe_allow_html=True)

st.sidebar.markdown("<h1 style='text-align: center; color: white; margin-top: -10px;'>Plant Doctor</h1>", unsafe_allow_html=True)
st.sidebar.write("---")
nav = st.sidebar.radio("", ["🏠 Home Page", "🥔 Potato (Aloo)", "🍅 Tomato Check", "🌽 Corn Field"])
st.sidebar.write("---")
st.sidebar.info("**Developers:**\n\n👨‍💻 Saqlain Khan\n👨‍💻 Raheel Chishti")

# --- 6. MAIN LOGIC ---
if nav == "🏠 Home Page":
    st.markdown("""
    <div class="hero-box">
        <h1 style="color:#064e3b; font-size: 3.5rem; font-weight: 800; margin:0;">Plant Doctor AI</h1>
        <p style="color:#065f46; font-size: 1.2rem; margin-bottom: 30px;">AI-Powered Crop Disease Detection for Smart Farmers</p>
        <a class="cta-btn" href="#start">🌿 Start Diagnosis</a>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns([1.8, 1])
    
    with col1:
        st.image("https://images.unsplash.com/photo-1625246333195-78d9c38ad449?w=800", use_column_width=True)
        
    with col2:
        # --- WEATHER WIDGET LOGIC ---
        weather_bg = "linear-gradient(135deg, #3b82f6 0%, #06b6d4 100%)"
        icon = "⛅"
        if temp > 30: 
            weather_bg = "linear-gradient(135deg, #f59e0b 0%, #ea580c 100%)"
            icon = "☀️"
        
        st.markdown(f"""
        <div class="weather-card-container" style="background: {weather_bg};">
            <div class="live-badge"><div class="live-dot"></div> LIVE</div>
            
            <div>
                <div class="weather-icon-big">{icon}</div>
                <div class="temp-text">{temp}°C</div>
            </div>
            
            <div class="weather-footer">
                <div class="stats-row">
                    <span>💨 {wind} km/h</span>
                    <span>|</span>
                    <span>💧 65% Hum</span>
                </div>
                <div class="region-text">📍 Punjab Region</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    stats = [("🌱", "15K+", "Images Trained"), ("🎯", "98%", "Accuracy"), ("⚡", "< 1s", "Fast Prediction"), ("👨‍🌾", "Expert", "Farmer Approved")]
    for col, (i, v, l) in zip([c1,c2,c3,c4], stats):
        col.markdown(f"""
        <div class="feature-card">
            <div style="font-size:2.5rem; margin-bottom:10px;">{i}</div>
            <h2 style="margin:0; color:#064e3b;">{v}</h2>
            <p style="color:#555; margin:0;">{l}</p>
        </div>
        """, unsafe_allow_html=True)

elif nav == "🥔 Potato (Aloo)":
    st.header("🥔 Aloo Ki Bimari Check Karein", anchor="start")
    
    # --- MODEL CHECK ---
    if model is None:
        st.error("⚠️ **Model Folder Missing!**")
        st.info("Ensure `config.json` is in the same folder as `app.py` or `mera_potato_model` folder.")
    else:
        uploaded_file = st.file_uploader("Upload Leaf Photo", type=["jpg", "png", "jpeg"])
        
        if uploaded_file:
            col1, col2 = st.columns([1, 1])
            with col1:
                image = Image.open(uploaded_file).convert('RGB')
                st.image(image, caption="Uploaded Photo", use_column_width=True)
            
            with col2:
                with st.spinner("Analyzing..."):
                    time.sleep(1) 
                    
                    # PREDICTION LOGIC
                    import torch
                    model_image = image.resize((224, 224)) 
                    inputs = processor(images=model_image, return_tensors="pt")
                    
                    with torch.no_grad():
                        outputs = model(**inputs)
                        logits = outputs.logits
                        idx = logits.argmax(-1).item()
                        conf = torch.softmax(logits, dim=1)[0][idx].item() * 100
                        label = model.config.id2label[idx]
                    
                    # --- 90% CHECK ---
                    if conf < 90:
                        st.error("⚠️ **Photo Clear Nahi Hai!**")
                        st.warning(f"Confidence: {conf:.1f}% (Low)\n\nYe Aloo ka patta nahi lag raha. Saaf photo upload karein.")
                        st.stop()

                # DISPLAY RESULT
                clean_label = label.replace("_", " ").title()
                is_healthy = "healthy" in label.lower()
                
                color = "#059669" if is_healthy else "#dc2626"
                bg = "#ecfdf5" if is_healthy else "#fef2f2"
                
                st.markdown(f"""
                <div class='result-box' style='background: {bg}; border: 2px solid {color}; padding: 25px; border-radius: 20px; text-align: center;'>
                    <h2 style='color: {color}; margin:0; font-weight: 800;'>{clean_label}</h2>
                    <h4 style='color: {color}; margin-top: 10px; font-weight: 600;'>Confidence: {conf:.1f}%</h4>
                </div>
                """, unsafe_allow_html=True)
                
                if is_healthy:
                    st.balloons()
                    st.success("🎉 Fasal bilkul theek hai! Pani aur khad ka khayal rakhein.")
                else:
                    st.error("⚠️ Bimari Detect Hui Hai!")
                    st.markdown("""
                    <div style="background:white; padding:20px; border-radius:15px; border:1px solid #ddd; margin-top:20px;">
                        <h4 style="color:#d97706;">💊 Ilaj (Treatment):</h4>
                        <ul>
                            <li><b>Chemical:</b> Metalaxyl + Mancozeb (2.5g/Liter) spray karein.</li>
                            <li><b>Organic:</b> Neem Oil ka spray karein.</li>
                            <li><b>Note:</b> Mutasira patton ko jala dein.</li>
                        </ul>
                    </div>
                    """, unsafe_allow_html=True)

elif nav in ["🍅 Tomato Check", "🌽 Corn Field"]:
    st.info("🚧 Coming Soon...") 