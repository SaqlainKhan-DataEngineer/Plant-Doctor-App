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

# --- 2. ULTRA PREMIUM CSS (FULLY ANIMATED + 5 SLIDES) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
        scroll-behavior: smooth;
    }

    /* --- 1. NEW 5-IMAGE SLIDESHOW (FASTER) --- */
    .slider-frame {
        overflow: hidden;
        width: 100%;
        max-width: 1200px;
        margin: 20px auto;
        border-radius: 25px;
        box-shadow: 0 15px 40px rgba(0,0,0,0.15);
        border: 1px solid rgba(255,255,255,0.5);
        position: relative;
        z-index: 1;
    }
    
    .slide-images {
        width: 500%; /* 5 Images = 500% width */
        display: flex;
        /* Speed tez kar di hai: 12s total loop */
        animation: slide_animation 12s infinite ease-in-out; 
    }
    
    .img-container {
        width: 100%;
        height: 500px;
    }
    
    .img-container img {
        width: 100%;
        height: 100%;
        object-fit: cover;
    }

    /* Keyframes for 5 Images */
    @keyframes slide_animation {
        0% { margin-left: 0%; }
        15% { margin-left: 0%; }        /* Img 1 Ruka rahega */
        20% { margin-left: -100%; }     /* Slide to Img 2 */
        35% { margin-left: -100%; }     /* Img 2 Ruka rahega */
        40% { margin-left: -200%; }     /* Slide to Img 3 */
        55% { margin-left: -200%; }     /* Img 3 Ruka rahega */
        60% { margin-left: -300%; }     /* Slide to Img 4 */
        75% { margin-left: -300%; }     /* Img 4 Ruka rahega */
        80% { margin-left: -400%; }     /* Slide to Img 5 */
        95% { margin-left: -400%; }     /* Img 5 Ruka rahega */
        100% { margin-left: 0%; }       /* Back to Start */
    }

    /* --- 2. GLOBAL TEXT & EMOJI ANIMATIONS --- */
    /* Har Heading, Paragraph aur Image Load hote waqt animate karegi */
    h1, h2, h3, p, span, a {
        animation: fadeInUp 0.8s ease-out backwards;
    }
    
    /* Feature Icons (Emojis) ko BOUNCE effect diya hai */
    .feature-icon, .stMarkdown div[data-testid="stMetricValue"] {
        animation: popIn 0.8s cubic-bezier(0.68, -0.55, 0.265, 1.55) both;
    }

    @keyframes fadeInUp {
        from { opacity: 0; transform: translateY(30px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    @keyframes popIn {
        0% { transform: scale(0); opacity: 0; }
        80% { transform: scale(1.1); opacity: 1; }
        100% { transform: scale(1); }
    }

    /* --- 3. BACKGROUND PARTICLES (DIAMOND WIND) --- */
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

    /* --- 4. HERO & CARDS STYLING --- */
    .hero-container {
        text-align: center;
        padding: 60px 20px;
        border-radius: 30px;
        background: linear-gradient(-45deg, #ccfbf1, #d1fae5, #a7f3d0, #6ee7b7);
        background-size: 400% 400%;
        animation: gradientBG 15s ease infinite, popIn 1s ease-out; /* PopIn Animation Added */
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
        animation: fadeInUp 1s ease-out; /* Slide Up Added */
    }
    .feature-card:hover {
        transform: perspective(1000px) rotateX(5deg) rotateY(-5deg) translateY(-10px);
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
        animation: popIn 1.2s ease-out; /* Pop In */
    }
    .cta-button:hover {
        transform: scale(1.05);
        box-shadow: 0 15px 35px rgba(16,185,129,0.6);
    }

    /* --- 5. SIDEBAR STYLING --- */
    [data-testid="stSidebar"] {
        background-image: linear-gradient(180deg, #064e3b 0%, #047857 100%);
        border-right: none;
    }
    [data-testid="stSidebar"] * {
        color: #ecfdf5 !important;
    }
    
    @keyframes float-and-glow {
        0% { transform: translateY(0px); box-shadow: 0 0 10px rgba(255,255,255,0.1); }
        50% { transform: translateY(-10px); box-shadow: 0 0 30px rgba(16, 185, 129, 0.6); }
        100% { transform: translateY(0px); box-shadow: 0 0 10px rgba(255,255,255,0.1); }
    }

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
    
    img {
        border-radius: 20px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.1);
    }
    
    .result-box {
        padding: 30px;
        border-radius: 25px;
        text-align: center;
        background: rgba(255,255,255,0.9);
        box-shadow: 0 15px 30px rgba(0,0,0,0.08);
        animation: popIn 0.5s ease-out;
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
    # --- HERO SECTION ---
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
    
    # --- SLIDESHOW SECTION (UPDATED - 5 IMAGES & FASTER) ---
    st.markdown("""
    <div class="slider-frame">
        <div class="slide-images">
            <div class="img-container">
                <img src="https://images.unsplash.com/photo-1625246333195-78d9c38ad449?w=1200">
            </div>
            <div class="img-container">
                <img src="https://images.unsplash.com/photo-1586771107445-d3ca888129ff?w=1200">
            </div>
            <div class="img-container">
                <img src="https://images.unsplash.com/photo-1530836369250-ef72a3f5cda8?w=1200">
            </div>
            <div class="img-container">
                <img src="https://images.unsplash.com/photo-1595841696677-6489ff3f8cd1?w=1200">
            </div>
             <div class="img-container">
                <img src="https://images.unsplash.com/photo-1551754655-cd27e38d2076?w=1200">
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # --- TRUST INDICATORS ---
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
                <div class="feature-icon" style="font-size:3rem; margin-bottom:10px; width:auto; height:auto; background:none; box-shadow:none;">{icon}</div>
                <h2 style="margin:0; color:#064e3b; font-weight:800; font-size:2rem;">{value}</h2>
                <p style="font-weight:600; color:#555; margin:0;">{label}</p>
            </div>
            """, unsafe_allow_html=True)

    # --- HOW IT WORKS ---
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
                <div class="feature-icon">{icon}</div>
                <h3 style="color:#064e3b; font-weight:700;">{title}</h3>
                <p style="color:#555;">{desc}</p>
            </div>
            """, unsafe_allow_html=True)

    # --- SUPPORTED CROPS ---
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
                <div style="font-size:4.5rem; margin-bottom:15px;" class="feature-icon">{icon}</div>
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