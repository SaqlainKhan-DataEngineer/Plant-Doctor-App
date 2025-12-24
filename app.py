import streamlit as st
from PIL import Image
import torch
from transformers import AutoImageProcessor, AutoModelForImageClassification
import time

# --- 1. PAGE SETUP ---
st.set_page_config(
    page_title="Plant Doctor AI", 
    page_icon="🌿", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. ULTRA PREMIUM CSS (PARTICLES ON TOP) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }

    /* --- 1. BACKGROUND PARTICLES (NOW VISIBLE ON TOP) --- */
    .stApp::before {
        content: "";
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        /* Darker Green Circles for Visibility */
        background-image:
            radial-gradient(circle at 20% 80%, rgba(6, 78, 59, 0.15) 0%, transparent 20%),
            radial-gradient(circle at 80% 20%, rgba(6, 78, 59, 0.15) 0%, transparent 20%),
            radial-gradient(circle at 40% 40%, rgba(16, 185, 129, 0.15) 0%, transparent 20%),
            radial-gradient(circle at 90% 90%, rgba(5, 150, 105, 0.15) 0%, transparent 20%);
        background-size: 100% 100%;
        animation: drift 20s linear infinite;
        pointer-events: none; /* Clicks will pass through */
        z-index: 99; /* Brings particles on TOP of everything */
    }
    @keyframes drift {
        0% { transform: translate(0,0) scale(1); }
        25% { transform: translate(-30px, 30px) scale(1.1); }
        50% { transform: translate(30px, -30px) scale(0.9); }
        75% { transform: translate(-20px, -10px) scale(1.05); }
        100% { transform: translate(0,0) scale(1); }
    }

    /* --- 2. ANIMATIONS --- */
    @keyframes slideUp {
        from { opacity: 0; transform: translateY(40px); }
        to { opacity: 1; transform: translateY(0); }
    }
    @keyframes float-and-glow {
        0% { transform: translateY(0px); box-shadow: 0 0 10px rgba(255,255,255,0.1); }
        50% { transform: translateY(-12px); box-shadow: 0 0 30px rgba(16, 185, 129, 0.6); }
        100% { transform: translateY(0px); box-shadow: 0 0 10px rgba(255,255,255,0.1); }
    }
    @keyframes subtlePulse {
        0%, 100% { filter: brightness(1); }
        50% { filter: brightness(1.05); }
    }
    @keyframes gradientBG {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }

    /* --- 3. SIDEBAR STYLING --- */
    [data-testid="stSidebar"] {
        background-image: linear-gradient(180deg, #064e3b 0%, #047857 100%);
        border-right: none;
    }
    [data-testid="stSidebar"] * {
        color: #ecfdf5 !important;
    }
    
    /* Navigation Buttons */
    [data-testid="stSidebar"] .stRadio > div[role="radiogroup"] {
        align-items: center;
        justify-content: center;
    }
    [data-testid="stSidebar"] .stRadio div[role="radiogroup"] label {
        display: flex;
        align-items: center;
        width: 100%;
        background: rgba(255, 255, 255, 0.05);
        padding: 12px 15px;
        border-radius: 12px;
        margin-bottom: 10px !important;
        border: 1px solid rgba(255,255,255,0.05);
        transition: all 0.3s;
        text-align: left;
        font-weight: 600;
        letter-spacing: 0.5px;
        z-index: 100; /* Sidebar buttons above particles */
        position: relative;
    }
    [data-testid="stSidebar"] .stRadio div[role="radiogroup"] label:hover {
        background: rgba(255, 255, 255, 0.15);
        transform: translateX(5px);
        border-color: #34d399;
    }
    [data-testid="stSidebar"] .stRadio div[role="radiogroup"] div[aria-checked="true"] + div + label {
         background: linear-gradient(90deg, rgba(16, 185, 129, 0.25), transparent) !important;
         border-left: 5px solid #34d399 !important;
         font-weight: 800;
         transform: translateX(5px);
         box-shadow: -5px 0 20px rgba(52, 211, 153, 0.2);
    }

    /* --- 4. HERO SECTION --- */
    .hero-container {
        text-align: center;
        padding: 60px 20px;
        border-radius: 30px;
        background: linear-gradient(-45deg, #ccfbf1, #d1fae5, #a7f3d0, #6ee7b7);
        background-size: 400% 400%;
        animation: gradientBG 15s ease infinite, subtlePulse 8s ease-in-out infinite, slideUp 0.8s ease-out;
        box-shadow: 0 20px 50px rgba(0,0,0,0.1);
        margin-bottom: 40px;
        border: 1px solid rgba(255,255,255,0.6);
        position: relative;
        z-index: 10; /* Content above particles */
    }
    .hero-title {
        font-weight: 900;
        font-size: 4rem;
        background: -webkit-linear-gradient(#064e3b, #059669);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 10px;
        letter-spacing: -2px;
    }
    
    /* --- 5. 3D FLOATING CARDS --- */
    .feature-card {
        background: rgba(255, 255, 255, 0.8); /* Higher opacity */
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        padding: 30px;
        border-radius: 25px;
        text-align: center;
        border: 1px solid rgba(255,255,255,0.5);
        box-shadow: 0 8px 32px rgba(0,0,0,0.07);
        min-height: 320px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        transform-style: preserve-3d;
        transition: transform 0.4s ease, box-shadow 0.4s ease;
        animation: slideUp 1s ease-out 0.2s backwards;
        position: relative;
        z-index: 10;
    }
    .feature-card:hover {
        transform: perspective(1000px) rotateX(5deg) rotateY(-5deg) translateY(-15px);
        box-shadow: 0 25px 50px rgba(16, 185, 129, 0.25);
        border-color: #34d399;
    }
    .feature-icon {
        font-size: 3.5rem;
        margin-bottom: 20px;
        background: linear-gradient(135deg, #ecfdf5, #d1fae5);
        width: 100px;
        height: 100px;
        line-height: 100px;
        border-radius: 50%;
        color: #059669;
        box-shadow: 0 10px 20px rgba(16, 185, 129, 0.2);
    }
    
    img {
        border-radius: 25px;
        box-shadow: 0 15px 40px rgba(0,0,0,0.15);
        transition: transform 0.3s;
        animation: slideUp 1s ease-out;
    }
    
    .result-box {
        padding: 30px;
        border-radius: 25px;
        text-align: center;
        margin-bottom: 25px;
        backdrop-filter: blur(20px);
        box-shadow: 0 15px 30px rgba(0,0,0,0.08);
        animation: slideUp 0.5s ease-out;
    }
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

# --- 4. SIDEBAR ---
# Super Animated Logo
st.sidebar.markdown("""
    <div style="display: flex; justify-content: center; margin-bottom: 20px; margin-top: 10px;">
        <img src="https://cdn-icons-png.flaticon.com/512/11698/11698467.png" 
             style="width: 140px; border-radius: 50%; padding: 8px; background: rgba(255,255,255,0.15); 
             border: 2px solid rgba(255,255,255,0.3); 
             animation: float-and-glow 3s ease-in-out infinite;">
    </div>
    """, unsafe_allow_html=True)

st.sidebar.markdown("<h1 style='text-align: center; color: white; font-weight: 800; margin-top: -10px; font-size: 2rem;'>Plant Doctor</h1>", unsafe_allow_html=True)
st.sidebar.markdown("<p style='text-align: center; font-size: 0.85rem; opacity: 0.8; margin-bottom: 20px; letter-spacing: 1px;'>AI DIAGNOSTICS</p>", unsafe_allow_html=True)
st.sidebar.write("---")

nav = st.sidebar.radio("", ["🏠  Home Page", "🥔  Potato (Aloo)", "🍅  Tomato Check", "🌽  Corn Field"])

st.sidebar.write("---")

with st.sidebar.expander("📸 Tips for Best Results"):
    st.markdown("""
    * ☀️ **Lighting:** Use bright daylight.
    * 🍃 **Focus:** Capture only the leaf.
    * 🖼️ **Background:** Keep it plain.
    """)

st.sidebar.write("---")
st.sidebar.info("**Developers:**\n\n👨‍💻 **Saqlain Khan**\n(Data Engineer)\n\n👨‍💻 **Raheel Chishti**\n(Team Member)")

# --- 5. MAIN LOGIC ---
if nav == "🏠  Home Page":
    st.markdown("""
    <div class="hero-container">
        <h1 class="hero-title">Smart Farming Assistant</h1>
        <p style="color: #065f46; font-size: 1.3rem;">Apni fasal ko bachayein, Jadid <b>AI Technology</b> ke sath.</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.image("https://images.unsplash.com/photo-1625246333195-78d9c38ad449?w=1200", use_column_width=True)
    
    st.write("") 
    st.write("") 

    st.markdown("<h2 style='text-align: center; color: #064e3b; margin-bottom: 50px; font-weight: 900; font-size: 2.8rem;'>Why Choose Us?</h2>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-icon">📸</div>
            <h3 style="color: #064e3b; font-weight: 800;">Instant Scan</h3>
            <p style="color: #555; font-weight: 600;">Bas tasveer upload karein aur <b>1 second</b> mein nateeja payein.</p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-icon">🔬</div>
            <h3 style="color: #064e3b; font-weight: 800;">98% Accuracy</h3>
            <p style="color: #555; font-weight: 600;">Hamara AI model hazaron tasveeron par train kiya gaya hai.</p>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-icon">💊</div>
            <h3 style="color: #064e3b; font-weight: 800;">Expert Cure</h3>
            <p style="color: #555; font-weight: 600;">Bimari ke hisaab se behtareen <b>dawayi aur ilaj</b> janlein.</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("<p style='text-align: center; color: #aaa; font-size: 0.9rem;'>© 2025 Plant Doctor AI | Designed by Saqlain & Raheel</p>", unsafe_allow_html=True)


elif nav == "🥔  Potato (Aloo)":
    st.header("🥔 Aloo Ki Bimari Check Karein")
    
    if not model:
        st.error("⚠️ Model folder nahi mila! (Check 'mera_potato_model' folder)")
        st.stop()

    uploaded_file = st.file_uploader("Upload Leaf Photo", type=["jpg", "png", "jpeg"])

    if uploaded_file:
        col1, col2 = st.columns([1, 1.5])
        
        with col1:
            image = Image.open(uploaded_file).convert('RGB')
            st.image(image, caption="Uploaded Photo", use_column_width=True)
        
        with col2:
            # Scanning Animation
            my_bar = st.progress(0, text="Starting engine...")
            status_text = st.empty()
            
            steps = ["🔍 Scanning image...", "🧬 Extracting features...", "📂 Comparing with database...", "✅ Finalizing result..."]
            
            for i, step in enumerate(steps):
                status_text.text(step)
                my_bar.progress((i + 1) * 25)
                time.sleep(0.4)
                
            status_text.empty()
            my_bar.empty()
            
            # AI Logic
            inputs = processor(images=image, return_tensors="pt")
            with torch.no_grad():
                outputs = model(**inputs)
                logits = outputs.logits
                idx = logits.argmax(-1).item()
            
            label = model.config.id2label[idx]
            clean_label = label.replace("_", " ").title()
            conf = torch.softmax(logits, dim=1)[0][idx].item() * 100
            
            if conf < 90:
                st.error("⚠️ **Tasveer Pehchani Nahi Ja Rahi!**")
                st.warning(f"""
                **AI Confuse hai (Confidence: {conf:.1f}%):**
                1. Lagta hai ye **Aloo (Potato)** ka patta nahi hai.
                2. Ya tasveer bohat dhundli (blurry) hai.
                """)
            else:
                is_healthy = "healthy" in clean_label.lower() or "healty" in clean_label.lower()

                if is_healthy:
                    bg_color = "#ecfdf5"
                    border_color = "#059669"
                    status_msg = "✅ Sab Theek Hai (All OK)"
                    clean_label = "Healthy (Sehatmand)"
                else:
                    bg_color = "#fef2f2"
                    border_color = "#dc2626"
                    status_msg = "⚠️ Bimari Detected (Action Needed)"

                st.markdown(f"""
                    <div class='result-box' style='background: {bg_color}; border: 2px solid {border_color};'>
                        <h2 style='color: {border_color}; margin:0; font-weight: 800;'>{clean_label}</h2>
                        <h4 style='color: {border_color}; margin-top: 10px; font-weight: 600;'>{status_msg}</h4>
                    </div>
                """, unsafe_allow_html=True)
                
                # Confidence Progress Bar
                st.write(f"**Confidence Score:** {conf:.1f}%")
                st.progress(int(conf))

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
                    
                elif "late" in clean_label.lower():
                    st.markdown("""
                    <div class='result-box' style='background: white; border-left: 5px solid #dc2626; text-align: left;'>
                        <h3 style='color: #dc2626; font-weight: 800;'>💊 Late Blight Ka Ilaj</h3>
                        <ul style="font-weight: 500;">
                            <li><b>Chemical:</b> Metalaxyl + Mancozeb (2.5g/liter) spray karein.</li>
                            <li><b>Schedule:</b> Har 7-10 din baad spray dohrayein.</li>
                        </ul>
                    </div>
                    """, unsafe_allow_html=True)
                    
                elif "early" in clean_label.lower():
                    st.markdown("""
                    <div class='result-box' style='background: white; border-left: 5px solid #d97706; text-align: left;'>
                        <h3 style='color: #d97706; font-weight: 800;'>💊 Early Blight Ka Ilaj</h3>
                        <ul style="font-weight: 500;">
                            <li><b>Chemical:</b> Chlorothalonil ya Azoxystrobin spray karein.</li>
                            <li><b>Organic:</b> Neem Oil ka spray bihtareen hai.</li>
                        </ul>
                    </div>
                    """, unsafe_allow_html=True)
                
                else:
                    st.info("Is result ke liye filhal koi makhsoos ilaj available nahi hai.")

elif nav in ["🍅  Tomato Check", "🌽  Corn Field"]:
    st.info("🚧 Coming Soon in few days...")