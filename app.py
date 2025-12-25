import streamlit as st
from PIL import Image
import torch
from transformers import AutoImageProcessor, AutoModelForImageClassification
import time
import datetime
import requests
import os  # <--- Ye add kiya hai path check karne ke liye

# --- 1. PAGE SETUP ---
st.set_page_config(
    page_title="Plant Doctor AI", 
    page_icon="🌿", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. ROBUST WEATHER FUNCTION (Optimized) ---
def get_real_weather():
    try:
        # Timeout added to prevent crashing
        url = "https://api.open-meteo.com/v1/forecast?latitude=31.5204&longitude=74.3587&current_weather=true"
        response = requests.get(url, timeout=3) 
        data = response.json()
        temp = data['current_weather']['temperature']
        wind = data['current_weather']['windspeed']
        return temp, wind
    except:
        return 28, 12 # Fallback Data

temp, wind = get_real_weather()

# --- 3. ULTRA PREMIUM CSS (SAME AS BEFORE) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
        scroll-behavior: smooth;
    }

    /* ANIMATIONS */
    @keyframes fadeInUp { from { opacity: 0; transform: translateY(30px); } to { opacity: 1; transform: translateY(0); } }
    @keyframes popIn { 0% { transform: scale(0.8); opacity: 0; } 100% { transform: scale(1); opacity: 1; } }
    @keyframes pulse-red { 0% { box-shadow: 0 0 0 0 rgba(255, 50, 50, 0.7); } 70% { box-shadow: 0 0 0 10px rgba(255, 50, 50, 0); } 100% { box-shadow: 0 0 0 0 rgba(255, 50, 50, 0); } }
    @keyframes float-weather { 0% { transform: translateY(0px); } 50% { transform: translateY(-8px); } 100% { transform: translateY(0px); } }
    @keyframes diamond-wind { 0% { transform: translateY(0) translateX(0); } 100% { transform: translateY(100px) translateX(-100px); } }
    @keyframes gradientBG { 0% { background-position: 0% 50%; } 50% { background-position: 100% 50%; } 100% { background-position: 0% 50%; } }
    @keyframes float-logo { 0% { transform: translateY(0px); box-shadow: 0 0 15px rgba(16, 185, 129, 0.4); } 50% { transform: translateY(-8px); box-shadow: 0 0 30px rgba(16, 185, 129, 0.7); } 100% { transform: translateY(0px); box-shadow: 0 0 15px rgba(16, 185, 129, 0.4); } }

    h1, h2, h3, p, span, a, div.stMarkdown { animation: fadeInUp 0.8s ease-out both; }

    /* BACKGROUND PARTICLES */
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

    /* SIDEBAR NAVIGATION */
    [data-testid="stSidebar"] { background-image: linear-gradient(180deg, #064e3b 0%, #047857 100%); border-right: none; }
    [data-testid="stSidebar"] * { color: #ecfdf5 !important; }
    [data-testid="stSidebar"] .stRadio div[role="radiogroup"] label {
        background: rgba(0, 0, 0, 0.25); padding: 15px 20px; border-radius: 15px; margin-bottom: 12px !important;
        border: 1px solid rgba(255,255,255,0.1); width: 100%; display: flex; align-items: center;
        transition: all 0.3s ease; box-shadow: 0 4px 6px rgba(0,0,0,0.1); cursor: pointer;
    }
    [data-testid="stSidebar"] .stRadio div[role="radiogroup"] label:hover {
        background: rgba(255, 255, 255, 0.15); transform: scale(1.02); border-color: #34d399;
    }
    [data-testid="stSidebar"] .stRadio div[role="radiogroup"] div[aria-checked="true"] + div + label {
         background: linear-gradient(90deg, #059669, #10b981) !important; border: 1px solid #a7f3d0 !important;
         font-weight: 800; transform: scale(1.03); box-shadow: 0 0 20px rgba(16, 185, 129, 0.6) !important; color: white !important;
    }
    [data-testid="stSidebar"] .stRadio div[role="radiogroup"] div[role="radio"] { display: none; }

    /* HERO & CARDS */
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
    .feature-card:hover { transform: perspective(1000px) rotateX(5deg) rotateY(-5deg) translateY(-15px); box-shadow: 0 30px 60px rgba(16, 185, 129, 0.3); border-color: #34d399; }
    
    .cta-button {
        display: inline-block; background: linear-gradient(90deg, #059669, #10b981); color: white !important;
        padding: 18px 45px; border-radius: 50px; font-weight: 800; font-size: 1.1rem; text-decoration: none;
        box-shadow: 0 10px 30px rgba(16,185,129,0.5); transition: all 0.3s; margin-top: 25px; border: 2px solid #a7f3d0;
        animation: popIn 1.2s ease-out;
    }
    .cta-button:hover { transform: scale(1.1) translateY(-5px); }

    /* SLIDER */
    .slider-container { width: 100%; overflow: hidden; border-radius: 25px; box-shadow: 0 20px 50px rgba(0,0,0,0.2); border: 2px solid rgba(255,255,255,0.7); background: #000; animation: popIn 1s ease-out; }
    .slide-track { display: flex; width: calc(1000px * 10); animation: scroll 45s linear infinite; }
    .slide-track:hover { animation-play-state: paused; }
    .slide { width: 600px; height: 350px; flex-shrink: 0; padding: 0 5px; }
    .slide img { width: 100%; height: 100%; object-fit: cover; border-radius: 15px; transition: transform 0.4s; }
    .slide img:hover { transform: scale(1.08); filter: brightness(1.1); cursor: grab; }
    @keyframes scroll { 0% { transform: translateX(0); } 100% { transform: translateX(calc(-600px * 5)); } }

    /* NEW PREMIUM WEATHER WIDGET */
    .weather-container {
        position: relative;
        background: rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(25px); /* Strong Blur */
        -webkit-backdrop-filter: blur(25px);
        border-radius: 30px;
        padding: 25px;
        border: 1px solid rgba(255, 255, 255, 0.2);
        box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25), inset 0 0 0 1px rgba(255, 255, 255, 0.1);
        overflow: hidden;
        transition: transform 0.3s ease;
        height: 350px;
        display: flex; flex-direction: column; justify-content: space-between;
    }
    .weather-container:hover { transform: translateY(-5px); box-shadow: 0 30px 60px -12px rgba(0, 0, 0, 0.35); }

    /* Decorative Glow behind the card */
    .weather-glow {
        position: absolute; top: -50%; left: -50%; width: 200%; height: 200%;
        background: radial-gradient(circle, rgba(255,255,255,0.2) 0%, transparent 60%);
        animation: rotate-glow 15s linear infinite; z-index: 0; pointer-events: none;
    }
    .weather-content { position: relative; z-index: 2; display: flex; flex-direction: column; align-items: center; height: 100%; }
    .weather-header { width: 100%; display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }

    .live-badge {
        background: rgba(0, 0, 0, 0.3); padding: 6px 14px; border-radius: 20px;
        font-size: 0.75rem; font-weight: 700; letter-spacing: 1px; display: flex; align-items: center; gap: 8px;
        border: 1px solid rgba(255,255,255,0.1); box-shadow: 0 4px 10px rgba(0,0,0,0.1);
    }
    .live-dot { width: 8px; height: 8px; background: #ef4444; border-radius: 50%; box-shadow: 0 0 8px #ef4444; animation: pulse-red 1.5s infinite; }

    .temp-big {
        font-size: 5.5rem; font-weight: 800; line-height: 1;
        background: linear-gradient(180deg, #ffffff 20%, rgba(255,255,255,0.6) 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        filter: drop-shadow(0 4px 10px rgba(0,0,0,0.2)); margin: 10px 0;
    }
    .weather-icon-3d { font-size: 4rem; filter: drop-shadow(0 10px 15px rgba(0,0,0,0.3)); animation: float-weather 6s ease-in-out infinite; }

    .details-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; width: 100%; margin-top: auto; }
    .detail-item {
        background: rgba(255, 255, 255, 0.15); border-radius: 15px; padding: 10px; text-align: center;
        border: 1px solid rgba(255,255,255,0.1); transition: background 0.2s;
    }
    .detail-item:hover { background: rgba(255, 255, 255, 0.25); }
    .detail-label { font-size: 0.75rem; color: rgba(255,255,255,0.8); text-transform: uppercase; letter-spacing: 1px; }
    .detail-val { font-size: 1.1rem; font-weight: 700; color: white; }

    .result-box { padding: 30px; border-radius: 25px; text-align: center; background: rgba(255,255,255,0.95); box-shadow: 0 20px 50px rgba(0,0,0,0.1); animation: popIn 0.6s ease-out; border: 2px solid white; }
    img { border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.15); transition: transform 0.3s; }
    </style>
    """, unsafe_allow_html=True)

# --- 4. OPTIMIZED MODEL LOADING (WITH PATH FIX) ---
@st.cache_resource
def load_model():
    try:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # --- PATH FIX: Check karega files kahan hain ---
        if os.path.exists("config.json") and (os.path.exists("model.safetensors") or os.path.exists("pytorch_model.bin")):
            model_path = "." # Current directory
        else:
            model_path = "mera_potato_model" # Subfolder
            
        model = AutoModelForImageClassification.from_pretrained(model_path).to(device)
        processor = AutoImageProcessor.from_pretrained(model_path)
        model.eval() 
        return model, processor, device
    except:
        return None, None, "cpu"

model, processor, device = load_model()

# --- 5. SIDEBAR ---
st.sidebar.markdown("""
    <div style="display: flex; justify-content: center; margin-bottom: 25px; margin-top: 10px;">
        <img src="https://cdn-icons-png.flaticon.com/512/11698/11698467.png" 
             style="width: 150px; border-radius: 50%; padding: 10px; background: rgba(255,255,255,0.15); 
             border: 3px solid rgba(255,255,255,0.4); 
             animation: float-logo 3s ease-in-out infinite;"> 
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

# --- 6. MAIN LOGIC ---
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
        st.markdown("""
        <div class="slider-container">
            <div class="slide-track">
                <div class="slide"><img src="https://images.unsplash.com/photo-1625246333195-78d9c38ad449?w=800"></div>
                <div class="slide"><img src="https://images.unsplash.com/photo-1586771107445-d3ca888129ff?w=800"></div>
                <div class="slide"><img src="https://images.unsplash.com/photo-1530836369250-ef72a3f5cda8?w=800"></div>
                <div class="slide"><img src="https://images.unsplash.com/photo-1587334274328-64186a80aeee?w=800"></div>
                <div class="slide"><img src="https://images.unsplash.com/photo-1551754655-cd27e38d2076?w=800"></div>
                <div class="slide"><img src="https://images.unsplash.com/photo-1625246333195-78d9c38ad449?w=800"></div>
            </div>
        </div>
        <p style="text-align:center; font-size:0.8rem; color:#aaa; margin-top:5px;">💡 Hover to Pause | Scroll to View</p>
        """, unsafe_allow_html=True)
        
    with col2:
        if temp > 30:
            card_bg = "linear-gradient(145deg, #f59e0b 0%, #ea580c 100%)"
            weather_icon = "☀️"
            condition = "Sunny"
        elif temp < 20:
            card_bg = "linear-gradient(145deg, #6366f1 0%, #3b82f6 100%)"
            weather_icon = "❄️"
            condition = "Chilly"
        else:
            card_bg = "linear-gradient(145deg, #10b981 0%, #059669 100%)"
            weather_icon = "⛅"
            condition = "Pleasant"

        st.markdown(f"""
        <div class="weather-container" style="background: {card_bg};">
            <div class="weather-glow"></div>
            <div class="weather-content">
                <div class="weather-header">
                    <div class="live-badge"><div class="live-dot"></div> LIVE</div>
                    <div style="font-weight:600; font-size:0.9rem; color:rgba(255,255,255,0.9);">📍 Punjab</div>
                </div>
                <div class="weather-icon-3d">{weather_icon}</div>
                <div class="temp-big">{temp}°</div>
                <div style="font-size:1.2rem; font-weight:600; color:rgba(255,255,255,0.9); margin-bottom:15px;">{condition}</div>
                <div class="details-grid">
                    <div class="detail-item">
                        <div class="detail-label">Wind</div>
                        <div class="detail-val">{wind} <span style="font-size:0.7rem;">km/h</span></div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-label">Humidity</div>
                        <div class="detail-val">65 <span style="font-size:0.7rem;">%</span></div>
                    </div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
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
    
    # --- MODEL CHECK (SAFE) ---
    if not model:
        st.error("⚠️ **Model Folder Missing!**")
        st.info("Ensure `config.json` and `model.safetensors` are in the same folder as `app.py` or in `mera_potato_model` folder.")
        st.stop()
    
    uploaded_file = st.file_uploader("Upload Leaf Photo", type=["jpg", "png", "jpeg"])
    
    if uploaded_file is not None and uploaded_file.size > 5*1024*1024:
        st.error("⚠️ File size too large! Please upload image under 5MB.")
    elif uploaded_file:
        col1, col2 = st.columns([1, 1.5])
        with col1:
            display_image = Image.open(uploaded_file).convert('RGB')
            st.image(display_image, caption="Uploaded Photo", use_column_width=True)
        
        with col2:
            with st.spinner("Analyzing..."):
                time.sleep(1) 
                
                # PREDICTION LOGIC
                import torch
                model_image = display_image.resize((224, 224)) 
                inputs = processor(images=model_image, return_tensors="pt").to(device)
                
                with torch.no_grad():
                    outputs = model(**inputs)
                    logits = outputs.logits
                    idx = logits.argmax(-1).item()
                    conf = torch.softmax(logits, dim=1)[0][idx].item() * 100
                    label = model.config.id2label[idx].replace("_", " ").title()
                    probs = torch.softmax(logits, dim=1)[0].tolist()
                    labels = [model.config.id2label[i].replace("_", " ").title() for i in range(len(probs))]
                    prob_dict = {l: p*100 for l, p in zip(labels, probs)}
                
                # --- 90% CHECK ---
                if conf < 90:
                    st.error("⚠️ **Photo Clear Nahi Hai!**")
                    st.warning(f"Confidence: {conf:.1f}% (Low)\n\nYe Aloo ka patta nahi lag raha. Saaf photo upload karein.")
                    st.stop()

            # DISPLAY RESULT
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

elif nav in ["🍅 Tomato Check", "🌽 Corn Field"]:
    st.info("🚧 Coming Soon...")  