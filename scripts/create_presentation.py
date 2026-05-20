"""
Generate Plant Doctor AI presentation (emerald theme, ~20 slides with CM).
Run: python scripts/create_presentation.py
"""
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

# Theme (DermaScan-style: clean header bar + light body)
EMERALD = RGBColor(0x05, 0x96, 0x69)
EMERALD_DARK = RGBColor(0x06, 0x4E, 0x3B)
MINT = RGBColor(0xEC, 0xFD, 0xF5)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
TEXT_DARK = RGBColor(0x1F, 0x29, 0x37)
TEXT_MUTED = RGBColor(0x37, 0x41, 0x51)
ACCENT_GOLD = RGBColor(0xD9, 0x77, 0x06)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "Plant_Doctor_AI_Presentation.pptx"
W, H = Inches(13.333), Inches(7.5)  # 16:9

# v3 model stats from training runs (test set)
V3_MODELS = [
    {
        "crop": "Potato",
        "emoji": "🥔",
        "n_classes": 3,
        "diseases": "Early Blight, Late Blight, Healthy",
        "test_acc": "99%",
        "train_acc": "—",
        "cv": "—",
        "gap": "Minimal",
        "cm_file": "potato_v3_confusion_matrix.png",
        "model_file": "potato_disease_model_v3.pkl",
    },
    {
        "crop": "Tomato",
        "emoji": "🍅",
        "n_classes": 9,
        "diseases": "Bacterial Spot, Early/Late Blight, Leaf Mold, Septoria, Target Spot, YLCV, Mosaic, Healthy",
        "test_acc": "87%",
        "train_acc": "94%",
        "cv": "84%",
        "gap": "7% (acceptable)",
        "cm_file": "tomato_v3_confusion_matrix.png",
        "model_file": "tomato_disease_model_v3.pkl",
    },
    {
        "crop": "Pepper",
        "emoji": "🫑",
        "n_classes": 2,
        "diseases": "Bacterial Spot, Healthy",
        "test_acc": "98%",
        "train_acc": "100%",
        "cv": "—",
        "gap": "1.6% (no overfitting)",
        "cm_file": "pepper_v3_confusion_matrix.png",
        "model_file": "pepper_disease_model_v3.pkl",
    },
    {
        "crop": "Corn",
        "emoji": "🌽",
        "n_classes": 4,
        "diseases": "Blight, Common Rust, Gray Leaf Spot, Healthy",
        "test_acc": "99%",
        "train_acc": "100%",
        "cv": "98%",
        "gap": "1.2% (no overfitting)",
        "cm_file": "corn_v3_confusion_matrix.png",
        "model_file": "corn_disease_model_v3.pkl",
    },
]


def blank_slide(prs, layout_idx=6):
    return prs.slides.add_slide(prs.slide_layouts[layout_idx])


def add_header_bar(slide, title, subtitle=None):
    """Top emerald bar with title."""
    bar = slide.shapes.add_shape(1, Inches(0), Inches(0), W, Inches(1.35))
    bar.fill.solid()
    bar.fill.fore_color.rgb = EMERALD_DARK
    bar.line.fill.background()
    tb = slide.shapes.add_textbox(Inches(0.55), Inches(0.22), Inches(12.2), Inches(0.75))
    p = tb.text_frame.paragraphs[0]
    p.text = title
    p.font.size = Pt(32)
    p.font.bold = True
    p.font.color.rgb = WHITE
    if subtitle:
        sb = slide.shapes.add_textbox(Inches(0.55), Inches(0.88), Inches(12.2), Inches(0.4))
        sp = sb.text_frame.paragraphs[0]
        sp.text = subtitle
        sp.font.size = Pt(14)
        sp.font.color.rgb = RGBColor(0xA7, 0xF3, 0xD0)


def add_footer(slide, text="Plant Doctor AI · FYP 2025"):
    fb = slide.shapes.add_textbox(Inches(0.5), Inches(7.05), Inches(12.3), Inches(0.35))
    fp = fb.text_frame.paragraphs[0]
    fp.text = text
    fp.font.size = Pt(10)
    fp.font.color.rgb = TEXT_MUTED
    fp.alignment = PP_ALIGN.RIGHT


def add_mint_background(slide):
    body_bg = slide.shapes.add_shape(1, Inches(0), Inches(1.35), W, H - Inches(1.35))
    body_bg.fill.solid()
    body_bg.fill.fore_color.rgb = MINT
    body_bg.line.fill.background()


def add_bullets(slide, items, left=0.65, top=1.65, width=12.0, height=5.2, size=20):
    box = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    tf = box.text_frame
    tf.word_wrap = True
    for i, item in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = item
        p.level = 0
        p.font.size = Pt(size)
        p.font.color.rgb = TEXT_DARK
        p.space_after = Pt(10)


def accuracy_overview_slide(prs):
    """Slide: 4 crops — disease count + test accuracy (from v3 training)."""
    slide = blank_slide(prs)
    add_mint_background(slide)
    add_header_bar(
        slide,
        "Results & Model Accuracy (v3 XGBoost)",
        "18 disease classes total · 74,000+ training images",
    )
    x0 = 0.55
    for i, m in enumerate(V3_MODELS):
        left = x0 + i * 3.15
        card = slide.shapes.add_shape(1, Inches(left), Inches(1.75), Inches(2.95), Inches(3.35))
        card.fill.solid()
        card.fill.fore_color.rgb = WHITE
        card.line.color.rgb = EMERALD
        lines = [
            (f"{m['emoji']} {m['crop']}", 20, True, EMERALD_DARK),
            (f"{m['n_classes']} disease classes", 13, False, TEXT_MUTED),
            (f"Test accuracy: {m['test_acc']}", 28, True, EMERALD if m["test_acc"] != "87%" else ACCENT_GOLD),
            (f"Train: {m['train_acc']}  ·  CV: {m['cv']}", 11, False, TEXT_MUTED),
            (m["gap"], 11, False, TEXT_MUTED),
        ]
        y = 2.0
        for text, sz, bold, color in lines:
            tb = slide.shapes.add_textbox(Inches(left + 0.15), Inches(y), Inches(2.65), Inches(0.55))
            p = tb.text_frame.paragraphs[0]
            p.text = text
            p.font.size = Pt(sz)
            p.font.bold = bold
            p.font.color.rgb = color
            p.alignment = PP_ALIGN.CENTER
            y += 0.52 if sz < 20 else 0.72
    add_bullets(
        slide,
        [
            "🥔 Potato 3 + 🍅 Tomato 9 + 🫑 Pepper 2 + 🌽 Corn 4 = 18 classes",
            "Tomato hardest (9 classes, real-field variation); Potato/Pepper/Corn 98–99% test",
            "Inference < 3 seconds per scan · .pkl models deployed on Streamlit",
        ],
        top=5.25,
        size=16,
    )
    add_footer(slide)


def confusion_matrices_grid_slide(prs):
    """One slide: all 4 v3 confusion matrix heatmaps (2×2)."""
    slide = blank_slide(prs)
    add_mint_background(slide)
    add_header_bar(slide, "v3 Confusion Matrices — All 4 Models", "Test-set predictions vs actual labels")

    layout = [
        (V3_MODELS[0], 0.4, 1.5, 6.15, 2.55),
        (V3_MODELS[1], 6.75, 1.5, 6.15, 2.55),
        (V3_MODELS[2], 0.4, 4.25, 6.15, 2.55),
        (V3_MODELS[3], 6.75, 4.25, 6.15, 2.55),
    ]
    for m, left, top, width, height in layout:
        path = ROOT / m["cm_file"]
        if path.exists():
            slide.shapes.add_picture(str(path), Inches(left), Inches(top), width=Inches(width))
        else:
            ph = slide.shapes.add_shape(1, Inches(left), Inches(top), Inches(width), Inches(height))
            ph.fill.solid()
            ph.fill.fore_color.rgb = WHITE
            ph.line.color.rgb = TEXT_MUTED
            pt = slide.shapes.add_textbox(Inches(left), Inches(top + height / 2 - 0.2), Inches(width), Inches(0.4))
            pp = pt.text_frame.paragraphs[0]
            pp.text = f"Missing: {m['cm_file']}"
            pp.alignment = PP_ALIGN.CENTER
        cap = slide.shapes.add_textbox(
            Inches(left), Inches(top + height + 0.02), Inches(width), Inches(0.38)
        )
        cp = cap.text_frame.paragraphs[0]
        cp.text = (
            f"{m['emoji']} {m['crop']} · {m['n_classes']} classes · Test {m['test_acc']}"
        )
        cp.font.size = Pt(11)
        cp.font.bold = True
        cp.font.color.rgb = EMERALD_DARK
        cp.alignment = PP_ALIGN.CENTER
    add_footer(slide)


def model_detail_slides(prs):
    """One slide per crop: large CM + metrics (panel explanation)."""
    for m in V3_MODELS:
        slide = blank_slide(prs)
        add_mint_background(slide)
        add_header_bar(
            slide,
            f"{m['emoji']} {m['crop']} Model — v3 XGBoost",
            f"{m['n_classes']} disease classes · {m['model_file']}",
        )
        path = ROOT / m["cm_file"]
        if path.exists():
            slide.shapes.add_picture(str(path), Inches(0.5), Inches(1.55), height=Inches(5.35))
        stats = slide.shapes.add_textbox(Inches(7.0), Inches(1.75), Inches(5.8), Inches(5.0))
        tf = stats.text_frame
        tf.word_wrap = True
        bullets = [
            f"Classes ({m['n_classes']}): {m['diseases']}",
            f"Test accuracy: {m['test_acc']}",
            f"Train accuracy: {m['train_acc']}",
            f"5-Fold CV: {m['cv']}",
            f"Generalization: {m['gap']}",
            "Features: HOG, LBP, GLCM, Gabor, ORB",
            "Classifier: XGBoost + Random Forest ensemble",
        ]
        for i, line in enumerate(bullets):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.text = f"• {line}"
            p.font.size = Pt(17)
            p.font.color.rgb = TEXT_DARK
            p.space_after = Pt(8)
        add_footer(slide)


def title_slide(prs):
    slide = blank_slide(prs)
    # Full emerald gradient block
    bg = slide.shapes.add_shape(1, Inches(0), Inches(0), W, H)
    bg.fill.solid()
    bg.fill.fore_color.rgb = EMERALD_DARK
    bg.line.fill.background()

    accent = slide.shapes.add_shape(1, Inches(0), Inches(0), W, Inches(0.12))
    accent.fill.solid()
    accent.fill.fore_color.rgb = EMERALD
    accent.line.fill.background()

    t1 = slide.shapes.add_textbox(Inches(0.8), Inches(2.0), Inches(11.5), Inches(1.2))
    p1 = t1.text_frame.paragraphs[0]
    p1.text = "🌿 Plant Doctor AI"
    p1.font.size = Pt(48)
    p1.font.bold = True
    p1.font.color.rgb = WHITE
    p1.alignment = PP_ALIGN.CENTER

    t2 = slide.shapes.add_textbox(Inches(0.8), Inches(3.2), Inches(11.5), Inches(0.9))
    p2 = t2.text_frame.paragraphs[0]
    p2.text = "Pakistani Kisanon Ka AI Doctor — AI-Powered Crop Disease Detection"
    p2.font.size = Pt(22)
    p2.font.color.rgb = RGBColor(0xA7, 0xF3, 0xD0)
    p2.alignment = PP_ALIGN.CENTER

    t3 = slide.shapes.add_textbox(Inches(0.8), Inches(4.5), Inches(11.5), Inches(1.4))
    tf = t3.text_frame
    lines = [
        "Saqlain Sajjad  ·  Roll No. 225218  ·  Data Engineer",
        "Raheel Chishti  ·  Roll No. 225186  ·  Team Member",
    ]
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = line
        p.font.size = Pt(18)
        p.font.color.rgb = WHITE
        p.alignment = PP_ALIGN.CENTER

    t4 = slide.shapes.add_textbox(Inches(0.8), Inches(6.2), Inches(11.5), Inches(0.5))
    p4 = t4.text_frame.paragraphs[0]
    p4.text = "Empowering Farmers, One Scan at a Time"
    p4.font.size = Pt(14)
    p4.font.italic = True
    p4.font.color.rgb = ACCENT_GOLD
    p4.alignment = PP_ALIGN.CENTER


def content_slide(prs, title, bullets, subtitle=None, two_col=None):
    slide = blank_slide(prs)
    # Mint background strip
    body_bg = slide.shapes.add_shape(1, Inches(0), Inches(1.35), W, H - Inches(1.35))
    body_bg.fill.solid()
    body_bg.fill.fore_color.rgb = MINT
    body_bg.line.fill.background()
    add_header_bar(slide, title, subtitle)

    if two_col:
        left, right = two_col
        lb = slide.shapes.add_textbox(Inches(0.55), Inches(1.55), Inches(6.0), Inches(0.45))
        lp = lb.text_frame.paragraphs[0]
        lp.text = left[0]
        lp.font.bold = True
        lp.font.size = Pt(18)
        lp.font.color.rgb = EMERALD_DARK
        add_bullets(slide, left[1], left=0.55, top=2.05, width=5.9, height=4.8, size=17)

        rb = slide.shapes.add_textbox(Inches(6.85), Inches(1.55), Inches(6.0), Inches(0.45))
        rp = rb.text_frame.paragraphs[0]
        rp.text = right[0]
        rp.font.bold = True
        rp.font.size = Pt(18)
        rp.font.color.rgb = EMERALD_DARK
        add_bullets(slide, right[1], left=6.85, top=2.05, width=5.9, height=4.8, size=17)
    else:
        add_bullets(slide, bullets)

    add_footer(slide)
    return slide


def build():
    prs = Presentation()
    prs.slide_width = W
    prs.slide_height = H

    title_slide(prs)

    content_slide(
        prs,
        "The Challenge in Modern Agriculture",
        [],
        two_col=(
            (
                "Problems",
                [
                    "Late diagnosis — diseases spotted after major crop damage",
                    "Expert shortage in rural Punjab & villages",
                    "Complex tools — no Urdu / Roman Urdu support",
                    "Farmers lose money; food security at risk",
                ],
            ),
            (
                "Impact",
                [
                    "Yield loss & wasted pesticides",
                    "Delayed treatment increases cost",
                    "Small farmers cannot afford consultants",
                    "National agriculture productivity suffers",
                ],
            ),
        ),
    )

    content_slide(
        prs,
        "Our Solution — The AI Doctor for Plants",
        [
            "Smartphone-friendly web app — no app store needed",
            "Upload leaf photo → diagnosis in under 3 seconds",
            "Roman Urdu + Urdu treatment advice via Google Gemini AI",
            "Live Lahore weather widget for safe spray timing",
            "Expert chat for farmer ↔ agricultural expert support",
            "Live: plantdoctorapp.streamlit.app",
        ],
    )

    content_slide(
        prs,
        "System Architecture",
        [
            "Frontend: Streamlit Cloud + custom CSS (glassmorphism UI)",
            "REST API: FastAPI on Railway.app (JWT, bcrypt, rate limits)",
            "Database: MySQL on Railway (users, scans, consultations, diseases)",
            "ML Inference: XGBoost .pkl models loaded in Streamlit (<3s)",
            "Generative AI: Gemini API for farmer-friendly advice text",
            "Email: SMTP / Resend for optional account verification",
        ],
    )

    content_slide(
        prs,
        "Machine Learning Engine",
        [
            "Dataset: 74,000+ labeled crop leaf images",
            "Models: Custom XGBoost + Random Forest classifiers (v3 .pkl)",
            "Classical CV features: HOG, LBP, GLCM, Gabor filters, ORB",
            "Auto crop detection before disease classification",
            "Compressed models for fast edge inference on Streamlit",
            "Confusion matrices & reports saved per crop training script",
        ],
    )

    content_slide(
        prs,
        "Supported Crops & 18 Disease Classes",
        [
            "🥔 Potato (3 classes) — Test 99%: Early Blight, Late Blight, Healthy",
            "🍅 Tomato (9 classes) — Test 87%: Bacterial Spot, Early/Late Blight, Leaf Mold, Septoria, Target Spot, YLCV, Mosaic, Healthy",
            "🫑 Pepper (2 classes) — Test 98%: Bacterial Spot, Healthy",
            "🌽 Corn (4 classes) — Test 99%: Blight, Common Rust, Gray Leaf Spot, Healthy",
            "Total: 18 disease classes · Roman Urdu names in UI",
        ],
    )

    content_slide(
        prs,
        "Key Platform Features",
        [
            "🔐 Secure JWT auth, roles: Farmer, Expert, Admin",
            "🔬 AI Quick Scan with confidence score & scan history",
            "👨‍⚕️ AI Doctor advice (Gemini) saved to MySQL per scan",
            "🌧️ Open-Meteo weather (temperature, wind, humidity)",
            "💬 Expert consultation requests",
            "📊 User dashboard — Plotly charts, crop & disease analytics",
            "🛡️ Admin panel — users, scans, platform stats",
        ],
    )

    content_slide(
        prs,
        "Database Architecture",
        [
            "Cloud MySQL (Railway) — production",
            "SQL Server — optional local dev (agnostic query wrapper)",
            "Table: users — auth, roles, email verification",
            "Table: scans — crop, disease, confidence, ai_advice, image (base64 JPEG)",
            "Table: consultations — farmer ↔ expert messages",
            "Table: diseases — knowledge base (symptoms, treatment, prevention)",
            "Relational design for history, analytics & admin reporting",
        ],
    )

    accuracy_overview_slide(prs)
    confusion_matrices_grid_slide(prs)
    model_detail_slides(prs)

    content_slide(
        prs,
        "Technology Stack & Deployment",
        [
            "Languages: Python 3.10+",
            "Frontend: Streamlit, Plotly, Custom HTML/CSS",
            "Backend: FastAPI, Uvicorn, SlowAPI, PyJWT, bcrypt",
            "ML: XGBoost, scikit-learn, OpenCV, scikit-image, joblib",
            "AI: Google Gemini API",
            "DB: MySQL (Railway), pymysql",
            "Deploy: GitHub → Streamlit Cloud + Railway Docker",
            "Integrations: SMTP/Resend, Open-Meteo",
        ],
    )

    content_slide(
        prs,
        "The Farmer's Journey (Demo Flow)",
        [
            "1. Register / Login (auto-verify if email not configured)",
            "2. Select crop page or auto-detect from photo",
            "3. Upload sick leaf image → XGBoost predicts disease",
            "4. Gemini generates Roman Urdu treatment steps",
            "5. Scan saved to cloud history + dashboard charts",
            "6. Optional: Expert chat for second opinion",
        ],
    )

    content_slide(
        prs,
        "Admin Dashboard & Analytics",
        [
            "Admin-only panel (role-based JWT)",
            "Platform stats: total users, scans, diseases detected",
            "Plotly visualizations — crop breakdown, disease trends",
            "View all users & recent scans across Pakistan",
            "Promote users to Expert role for consultations",
        ],
    )

    content_slide(
        prs,
        "Conclusion & Future Scope",
        [
            "Delivered end-to-end AI crop doctor for Pakistani farmers",
            "4 crops, 18 diseases, cloud auth, history, admin, expert chat",
            "Future: Wheat, Rice, Cotton models",
            "Mobile app / PWA offline with Edge AI on phone",
            "Regional disease heatmaps & Urdu full UI toggle",
            "Drone imagery for large-field monitoring",
        ],
    )

    # Thank you slide
    slide = blank_slide(prs)
    bg = slide.shapes.add_shape(1, Inches(0), Inches(0), W, H)
    bg.fill.solid()
    bg.fill.fore_color.rgb = EMERALD_DARK
    bg.line.fill.background()
    t = slide.shapes.add_textbox(Inches(0.8), Inches(2.4), Inches(11.5), Inches(2.5))
    tf = t.text_frame
    p0 = tf.paragraphs[0]
    p0.text = "Thank You!"
    p0.font.size = Pt(52)
    p0.font.bold = True
    p0.font.color.rgb = WHITE
    p0.alignment = PP_ALIGN.CENTER
    for line in [
        "Empowering agriculture with the speed of AI.",
        "",
        "🌐 plantdoctorapp.streamlit.app",
        "Questions welcome from the panel.",
    ]:
        p = tf.add_paragraph()
        p.text = line
        p.font.size = Pt(20)
        p.font.color.rgb = RGBColor(0xA7, 0xF3, 0xD0)
        p.alignment = PP_ALIGN.CENTER

    prs.save(OUT)
    print(f"Saved: {OUT}")


if __name__ == "__main__":
    build()
