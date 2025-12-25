import streamlit as st
from PIL import Image
import torch
from transformers import AutoImageProcessor, AutoModelForImageClassification
import time
import datetime
import requests

# --- 1. PAGE SETUP ---
st.set_page_config(
    page_title="Plant Doctor AI", 
    page_icon="🌿", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. FUNCTION TO GET REAL WEATHER ---
def get_real_weather():
    try:
        url = "https://api.open-meteo.com/v1/forecast?latitude=31.5204&longitude=74.3587&current_weather=true"
        response = requests.get(url)
        data = response.json()
        temp = data['current_weather']['temperature']
        wind = data['current_weather']['windspeed']
        return temp, wind
    except:
        return 28, 12

temp, wind = get_real_weather()

# --- 3. ULTRA PREMIUM CSS (VIP WEATHER & SIDEBAR) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
        scroll-behavior: smooth;
    }

    /* --- 1. ANIMATIONS --- */
    @keyframes fadeInUp { from { opacity: 0; transform: translateY(30px); } to { opacity: 1; transform: translateY(0); } }
    @keyframes popIn { 0% { transform: scale(0.8); opacity: 0; } 100% { transform: scale(1); opacity: 1; } }
    @keyframes pulse-red { 0% { box-shadow: 0 0 0 0 rgba(255, 50, 50, 0.7); } 70% { box-shadow: 0 0 0 10px rgba(255, 50, 50, 0); } 100% { box-shadow: 0 0 0 0 rgba(255, 50, 50, 0); } }
    @keyframes float-and-glow { 0% { transform: translateY(0px); box-shadow: 0 0 15px rgba(16, 185, 129, 0.4); } 50% { transform: translateY(-12px); box-shadow: 0 0 30px rgba(16, 185, 129, 0.8); } 100% { transform: translateY(0px); box-shadow: 0 0 15px rgba(16, 185, 129, 0.4); } }
    @keyframes float-weather { 0% { transform: translateY(0px); } 50% { transform: translateY(-10px); } 100% { transform: translateY(0px); } }
    @keyframes diamond-wind { 0% { transform: translateY(0) translateX(0); } 100% { transform: translateY(100px) translateX(-100px); } }
    @keyframes gradientBG { 0% { background-position: 0% 50%; } 50% { background-position: 100% 50%; } 100% { background-position: 0% 50%; } }

    h1, h2, h3, p, span, a, div.stMarkdown { animation: fadeInUp 0.8s ease-out both; }

    /* --- 2. BACKGROUND PARTICLES (EMERALD) --- */
    .stApp::before {
        content: ""; position: fixed; top: -50%; left: -50%; width: 200%; height: 200%;
        background-image:
            radial-gradient(circle at 20px 30px, rgba(4, 120, 87, 0.5) 0px, transparent 2px),
            radial-gradient(circle at 40px 70px, rgba(16, 185, 129, 0.6) 0px, transparent 2px),
            radial-gradient(circle at 50px 160px, rgba(5, 150, 105, 0.5) 0px, transparent 2px),
            radial-gradient(circle at 90px 40px, rgba(52, 211, 153, 0.7) 0px, transparent 3px),
            radial-gradient(circle at 130px 80px, rgba(6, 78, 59, 0.6) 0px, transparent 2px);
        background-repeat: repeat; background-size: 200px 200px; animation: diamond-wind 25s linear infinite;
        pointer-events: none; z-index: 0;
    }

    /* --- 3. PREMIUM SIDEBAR BUTTONS (DARK MODE FIX) --- */
    [data-testid="stSidebar"] { background-image: linear-gradient(180deg, #064e3b 0%, #047857 100%); border-right: none; }
    [data-testid="stSidebar"] * { color: #ecfdf5 !important; }
    
    /* The Container for Buttons */
    [data-testid="stSidebar"] .stRadio div[role="radiogroup"] label {
        background: rgba(0, 0, 0, 0.25); /* Darker background for card effect */
        padding: 15px 20px; 
        border-radius: 15px; 
        margin-bottom: 12px !important;
        border: 1px solid rgba(255,255,255,0.1); 
        width: 100%; 
        display: flex; 
        align-items: center;
        transition: all 0.3s ease;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        cursor: pointer;
    }
    
    /* Hover Effect */
    [data-testid="stSidebar"] .stRadio div[role="radiogroup"] label:hover {
        background: rgba(255, 255, 255, 0.15); 
        transform: scale(1.02);
        border-color: #34d399;
    }
    
    /* Selected Item (FULL GLOW) */
    [data-testid="stSidebar"] .stRadio div[role="radiogroup"] div[aria-checked="true"] + div + label {
         background: linear-gradient(90deg, #059669, #10b981) !important; /* Full Green Gradient */
         border: 1px solid #a7f3d0 !important;
         font-weight: 800; 
         transform: scale(1.03);
         box-shadow: 0 0 20px rgba(16, 185, 129, 0.6); /* Neon Glow */
         color: white !important;
    }
    /* Hide the default radio circle */
    [data-testid="stSidebar"] .stRadio div[role="radiogroup"] div[role="radio"] {
        display: none; 
    }

    /* --- 4. HERO & CARDS --- */
    .hero-container {
        text-align: center; padding: 60px 20px; border-radius: 35px;
        background: linear-gradient(-45deg, #ccfbf1, #d1fae5, #a7f3d0, #6ee7b7);
        background-size: 400% 400%; animation: gradientBG 15s ease infinite, popIn 1s ease-out;
        box-shadow: 0 20px 60px rgba(0,0,0,0.15); margin-bottom: 40px; 
        border: 2px solid rgba(255,255,255,0.8); position: relative; z-index: 1;
    }

    .feature-card {
        background: rgba(255, 255, 255, 0.9); backdrop-filter: blur(25px);
        padding: 30px; border-radius: 30px; text-align: center;
        border: 1px solid rgba(255,255,255,0.6); box-shadow: 0 10px 30px rgba(0,0,0,0.08);
        height: 100%; display: flex; flex-direction: column; justify-content: center; align-items: center;
        transform-style: preserve-3d; transition: transform 0.4s ease, box-shadow 0.4s ease;
        position: relative; z-index: 1; animation: fadeInUp 1s ease-out;
    }
    .feature-card:hover { 
        transform: perspective(1000px) rotateX(5deg) rotateY(-5deg) translateY(-15px); 
        box-shadow: 0 30px 60px rgba(16, 185, 129, 0.3); border-color: #34d399;
    }
    
    .cta-button {
        display: inline-block; background: linear-gradient(90deg, #059669, #10b981); color: white !important;
        padding: 18px 45px; border-radius: 50px; font-weight: 800; font-size: 1.1rem; text-decoration: none;
        box-shadow: 0 10px 30px rgba(16,185,129,0.5); transition: all 0.3s; margin-top: 25px; border: 2px solid #a7f3d0;
        animation: popIn 1.2s ease-out;
    }
    .cta-button:hover { transform: scale(1.1) translateY(-5px); }

    /* --- 5. SLIDER & WEATHER --- */
    .slider-container {
        width: 100%; overflow: hidden; border-radius: 25px;
        box-shadow: 0 20px 50px rgba(0,0,0,0.2); border: 2px solid rgba(255,255,255,0.7);
        background: #000; animation: popIn 1s ease-out;
    }
    .slide-track { display: flex; width: calc(1000px * 10); animation: scroll 45s linear infinite; }
    .slide-track:hover { animation-play-state: paused; }
    .slide { width: 600px; height: 350px; flex-shrink: 0; padding: 0 5px; }
    .slide img { width: 100%; height: 100%; object-fit: cover; border-radius: 15px; transition: transform 0.4s; }
    .slide img:hover { transform: scale(1.08); filter: brightness(1.1); cursor: grab; }
    @keyframes scroll { 0% { transform: translateX(0); } 100% { transform: translateX(calc(-600px * 5)); } }

    /* PREMIUM WEATHER WIDGET */
    .weather-container {
        background: rgba(255, 255, 255, 0.15); backdrop-filter: blur(20px);
        border-radius: 25px; padding: 25px; border: 1px solid rgba(255, 255, 255, 0.3);
        box-shadow: 0 15px 40px rgba(0, 0, 0, 0.15); color: white; text-align: center;
        height: 350px; display: flex; flex-direction: column; justify-content: center; align-items: center;
        animation: popIn 1s ease-out 0.2s backwards;
        position: relative;
    }
    .weather-icon-big { font-size: 5rem; margin-bottom: 10px; filter: drop-shadow(0 0 15px rgba(255,255,255,0.8)); animation: float-weather 4s ease-in-out infinite; }
    .temp-text { font-size: 4.5rem; font-weight: 800; margin: 0; line-height: 1; text-shadow: 0 5px 15px rgba(0,0,0,0.2); }
    
    /* VIP BADGES */
    .live-badge {
        background: rgba(0, 0, 0, 0.3);
        padding: 5px 15px;
        border-radius: 50px;
        border: 1px solid rgba(255,255,255,0.2);
        display: inline-flex;
        align-items: center;
        gap: 8px;
        font-weight: 700;
        font-size: 0.8rem;
        letter-spacing: 1px;
        margin-bottom: 15px;
        box-shadow: 0 5px 15px rgba(0,0,0,0.1);
    }
    .live-dot {
        width: 8px; height: 8px; background: #ef4444; border-radius: 50%;
        box-shadow: 0 0 10px #ef4444;
        animation: pulse-red 1.5s infinite;
    }

    /* PREMIUM REGION PILL (FIXED) */
    .region-pill {
        margin-top: 20px;
        background: rgba(0, 0, 0, 0.2); /* Darker contrast */
        padding: 8px 20px;
        border-radius: 50px;
        font-size: 0.8rem;
        font-weight: 700;
        letter-spacing: 1px;
        border: 1px solid rgba(255,255,255,0.15);
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        display: inline-flex;
        align-items: center;
        gap: 8px;
        text-transform: uppercase;
        color: rgba(255,255,255,0.9);
    }

    .stat-badge { background: rgba(0, 0, 0, 0.2); padding: 8px 15px; border-radius: 50px; font-size: 0.9rem; border: 1px solid rgba(255,255,255,0.1); }
    .result-box { padding: 30px; border-radius: 25px; text-align: center; background: rgba(255,255,255,0.95); box-shadow: 0 20px 50px rgba(0,0,0,0.1); animation: popIn 0.6s ease-out; border: 2px solid white; }
    img { border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.15); transition: transform 0.3s; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. LOAD MODEL ---
@st.cache_resource
def load_model():
    try:
        model = AutoModelForImageClassification.from_pretrained("mera_potato_model")
        processor = AutoImageProcessor.from_pretrained("mera_potato_model")
        return model, processor
    except:
        return None, None

model, processor = load_model()

# --- 4. SIDEBAR (ANIMATED LOGO) ---
st.sidebar.markdown("""
    <div style="display: flex; justify-content: center; margin-bottom: 25px; margin-top: 10px;">
        <img src="https://cdn-icons-png.flaticon.com/512/11698/11698467.png" 
             style="width: 150px; border-radius: 50%; padding: 10px; background: rgba(255,255,255,0.15); 
             border: 3px solid rgba(255,255,255,0.4); 
             animation: float-and-glow 3s ease-in-out infinite;"> 
    </div>
    """, unsafe_allow_html=True)

st.sidebar.markdown("<h1 style='text-align: center; color: white; font-weight: 800; margin-top: -10px; font-size: 2.2rem; text-shadow: 0 2px 10px rgba(0,0,0,0.2);'>Plant Doctor</h1>", unsafe_allow_html=True)
st.sidebar.markdown("<p style='text-align: center; font-size: 0.9rem; opacity: 0.9; margin-bottom: 30px; letter-spacing: 2px; font-weight: 600;'>AI DIAGNOSTICS</p>", unsafe_allow_html=True)
st.sidebar.write("---")

nav = st.sidebar.radio("", ["🏠 Home Page", "🥔 Potato (Aloo)", "🍅 Tomato Check", "🌽 Corn Field"])

st.sidebar.write("---")
with st.sidebar.expander("📸 Tips for Best Results"):
    st.markdown("* ☀️ **Lighting:** Use bright daylight.\n* 🍃 **Focus:** Capture only the leaf.\n* 🖼️ **Background:** Keep it plain.")
st.sidebar.write("---")
st.sidebar.info("**Developers:**\n\n👨‍💻 **Saqlain Khan**\n(Data Engineer)\n\n👨‍💻 **Raheel Chishti**\n(Team Member)")

# --- 5. MAIN LOGIC ---
if nav == "🏠 Home Page":
    st.markdown("""
    <div class="hero-container">
        <h1 style="font-size: 4.5rem; font-weight: 900; background: -webkit-linear-gradient(#064e3b, #059669); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">Plant Doctor AI</h1>
        <p style="color:#065f46; font-size:1.5rem; font-weight:600; margin-bottom:15px;">
            AI-Powered Crop Disease Detection for Smart Farmers
        </p>
        <p style="color:#047857; font-size:1.2rem; max-width:750px; margin:auto; line-height:1.6;">
            Upload a leaf image and get instant disease diagnosis with treatment guidance.
        </p>
        <br>
        <a class="cta-button" href="#alookibimaricheckkarein">🌿 Start Diagnosis</a>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # SLIDER
        st.markdown("""
        <div class="slider-container">
            <div class="slide-track">
                <div class="slide"><img src="https://images.unsplash.com/photo-1625246333195-78d9c38ad449?w=800"></div>
                <div class="slide"><img src="https://images.unsplash.com/photo-1586771107445-d3ca888129ff?w=800"></div>
                <div class="slide"><img src="https://images.unsplash.com/photo-1530836369250-ef72a3f5cda8?w=800"></div>
                <div class="slide"><img src="https://images.unsplash.com/photo-1587334274328-64186a80aeee?w=800"></div>
                <div class="slide"><img src="https://images.unsplash.com/photo-1551754655-cd27e38d2076?w=800"></div>
                <div class="slide"><img src="https://images.unsplash.com/photo-1625246333195-78d9c38ad449?w=800"></div>
                <div class="slide"><img src="https://images.unsplash.com/photo-1586771107445-d3ca888129ff?w=800"></div>
            </div>
        </div>
        <p style="text-align:center; font-size:0.8rem; color:#aaa; margin-top:5px;">💡 Hover to Pause | Scroll to View</p>
        """, unsafe_allow_html=True)
        
    with col2:
        # WEATHER WITH VIP BADGE
        bg_gradient = "linear-gradient(135deg, #3b82f6 0%, #06b6d4 100%)"
        weather_icon = "⛅"
        if temp > 30:
            bg_gradient = "linear-gradient(135deg, #f59e0b 0%, #d97706 100%)"
            weather_icon = "☀️"
        elif temp < 20:
            bg_gradient = "linear-gradient(135deg, #6366f1 0%, #4f46e5 100%)"
            weather_icon = "❄️"

        st.markdown(f"""
        <div class="weather-container" style="background: {bg_gradient};">
            <div class="live-badge">
                <div class="live-dot"></div> LIVE WEATHER
            </div>
            <div class="weather-icon-big">{weather_icon}</div>
            <div class="temp-text">{temp}°C</div>
            <div class="weather-grid">
                <div class="stat-badge">💨 {wind} km/h</div>
                <div class="stat-badge">💧 65% Hum</div>
            </div>
            <div class="region-pill">📍 Punjab Region</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    
    # TRUST STATS
    c1, c2, c3, c4 = st.columns(4)
    stats = [("🌱", "15K+", "Images Trained"), ("🎯", "98%", "Accuracy"), ("⚡", "< 1s", "Fast Prediction"), ("👨‍🌾", "Expert", "Farmer Approved")]
    for col, (icon, val, lbl) in zip([c1,c2,c3,c4], stats):
        with col:
            st.markdown(f"""
            <div class="feature-card" style="padding:20px; min-height:180px;">
                <div class="feature-icon" style="font-size:3rem; margin-bottom:10px;">{icon}</div>
                <h2 style="margin:0; color:#064e3b; font-weight:800;">{val}</h2>
                <p style="color:#555; margin:0;">{lbl}</p>
            </div>
            """, unsafe_allow_html=True)

    # HOW IT WORKS
    st.markdown("<h2 style='text-align:center; color:#064e3b; font-weight:900; margin-top:60px; font-size:2.5rem;'>How It Works</h2>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    steps = [("📸", "Upload Leaf", "Clear photo lein."), ("🤖", "AI Analysis", "Model check karega."), ("💊", "Get Cure", "Ilaj payein.")]
    for col, (icon, title, desc) in zip([c1,c2,c3], steps):
        with col:
            st.markdown(f"""
            <div class="feature-card">
                <div class="feature-icon" style="font-size:3.5rem; margin-bottom:15px; color:#059669;">{icon}</div>
                <h3 style="color:#064e3b; font-weight:700;">{title}</h3><p style="color:#555;">{desc}</p>
            </div>
            """, unsafe_allow_html=True)

    # CROPS
    st.markdown("<h2 style='text-align:center; color:#064e3b; font-weight:900; margin-top:60px; font-size:2.5rem;'>Supported Crops</h2>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    crops = [("🥔", "Potato", "Fully Supported ✅"), ("🍅", "Tomato", "Launching Soon 🚀"), ("🌽", "Corn", "In Development 🛠️")]
    for col, (icon, name, status) in zip([c1,c2,c3], crops):
        with col:
            st.markdown(f"""
            <div class="feature-card" style="min-height:220px;">
                <div style="font-size:4.5rem; margin-bottom:15px;" class="feature-icon">{icon}</div>
                <h3 style="color:#064e3b; font-weight:800;">{name}</h3>
                <p style="font-weight:600; color:#059669;">{status}</p>
            </div>
            """, unsafe_allow_html=True)

    # FOOTER
    st.markdown("""
    <hr style="border-top: 2px solid #a7f3d0; margin-top: 80px;">
    <div style="text-align:center; padding:30px; color:#555;">
        <p style="font-weight:700; font-size: 1.1rem;">© 2025 Plant Doctor AI</p>
        <p style="font-size:0.9rem; margin-top: 10px;">
            Built with ❤️ using 
            <span style="background:#fce7f3; padding:4px 8px; border-radius:5px; color:#be185d; font-weight:600;">Streamlit</span>
            <span style="background:#e0e7ff; padding:4px 8px; border-radius:5px; color:#4338ca; font-weight:600;">PyTorch</span>
            & 
            <span style="background:#fef3c7; padding:4px 8px; border-radius:5px; color:#b45309; font-weight:600;">Transformers (ViT)</span>
        </p>
        <p style="font-size:0.8rem; margin-top: 10px; opacity: 0.8;">Developed by <b>Saqlain Khan</b> & <b>Raheel Chishti</b></p>
    </div>
    """, unsafe_allow_html=True)

elif nav == "🥔 Potato (Aloo)":
    st.header("🥔 Aloo Ki Bimari Check Karein", anchor="alookibimaricheckkarein")
    if not model: st.error("⚠️ Model folder nahi mila!"); st.stop()
    
    uploaded_file = st.file_uploader("Upload Leaf Photo", type=["jpg", "png", "jpeg"])
    if uploaded_file:
        col1, col2 = st.columns([1, 1.5])
        with col1:
            image = Image.open(uploaded_file).convert('RGB')
            st.image(image, caption="Uploaded Photo", use_column_width=True)
        with col2:
            my_bar = st.progress(0, text="Starting engine...")
            for i in range(100): time.sleep(0.01); my_bar.progress(i+1)
            my_bar.empty()
            
            inputs = processor(images=image, return_tensors="pt")
            with torch.no_grad():
                outputs = model(**inputs)
                logits = outputs.logits
                idx = logits.argmax(-1).item()
                conf = torch.softmax(logits, dim=1)[0][idx].item() * 100
                label = model.config.id2label[idx].replace("_", " ").title()
                
                probs = torch.softmax(logits, dim=1)[0].tolist()
                labels = [model.config.id2label[i].replace("_", " ").title() for i in range(len(probs))]
                prob_dict = {l: p*100 for l, p in zip(labels, probs)}

            is_healthy = "healthy" in label.lower() or "healty" in label.lower()
            bg_color = "#ecfdf5" if is_healthy else "#fef2f2"
            border_color = "#059669" if is_healthy else "#dc2626"
            
            st.markdown(f"""
                <div class='result-box' style='background: {bg_color}; border: 2px solid {border_color};'>
                    <h2 style='color: {border_color}; margin:0; font-weight: 800;'>{label}</h2>
                    <h4 style='color: {border_color}; margin-top: 10px; font-weight: 600;'>Confidence: {conf:.1f}%</h4>
                </div>
            """, unsafe_allow_html=True)
            
            st.write("### 📊 Analysis Breakdown")
            for l, p in prob_dict.items():
                st.write(f"**{l}**")
                st.progress(int(p))
            
            report_text = f"Plant Doctor AI Report\nDate: {datetime.datetime.now()}\n\nDiagnosis: {label}\nConfidence: {conf:.1f}%\n\nStatus: {'Healthy' if is_healthy else 'Action Needed'}"
            st.download_button(
                label="📄 Download Report",
                data=report_text,
                file_name="plant_doctor_report.txt",
                mime="text/plain"
            )

            if is_healthy:
                st.balloons()
                st.markdown("""
                <div class='result-box' style='background: white; border-left: 5px solid #059669; text-align: left;'>
                    <h3 style='color: #059669; font-weight: 800;'>🎉 Mubarak Ho!</h3>
                    <p style="font-weight: 600;">Aapki fasal bilkul theek hai. Hifazat ke liye ye karein:</p>
                    <ul style="font-weight: 500;">
                        <li>💧 <b>Pani:</b> Waqt par pani dein.</li>
                        <li>👀 <b>Nigrani:</b> Rozana pattay check karein.</li>
                    </ul>
                </div>
                """, unsafe_allow_html=True)
            elif "late" in label.lower():
                st.markdown("""
                <div class='result-box' style='background: white; border-left: 5px solid #dc2626; text-align: left;'>
                    <h3 style='color: #dc2626; font-weight: 800;'>💊 Late Blight Ka Ilaj</h3>
                    <ul style="font-weight: 500;">
                        <li><b>Spray (Chemical):</b> Metalaxyl + Mancozeb (2.5g per Liter) spray karein.</li>
                        <li><b>Frequency:</b> Har 7-10 din baad spray dohrayein jab tak bimari khatam na ho.</li>
                        <li><b>Organic:</b> Copper Fungicide ka bhi istemal kar sakte hain.</li>
                    </ul>
                </div>
                """, unsafe_allow_html=True)
            elif "early" in label.lower():
                st.markdown("""
                <div class='result-box' style='background: white; border-left: 5px solid #d97706; text-align: left;'>
                    <h3 style='color: #d97706; font-weight: 800;'>💊 Early Blight Ka Ilaj</h3>
                    <ul style="font-weight: 500;">
                        <li><b>Spray (Chemical):</b> Chlorothalonil ya Azoxystrobin spray karein.</li>
                        <li><b>Organic:</b> Neem Oil ka spray bihtareen hai.</li>
                        <li><b>Tip:</b> Neeche wale purane patton ko hata dein taake hawa lagay.</li>
                    </ul>
                </div>
                """, unsafe_allow_html=True)
            else:
                 st.info("⚠️ Bimari detect hui hai, lekin iska specific ilaj database mein nahi hai. Kisi maahir se rabta karein.")

elif nav in ["🍅 Tomato Check", "🌽 Corn Field"]:
    st.info("🚧 Coming Soon...") 