import streamlit as st
from PIL import Image
import torch
from transformers import AutoImageProcessor, AutoModelForImageClassification
import time

# --- 1. PAGE SETUP ---
st.set_page_config(
    page_title="Plant Doctor AI", 
    page_icon="🌿", 
    layout="wide"
)

# --- 2. PROFESSIONAL CSS STYLING ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Poppins', sans-serif;
    }
    
    .stApp {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    }

    /* Sidebar Styling */
    [data-testid="stSidebar"] {
        background-color: #1b5e20;
        background-image: linear-gradient(180deg, #1b5e20 0%, #43a047 100%);
    }
    [data-testid="stSidebar"] * {
        color: white !important;
    }

    /* Global Image Styling */
    img {
        border-radius: 15px;
    }

    /* Home Page Cards */
    .hero-title {
        color: #1b5e20;
        text-align: center;
        font-weight: 700;
        margin-bottom: 10px;
    }
    .hero-subtitle {
        color: #555;
        text-align: center;
        margin-bottom: 30px;
        font-size: 1.2rem;
    }
    .feature-card {
        background: white;
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        text-align: center;
        transition: transform 0.3s ease;
        margin-bottom: 20px;
    }
    .feature-card:hover {
        transform: translateY(-5px);
    }
    .feature-icon {
        font-size: 2.5rem;
        margin-bottom: 10px;
    }

    /* Potato Result Styling */
    .result-box {
        padding: 20px;
        border-radius: 15px;
        text-align: center;
        margin-bottom: 20px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.05);
    }
    .treatment-card {
        background: white;
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.1);
        margin-top: 15px;
        border-left: 5px solid #2e7d32;
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
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/628/628283.png", width=80)
st.sidebar.title("Plant Doctor AI")
st.sidebar.write("---")
nav = st.sidebar.radio("Navigation", ["🏠 Home", "🥔 Potato (Aloo)", "🍅 Tomato", "🌽 Corn"])
st.sidebar.write("---")
st.sidebar.info("Developed by:\n**Saqlain Khan**\nData Engineer")

# --- 5. MAIN LOGIC ---
if nav == "🏠 Home":
    # --- HERO SECTION ---
    st.markdown("<h1 class='hero-title'>🌿 Smart Farming Assistant</h1>", unsafe_allow_html=True)
    st.markdown("<p class='hero-subtitle'>Apni fasal ko bimariyon se bachayein, AI ki madad se.</p>", unsafe_allow_html=True)
    
    # --- COVER IMAGE (Fixed Error Here) ---
    st.image("https://images.unsplash.com/photo-1625246333195-78d9c38ad449?w=1200", use_column_width=True)
    
    st.write("") # Spacer
    st.write("") # Spacer

    # --- FEATURES SECTION (Cards) ---
    st.markdown("<h3 style='text-align: center; color: #1b5e20;'>Why Choose Us?</h3>", unsafe_allow_html=True)
    
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
    st.markdown("<p style='text-align: center; color: #777;'>© 2025 Plant Doctor AI | Powered by Hugging Face & Streamlit</p>", unsafe_allow_html=True)


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
            
            # Prediction Logic
            inputs = processor(images=image, return_tensors="pt")
            with torch.no_grad():
                outputs = model(**inputs)
                logits = outputs.logits
                idx = logits.argmax(-1).item()
            
            label = model.config.id2label[idx]
            clean_label = label.replace("_", " ").title()
            conf = torch.softmax(logits, dim=1)[0][idx].item() * 100
            
            # --- GUARDRAIL CHECK ---
            if conf < 90:
                st.error("⚠️ **Tasveer Pehchani Nahi Ja Rahi!**")
                st.warning(f"""
                **AI Confuse hai (Confidence: {conf:.1f}%):**
                1. Lagta hai ye **Aloo (Potato)** ka patta nahi hai.
                2. Ya tasveer bohat dhundli (blurry) hai.
                """)
            else:
                # --- LOGIC FIX (Healthy Case) ---
                is_healthy = "healthy" in clean_label.lower() or "healty" in clean_label.lower()

                if is_healthy:
                    bg_color = "#e8f5e9" # Light Green
                    border_color = "#2e7d32"
                    status_msg = "✅ Sab Theek Hai (All OK)"
                    clean_label = "Healthy (Sehatmand)"
                else:
                    bg_color = "#ffebee" # Light Red
                    border_color = "#c62828"
                    status_msg = "⚠️ Bimari Detected (Action Needed)"

                # Display Result Box
                st.markdown(f"""
                    <div class='result-box' style='background: {bg_color}; border: 2px solid {border_color};'>
                        <h2 style='color: {border_color}; margin:0;'>{clean_label}</h2>
                        <h4 style='color: {border_color}; margin-top: 10px;'>{status_msg}</h4>
                        <p style='margin-top: 5px; color: #555;'>Confidence: {conf:.1f}%</p>
                    </div>
                """, unsafe_allow_html=True)

                # Display Treatments
                if is_healthy:
                    st.balloons()
                    st.markdown("""
                    <div class='treatment-card' style='border-left: 5px solid #4caf50;'>
                        <h3 style='color: #2e7d32;'>🎉 Mubarak Ho!</h3>
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
                    <div class='treatment-card' style='border-left: 5px solid #d32f2f;'>
                        <h3 style='color: #d32f2f;'>💊 Late Blight Ka Ilaj</h3>
                        <ul style='font-size: 1.1rem; line-height: 1.8;'>
                            <li><b>1. Chemical:</b> Metalaxyl + Mancozeb (2.5g/liter) spray karein.</li>
                            <li><b>2. Schedule:</b> Har 7-10 din baad spray dohrayein.</li>
                            <li><b>3. Warning:</b> Ye bimari tezi se phailti hai, foran action lein.</li>
                        </ul>
                    </div>
                    """, unsafe_allow_html=True)
                    
                elif "early" in clean_label.lower():
                    st.markdown("""
                    <div class='treatment-card' style='border-left: 5px solid #ff9800;'>
                        <h3 style='color: #e65100;'>💊 Early Blight Ka Ilaj</h3>
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

    