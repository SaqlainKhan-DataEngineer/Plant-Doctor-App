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

# --- 2. ADVANCED ANIMATED CSS (UPDATED FOR BEAUTY) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Poppins', sans-serif;
    }
    
    /* --- ANIMATIONS --- */
    @keyframes slideUp {
        from { opacity: 0; transform: translateY(40px); }
        to { opacity: 1; transform: translateY(0); }
    }
    @keyframes pulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.1); filter: drop-shadow(0 0 8px rgba(255,255,255,0.4)); }
        100% { transform: scale(1); }
    }
    @keyframes float {
        0% { transform: translateY(0px); }
        50% { transform: translateY(-15px); }
        100% { transform: translateY(0px); }
    }

    /* --- SIDEBAR STYLING --- */
    [data-testid="stSidebar"] {
        background-image: linear-gradient(180deg, #052e16 0%, #115e59 100%); 
        border-right: 3px solid #004d40;
    }
    [data-testid="stSidebar"] * {
        color: #e0f2f1 !important;
    }
    .sidebar-logo {
        display: block;
        margin: 0 auto;
        animation: pulse 2.5s infinite;
        font-size: 4.5rem;
        text-align: center;
    }
    
    /* Navigation Menu */
    [data-testid="stSidebar"] .stRadio div[role="radiogroup"] label {
        background: rgba(255, 255, 255, 0.05);
        padding: 10px 15px;
        border-radius: 10px;
        margin-bottom: 8px;
        transition: all 0.3s ease;
        border: 1px solid transparent;
    }
    [data-testid="stSidebar"] .stRadio div[role="radiogroup"] label:hover {
        background: rgba(255, 255, 255, 0.15);
        transform: translateX(5px);
        border-left: 4px solid #10b981;
    }
    [data-testid="stSidebar"] .stRadio div[role="radiogroup"] div[aria-checked="true"] + div + label {
         background: rgba(16, 185, 129, 0.2) !important;
         border-left: 4px solid #10b981 !important;
         font-weight: 600;
    }

    /* --- MAIN PAGE STYLING --- */
    .stApp {
        background: linear-gradient(135deg, #f0f9ff 0%, #dcfce7 100%);
    }

    /* --- NEW & IMPROVED HERO SECTION --- */
    .hero-container {
        text-align: center;
        padding: 50px 20px;
        /* Premium Gradient Background */
        background: linear-gradient(135deg, #ffffff 0%, #e8f5e9 100%);
        border-radius: 25px;
        /* Soft Shadow */
        box-shadow: 0 20px 40px rgba(0,0,0,0.1);
        margin-bottom: 40px;
        border: 2px solid #a7f3d0; /* Soft Green Border */
        animation: slideUp 0.8s ease-out; 
    }
    .animated-icon-hero {
        display: inline-block;
        animation: float 3s ease-in-out infinite;
        font-size: 5rem; /* Icon thora bara kiya */
        margin-bottom: 10px;
    }
    .hero-title {
        /* Gradient Text Effect */
        background: -webkit-linear-gradient(45deg, #1b5e20, #10b981);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        margin-bottom: 15px;
        font-size: 3.5rem; /* Text size barhaya */
        letter-spacing: -1.5px;
    }
    .hero-subtitle {
        color: #555;
        font-size: 1.3rem;
        font-weight: 300;
    }

    /* Feature Cards */
    .feature-card {
        background: white;
        padding: 25px;
        border-radius: 20px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.05);
        text-align: center;
        transition: transform 0.3s ease;
        border-top: 5px solid #10b981;
        animation: slideUp 0.8s ease-out 0.3s backwards;
        min-height: 300px; 
        display: flex;
        flex-direction: column;
        justify-content: center; 
        align-items: center;
    }
    .feature-card:hover {
        transform: translateY(-15px);
        box-shadow: 0 20px 40px rgba(0,0,0,0.15);
    }
    .feature-icon {
        font-size: 3rem;
        margin-bottom: 20px;
        background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%);
        width: 90px;
        height: 90px;
        line-height: 90px;
        border-radius: 50%;
        color: #059669;
        box-shadow: 0 5px 15px rgba(16, 185, 129, 0.2);
    }

    img {
        border-radius: 20px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.15);
        animation: slideUp 1s ease-out;
    }
    
    .result-box {
        padding: 25px;
        border-radius: 20px;
        text-align: center;
        margin-bottom: 25px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.08);
        animation: slideUp 0.5s ease-out;
    }
    .treatment-card {
        background: white;
        padding: 25px;
        border-radius: 20px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        margin-top: 20px;
        animation: slideUp 0.6s ease-out 0.2s backwards;
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
st.sidebar.markdown("<div class='sidebar-logo'>🌱</div>", unsafe_allow_html=True)
st.sidebar.markdown("<h2 style='text-align: center; color: white; margin-top: -15px;'>Plant Doctor</h2>", unsafe_allow_html=True)
st.sidebar.markdown("<p style='text-align: center; font-size: 0.8rem; opacity: 0.7; margin-bottom: 20px;'>AI Based Detection</p>", unsafe_allow_html=True)

nav = st.sidebar.radio("", ["🏠 Home Page", "🥔 Potato (Aloo)", "🍅 Tomato Check", "🌽 Corn Field"])

st.sidebar.write("---")

with st.sidebar.expander("📸 Achi Tasveer Kaise Lein?"):
    st.markdown("""
    1. **Roshni:** Tasveer din ki roshni mein lein.
    2. **Focus:** Sirf pattay (leaf) par focus karein.
    3. **Background:** Saada background rakhne ki koshish karein.
    4. **Safayi:** Dhundli tasveer se result ghalat ho sakta hai.
    """)

st.sidebar.write("---")
st.sidebar.info("**Developed by:**\n\n👨‍💻 **Saqlain Khan**\n(Data Engineer)\n\n👨‍💻 **Raheel Chishti**\n(Team Member)")

# --- 5. MAIN LOGIC ---
if nav == "🏠 Home Page":
    # --- HERO SECTION (NEW LOOK) ---
    st.markdown("""
    <div class="hero-container">
        <div class="animated-icon-hero">🌿</div>
        <h1 class="hero-title">Smart Farming Assistant</h1>
        <p class="hero-subtitle">Apni fasal ko bimariyon se bachayein, Jadid AI Technology ki madad se.</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.image("https://images.unsplash.com/photo-1625246333195-78d9c38ad449?w=1200", use_column_width=True)
    
    st.write("") 
    st.write("") 

    st.markdown("<h2 style='text-align: center; color: #064e3b; margin-bottom: 40px; font-weight: 700; animation: slideUp 1s ease-out;'>Why Choose This App?</h2>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-icon">📸</div>
            <h3>Instant Scan</h3>
            <p>Pattay ki tasveer upload karein aur foran nateeja payein.</p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-icon">💊</div>
            <h3>Expert Cure</h3>
            <p>Bimari ke mutabiq makhsoos dawayi aur ilaj janlein.</p>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-icon">🛡️</div>
            <h3>Prevention</h3>
            <p>Fasal ko mustaqbil ki bimariyon se mehfooz rakhne ke tareeqay.</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("<p style='text-align: center; color: #777; font-size: 0.9rem;'>© 2025 Plant Doctor AI | Designed with ❤️ by Saqlain & Raheel</p>", unsafe_allow_html=True)


elif nav == "🥔 Potato (Aloo)":
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
            with st.spinner("🤖 AI pattay ko ghor se dekh raha hai..."):
                time.sleep(1.5)
            
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
                        <h2 style='color: {border_color}; margin:0;'>{clean_label}</h2>
                        <h4 style='color: {border_color}; margin-top: 10px;'>{status_msg}</h4>
                        <p style='margin-top: 5px; color: #555;'>Confidence: {conf:.1f}%</p>
                    </div>
                """, unsafe_allow_html=True)

                if is_healthy:
                    st.balloons()
                    st.markdown("""
                    <div class='treatment-card' style='border-left: 5px solid #059669;'>
                        <h3 style='color: #059669;'>🎉 Mubarak Ho!</h3>
                        <p>Aapki fasal bilkul theek hai. Hifazat ke liye ye karein:</p>
                        <ul style='font-size: 1.1rem; line-height: 1.8;'>
                            <li>💧 <b>Pani:</b> Waqt par pani dein.</li>
                            <li>👀 <b>Nigrani:</b> Rozana pattay check karein.</li>
                            <li>🌱 <b>Khad:</b> Balanced NPK fertilizer use karein.</li>
                        </ul>
                    </div>
                    """, unsafe_allow_html=True)
                    
                elif "late" in clean_label.lower():
                    st.markdown("""
                    <div class='treatment-card' style='border-left: 5px solid #dc2626;'>
                        <h3 style='color: #dc2626;'>💊 Late Blight Ka Ilaj</h3>
                        <ul style='font-size: 1.1rem; line-height: 1.8;'>
                            <li><b>1. Chemical:</b> Metalaxyl + Mancozeb (2.5g/liter) spray karein.</li>
                            <li><b>2. Schedule:</b> Har 7-10 din baad spray dohrayein.</li>
                            <li><b>3. Warning:</b> Ye bimari tezi se phailti hai, foran action lein.</li>
                        </ul>
                    </div>
                    """, unsafe_allow_html=True)
                    
                elif "early" in clean_label.lower():
                    st.markdown("""
                    <div class='treatment-card' style='border-left: 5px solid #d97706;'>
                        <h3 style='color: #d97706;'>💊 Early Blight Ka Ilaj</h3>
                        <ul style='font-size: 1.1rem; line-height: 1.8;'>
                            <li><b>1. Chemical:</b> Chlorothalonil ya Azoxystrobin spray karein.</li>
                            <li><b>2. Organic:</b> Neem Oil ka spray bihtareen hai.</li>
                            <li><b>3. Safai:</b> Zameen se lagne walay purane pattay hata dein.</li>
                        </ul>
                    </div>
                    """, unsafe_allow_html=True)
                
                else:
                    st.info("Is result ke liye filhal koi makhsoos ilaj available nahi hai.")

elif nav in ["🍅 Tomato Check", "🌽 Corn Field"]:
    st.info("🚧 Coming Soon ...") 
    