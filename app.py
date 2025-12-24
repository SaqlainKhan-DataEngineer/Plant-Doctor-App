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

# --- 2. ANIMATED & PROFESSIONAL CSS ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Poppins', sans-serif;
    }
    
    /* --- 1. ANIMATIONS --- */
    /* Floating Animation (Main Page) */
    @keyframes float {
        0% { transform: translateY(0px); }
        50% { transform: translateY(-10px); }
        100% { transform: translateY(0px); }
    }
    
    /* Pulse Animation (Sidebar Logo) - Dhak Dhak */
    @keyframes pulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.1); filter: drop-shadow(0 0 10px rgba(255,255,255,0.3)); }
        100% { transform: scale(1); }
    }
    
    .animated-icon {
        display: inline-block;
        animation: float 3s ease-in-out infinite;
        font-size: 3rem;
    }
    
    .sidebar-logo {
        display: block;
        margin: 0 auto;
        animation: pulse 2s infinite; /* Ye sidebar wale ko zinda karega */
        font-size: 4rem;
        text-align: center;
    }

    /* --- 2. SIDEBAR STYLING (Deep Jungle + Sky Touch) --- */
    [data-testid="stSidebar"] {
        /* Green gradient with a hint of blue at bottom */
        background-image: linear-gradient(180deg, #052e16 0%, #115e59 100%); 
        border-right: 2px solid #004d40;
    }
    [data-testid="stSidebar"] * {
        color: #e0f2f1 !important; /* Thora sa safed-blueish text taake parha jaye */
    }
    [data-testid="stSidebarNav"] {
        padding-top: 20px;
    }

    /* --- 3. MAIN PAGE STYLING --- */
    /* Background: Halka sa Sky Blue touch */
    .stApp {
        background: linear-gradient(135deg, #f0f9ff 0%, #dcfce7 100%);
    }

    /* Hero Section */
    .hero-container {
        text-align: center;
        padding: 30px;
        background: white;
        border-radius: 20px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.08);
        margin-bottom: 30px;
        border-bottom: 5px solid #10b981; /* Bright Green Border */
    }
    .hero-title {
        color: #064e3b;
        font-weight: 700;
        margin-bottom: 5px;
        font-size: 2.8rem;
    }
    .hero-subtitle {
        color: #555;
        font-size: 1.2rem;
    }

    /* Feature Cards */
    .feature-card {
        background: white;
        padding: 25px;
        border-radius: 15px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        text-align: center;
        transition: transform 0.3s ease;
        border-top: 5px solid #10b981;
    }
    .feature-card:hover {
        transform: translateY(-8px);
        box-shadow: 0 10px 25px rgba(0,0,0,0.1);
    }
    .feature-icon {
        font-size: 2.5rem;
        margin-bottom: 15px;
        background: #ecfdf5;
        width: 70px;
        height: 70px;
        line-height: 70px;
        border-radius: 50%;
        margin: 0 auto 15px auto;
        color: #059669;
    }

    /* Image Styling */
    img {
        border-radius: 15px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    
    /* Result Box */
    .result-box {
        padding: 20px;
        border-radius: 15px;
        text-align: center;
        margin-bottom: 20px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.05);
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

# --- 4. SIDEBAR (Animated) ---
# Yahan humne Animation Class lagayi hai
st.sidebar.markdown("<div class='sidebar-logo'>🌱</div>", unsafe_allow_html=True)
st.sidebar.markdown("<h2 style='text-align: center; color: white;'>Plant Doctor</h2>", unsafe_allow_html=True)
st.sidebar.markdown("<p style='text-align: center; font-size: 0.9rem; opacity: 0.8;'>AI Based Detection</p>", unsafe_allow_html=True)
st.sidebar.write("---")

nav = st.sidebar.radio("Navigation", ["🏠 Home", "🥔 Potato (Aloo)", "🍅 Tomato", "🌽 Corn"])

st.sidebar.write("---")
st.sidebar.info("**Developed by:**\n\n👨‍💻 **Saqlain Khan**\n(Data Engineer)\n\n👨‍💻 **Raheel Chishti**\n(Team Member)")

# --- 5. MAIN LOGIC ---
if nav == "🏠 Home":
    # --- HERO SECTION ---
    st.markdown("""
    <div class="hero-container">
        <div class="animated-icon">🌿</div>
        <h1 class="hero-title">Smart Farming Assistant</h1>
        <p class="hero-subtitle">Apni fasal ko bimariyon se bachayein, AI ki madad se.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # --- COVER IMAGE ---
    st.image("https://images.unsplash.com/photo-1625246333195-78d9c38ad449?w=1200", use_column_width=True)
    
    st.write("") 
    st.write("") 

    # --- FEATURES SECTION ---
    st.markdown("<h3 style='text-align: center; color: #064e3b; margin-bottom: 30px;'>Why Choose This App?</h3>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-icon">📸</div>
            <h3>Instant Scan</h3>
            <p>Tasveer upload karein aur foran nateeja payein.</p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-icon">💊</div>
            <h3>Expert Cure</h3>
            <p>Har bimari ka makhsoos ilaj aur dawayi.</p>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-icon">🛡️</div>
            <h3>Prevention</h3>
            <p>Fasal ko mustaqbil mein mehfooz rakhne ke tareeqay.</p>
        </div>
        """, unsafe_allow_html=True)

    # --- FOOTER ---
    st.markdown("---")
    st.markdown("<p style='text-align: center; color: #777;'>© 2025 Plant Doctor AI | Designed by Saqlain & Raheel</p>", unsafe_allow_html=True)


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
            st.info("🔍 Analyzing image...")
            time.sleep(1) 
            
            # Prediction
            inputs = processor(images=image, return_tensors="pt")
            with torch.no_grad():
                outputs = model(**inputs)
                logits = outputs.logits
                idx = logits.argmax(-1).item()
            
            label = model.config.id2label[idx]
            clean_label = label.replace("_", " ").title()
            conf = torch.softmax(logits, dim=1)[0][idx].item() * 100
            
            # Guardrail
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
                    bg_color = "#ecfdf5" # Mint Green (Light Blueish Green)
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

elif nav in ["🍅 Tomato", "🌽 Corn"]:
    st.info("🚧 Coming Soon in few days...")

    