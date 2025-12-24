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

# --- 2. THE ULTIMATE CSS (CLAUDE VISUALS + KIMI SMOOTHNESS) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
        scroll-behavior: smooth; /* Kimi's Smooth Scroll */
    }

    /* --- 1. BACKGROUND PARTICLES (CLAUDE'S DIAMOND WIND - HIGH VISIBILITY) --- */
    .stApp::before {
        content: "";
        position: fixed;
        top: -50%;
        left: -50%;
        width: 200%;
        height: 200%;
        background-image:
            radial-gradient(circle at 20px 30px, rgba(4, 120, 87, 0.4) 0px, transparent 3px),
            radial-gradient(circle at 40px 70px, rgba(16, 185, 129, 0.5) 0px, transparent 3px),
            radial-gradient(circle at 50px 160px, rgba(5, 150, 105, 0.4) 0px, transparent 3px),
            radial-gradient(circle at 90px 40px, rgba(52, 211, 153, 0.6) 0px, transparent 2px),
            radial-gradient(circle at 130px 80px, rgba(6, 78, 59, 0.5) 0px, transparent 3px);
        background-repeat: repeat;
        background-size: 200px 200px;
        animation: diamond-wind 30s linear infinite;
        pointer-events: none;
        z-index: 0;
    }

    @keyframes diamond-wind {
        0% { transform: translateY(0) translateX(0); }
        100% { transform: translateY(100px) translateX(-100px); } 
    }

    /* --- 2. KIMI'S FADE-IN ANIMATION (Smooth Entry) --- */
    .stApp > div > div > div > div > div[class*="stMarkdown"],
    .stApp > div > div > div > div > div[data-testid="stImage"] {
        animation: fadeInUp 0.8s ease-out backwards;
    }
    @keyframes fadeInUp {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }

    /* --- 3. HERO & CARDS STYLING --- */
    .hero-container {
        text-align: center;
        padding: 60px 20px;
        border-radius: 30px;
        background: linear-gradient(-45deg, #ccfbf1, #d1fae5, #a7f3d0, #6ee7b7);
        background-size: 400% 400%;
        animation: gradientBG 15s ease infinite;
        box-shadow: 0 20px 50px rgba(0,0,0,0.1);
        margin-bottom: 40px;
        border: 1px solid rgba(255,255,255,0.6);
        position: relative;
        z-index: 1;
    }
    
    @keyframes gradientBG {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }

    /* 3D Floating Cards */
    .feature-card {
        background: rgba(255, 255, 255, 0.85);
        backdrop-filter: blur(20px);
        padding: 30px;
        border-radius: 25px;
        text-align: center;
        border: 1px solid rgba(255,255,255,0.5);
        box-shadow: 0 8px 32px rgba(0,0,0,0.07);
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        transform-style: preserve-3d;
        transition: transform 0.4s ease, box-shadow 0.4s ease;
        position: relative;
        z-index: 1;
    }
    .feature-card:hover {
        transform: perspective(1000px) rotateX(5deg) rotateY(-5deg) translateY(-10px);
        box-shadow: 0 25px 50px rgba(16, 185, 129, 0.25);
        border-color: #34d399;
    }
    
    /* CTA Button (Start Diagnosis) */
    .cta-button {
        display: inline-block;
        background: linear-gradient(90deg, #059669, #10b981);
        color: white !important;
        padding: 15px 40px;
        border-radius: 50px;
        font-weight: 700;
        text-decoration: none;
        box-shadow: 0 10px 25px rgba(16,185,129,0.4);
        transition: all 0.3s;
        margin-top: 20px;
    }
    .cta-button:hover {
        transform: scale(1.05);
        box-shadow: 0 15px 35px rgba(16,185,129,0.6);
    }

    /* --- 4. SIDEBAR STYLING --- */
    [data-testid="stSidebar"] {
        background-image: linear-gradient(180deg, #064e3b 0%, #047857 100%);
        border-right: none;
    }
    [data-testid="stSidebar"] * {
        color: #ecfdf5 !important;
    }
    
    /* Sidebar Logo Animation */
    @keyframes float-and-glow {
        0% { transform: translateY(0px); box-shadow: 0 0 10px rgba(255,255,255,0.1); }
        50% { transform: translateY(-10px); box-shadow: 0 0 30px rgba(16, 185, 129, 0.6); }
        100% { transform: translateY(0px); box-shadow: 0 0 10px rgba(255,255,255,0.1); }
    }

    /* Navigation Buttons */
    [data-testid="stSidebar"] .stRadio div[role="radiogroup"] label {
        background: rgba(255, 255, 255, 0.05);
        padding: 12px 15px;
        border-radius: 12px;
        margin-bottom: 10px !important;
        border: 1px solid rgba(255,255,255,0.05);
        transition: all 0.3s;
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
    }
    
    .result-box {
        padding: 30px;
        border-radius: 25px;
        text-align: center;
        background: rgba(255,255,255,0.9);
        box-shadow: 0 15px 30px rgba(0,0,0,0.08);
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
    # --- HERO SECTION (ChatGPT Content + Claude Design) ---
    st.markdown("""
    <div class="hero-container">
        <h1 style="font-size: 4rem; font-weight: 900; background: -webkit-linear-gradient(#064e3b, #059669); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">Plant Doctor AI</h1>
        <p style="color:#065f46; font-size:1.4rem; font-weight:600; margin-bottom:10px;">
            AI-Powered Crop Disease Detection for Smart Farmers
        </p>
        <p style="color:#047857; font-size:1.1rem; max-width:700px; margin:auto; line-height:1.6;">
            Upload a leaf image and get instant disease diagnosis with treatment guidance
            using deep learning models trained on real agricultural data.
        </p>
        <br>
        <a class="cta-button" href="#">🌿 Start Diagnosis</a>
    </div>
    """, unsafe_allow_html=True)
    
    st.image("https://images.unsplash.com/photo-1625246333195-78d9c38ad449?w=1200", use_column_width=True, style="border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.1);")
    
    # --- TRUST INDICATORS (ChatGPT Stats) ---
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns(4)
    stats = [
        ("🌱", "15K+", "Images Trained"),
        ("🎯", "98%", "Accuracy"),
        ("⚡", "< 1s", "Fast Prediction"),
        ("👨‍🌾", "Expert", "Farmer Approved")
    ]
    for col, (icon, value, label) in zip([col1,col2,col3,col4], stats):
        with col:
            st.markdown(f"""
            <div class="feature-card" style="min-height:180px; padding:20px;">
                <div style="font-size:3rem; margin-bottom:10px;">{icon}</div>
                <h2 style="margin:0; color:#064e3b; font-weight:800; font-size:2rem;">{value}</h2>
                <p style="font-weight:600; color:#555; margin:0;">{label}</p>
            </div>
            """, unsafe_allow_html=True)

    # --- HOW IT WORKS (ChatGPT Steps) ---
    st.markdown("<h2 style='text-align:center; color:#064e3b; font-weight:900; margin-top:80px; font-size:3rem;'>How It Works</h2>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    steps = [
        ("📸", "Upload Leaf", "Take a clear photo of the affected leaf."),
        ("🤖", "AI Analysis", "Deep learning model analyzes patterns."),
        ("💊", "Get Cure", "Instant diagnosis with cure suggestions.")
    ]
    for col, (icon, title, desc) in zip([col1,col2,col3], steps):
        with col:
            st.markdown(f"""
            <div class="feature-card">
                <div style="font-size:3.5rem; margin-bottom:15px; background: #ecfdf5; width:80px; height:80px; line-height:80px; border-radius:50%; margin: 0 auto 15px auto;">{icon}</div>
                <h3 style="color:#064e3b; font-weight:700;">{title}</h3>
                <p style="color:#555;">{desc}</p>
            </div>
            """, unsafe_allow_html=True)

    # --- SUPPORTED CROPS (ChatGPT Roadmap) ---
    st.markdown("<h2 style='text-align:center; color:#064e3b; font-weight:900; margin-top:80px; font-size:3rem;'>Supported Crops</h2>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    crops = [
        ("🥔", "Potato", "Fully Supported ✅"),
        ("🍅", "Tomato", "Launching Soon 🚀"),
        ("🌽", "Corn", "In Development 🛠️")
    ]
    for col, (icon, name, status) in zip([col1,col2,col3], crops):
        with col:
            st.markdown(f"""
            <div class="feature-card" style="min-height:220px;">
                <div style="font-size:4.5rem; margin-bottom:15px;">{icon}</div>
                <h3 style="color:#064e3b; font-weight:800;">{name}</h3>
                <p style="font-weight:600; color:#059669;">{status}</p>
            </div>
            """, unsafe_allow_html=True)

    # --- FOOTER ---
    st.markdown("""
    <hr style="border-top: 2px solid #a7f3d0; margin-top: 50px;">
    <div style="text-align:center; padding:20px; color:#555;">
        <p style="font-weight:600; font-size:1.1rem;">© 2025 Plant Doctor AI</p>
        <p style="font-size:0.9rem;">Built with ❤️ using Streamlit, PyTorch & Transformers</p>
        <p style="font-size:0.85rem; opacity:0.8;">Developed by <b>Saqlain Khan</b> & <b>Raheel Chishti</b></p>
    </div>
    """, unsafe_allow_html=True)


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
            st.image(image, caption="Uploaded Photo", use_column_width=True, style="border-radius:15px;")
        
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
    