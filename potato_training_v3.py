# potato_training_v3.py
import os
import cv2
import numpy as np
import joblib
import warnings
warnings.filterwarnings('ignore')
from collections import Counter

import albumentations as A
from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.preprocessing import StandardScaler 
from sklearn.feature_selection import SelectKBest, f_classif
from sklearn.calibration import CalibratedClassifierCV
from sklearn.utils.class_weight import compute_sample_weight
from skimage.feature import hog, local_binary_pattern, graycomatrix, graycoprops
import matplotlib.pyplot as plt
import seaborn as sns

# --- CONFIG ---
DATASET_PATH = r"D:\mega plant dataset\PlantvillageFYP"
CLASSES = [
    "Potato___Early_blight",
    "Potato___Late_blight",
    "Potato___healthy"
]
CLASS_NAMES = ["Early Blight", "Late Blight", "Healthy"]
IMG_SIZE = (128, 128)

# ============================================================
# PREPROCESSING
# ============================================================
def preprocess_image(img):
    img = cv2.resize(img, IMG_SIZE)

    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    lower = np.array([15, 20, 20])
    upper = np.array([100, 255, 255])
    mask  = cv2.inRange(hsv, lower, upper)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5,5))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN,  kernel)

    # Fill background with mean color (better than black)
    mean_color = cv2.mean(img, mask=mask)[:3]
    background = np.ones_like(img, dtype=np.uint8)
    background[:] = [int(c) for c in mean_color]
    img = np.where(mask[:,:,None] == 0, background, img).astype(np.uint8)

    # CLAHE
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8,8))
    lab[:,:,0] = clahe.apply(lab[:,:,0])
    img = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

    # Gray World color constancy
    img_f = img.astype(np.float32)
    avg   = [img_f[:,:,c].mean() for c in range(3)]
    avg_gray = sum(avg) / 3.0
    for c in range(3):
        if avg[c] > 0:
            img_f[:,:,c] *= avg_gray / avg[c]
    return np.clip(img_f, 0, 255).astype(np.uint8)

# ============================================================
# FEATURE EXTRACTION
# ============================================================
def extract_gabor(gray):
    feats = []
    for theta in range(4):
        theta_rad = theta * np.pi / 4
        for freq in [0.1, 0.3, 0.5]:
            lam = 1.0/freq if freq > 0 else 1.0
            kernel = cv2.getGaborKernel(
                (21,21), 5.0, theta_rad, lam, 0.5, 0, ktype=cv2.CV_32F)
            filtered = cv2.filter2D(gray, cv2.CV_32F, kernel)
            feats.extend([filtered.mean(), filtered.std(),
                          np.percentile(filtered, 25),
                          np.percentile(filtered, 75)])
    return np.array(feats)

def extract_orb(img):
    orb  = cv2.ORB_create(nfeatures=300)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, des = orb.detectAndCompute(gray, None)
    if des is None or len(des) == 0:
        return np.zeros(32)
    return np.mean(des, axis=0).astype(np.float32)

def extract_features(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    hsv  = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    # Color histograms
    hist_bgr = cv2.calcHist([img],[0,1,2],None,[16,16,16],[0,256,0,256,0,256])
    hist_bgr = cv2.normalize(hist_bgr, hist_bgr).flatten()
    hist_hsv = cv2.calcHist([hsv],[0,1,2],None,[16,16,16],[0,180,0,256,0,256])
    hist_hsv = cv2.normalize(hist_hsv, hist_hsv).flatten()

    # Color moments
    color_moments = []
    for c in range(3):
        ch = img[:,:,c].astype(np.float32)
        color_moments.extend([ch.mean(), ch.std(),
                               np.percentile(ch,25), np.percentile(ch,75)])
    f_color = np.hstack([hist_bgr, hist_hsv, color_moments])

    # Multi-scale HOG
    f_hog = []
    f_hog.extend(hog(gray, orientations=9, pixels_per_cell=(8,8),
                     cells_per_block=(2,2), visualize=False))
    f_hog.extend(hog(gray, orientations=9, pixels_per_cell=(16,16),
                     cells_per_block=(2,2), visualize=False))
    small = cv2.resize(gray, (IMG_SIZE[0]//2, IMG_SIZE[1]//2))
    f_hog.extend(hog(small, orientations=9, pixels_per_cell=(8,8),
                     cells_per_block=(2,2), visualize=False))
    f_hog = np.array(f_hog)

    # Multi-scale LBP
    f_lbp = []
    for r, p in [(1,8),(2,16),(3,24)]:
        lbp = local_binary_pattern(gray, p, r, method='uniform')
        h, _ = np.histogram(lbp.ravel(), bins=np.arange(0,p+3),
                            range=(0,p+2))
        h = h.astype("float"); h /= (h.sum()+1e-7)
        f_lbp.extend(h)
    f_lbp = np.array(f_lbp)

    # GLCM
    glcm = graycomatrix(gray, distances=[1,2,3],
                        angles=[0,np.pi/4,np.pi/2,3*np.pi/4],
                        levels=256, symmetric=True, normed=True)
    f_glcm = np.array([graycoprops(glcm,p).mean()
                        for p in ['contrast','correlation','energy',
                                  'homogeneity','dissimilarity','ASM']])

    # Gabor + ORB
    f_gabor = extract_gabor(gray)
    f_orb   = extract_orb(img)

    return np.hstack([f_color, f_hog, f_lbp, f_glcm, f_gabor, f_orb])

# ============================================================
# AUGMENTATION
# ============================================================
def get_aug_pipeline():
    return A.Compose([
        A.RandomRotate90(p=0.5),
        A.Flip(p=0.5),
        A.ShiftScaleRotate(shift_limit=0.1, scale_limit=0.2,
                           rotate_limit=45, p=0.7),
        A.RandomBrightnessContrast(brightness_limit=0.4,
                                   contrast_limit=0.4, p=0.8),
        A.HueSaturationValue(hue_shift_limit=20, sat_shift_limit=30,
                             val_shift_limit=20, p=0.6),
        A.GaussNoise(var_limit=(10,50), p=0.3),
        A.Blur(blur_limit=3, p=0.2),
        A.CoarseDropout(max_holes=6, max_height=24, max_width=24,
                        min_holes=1, fill_value=0, p=0.3),
    ])

def augment(img, n=10):
    pipe = get_aug_pipeline()
    return [pipe(image=img)['image'] for _ in range(n)]

# ============================================================
# STEP 1: PATHS + SPLIT
# ============================================================
print("="*55)
print("POTATO v3 — XGBoost + Advanced Features")
print("="*55)

all_paths, all_labels = [], []
for idx, cls in enumerate(CLASSES):
    folder = os.path.join(DATASET_PATH, cls)
    if not os.path.exists(folder):
        print(f"  Skip: {cls}"); continue
    imgs = [f for f in os.listdir(folder)
            if f.lower().endswith(('.jpg','.jpeg','.png'))]
    print(f"  {cls}: {len(imgs)}")
    for im in imgs:
        all_paths.append(os.path.join(folder, im))
        all_labels.append(idx)

print(f"\n  Total: {len(all_paths)}")

train_paths, test_paths, y_train_p, y_test_p = train_test_split(
    all_paths, all_labels, test_size=0.2,
    random_state=42, stratify=all_labels)
print(f"  Train: {len(train_paths)} | Test: {len(test_paths)}")

# ============================================================
# STEP 2: TEST SET — clean
# ============================================================
print("\nSTEP 2: Clean test set...")
X_test_l, y_test_l = [], []
for p, lbl in zip(test_paths, y_test_p):
    try:
        img = cv2.imread(p)
        if img is None: continue
        img = preprocess_image(img)
        X_test_l.append(extract_features(img))
        y_test_l.append(lbl)
    except: pass

X_test = np.array(X_test_l)
y_test = np.array(y_test_l)
print(f"  Test: {len(X_test)} samples | Features: {X_test.shape[1]}")

# ============================================================
# STEP 3: TRAIN SET + AUGMENTATION
# ============================================================
print("\nSTEP 3: Train + Augmentation (10x)...")
X_train_l, y_train_l = [], []

for i, (p, lbl) in enumerate(zip(train_paths, y_train_p)):
    try:
        img = cv2.imread(p)
        if img is None: continue
        img = cv2.resize(img, IMG_SIZE)
        img_proc = preprocess_image(img)

        # Original
        X_train_l.append(extract_features(img_proc))
        y_train_l.append(lbl)

        # 10 augmented
        for aug_img in augment(img, n=10):
            aug_proc = preprocess_image(aug_img)
            X_train_l.append(extract_features(aug_proc))
            y_train_l.append(lbl)
    except: pass

    if (i+1) % 200 == 0:
        print(f"  {i+1}/{len(train_paths)}...")

X_train = np.array(X_train_l)
y_train = np.array(y_train_l)
print(f"  Train: {len(X_train)} samples")

# ============================================================
# STEP 4: SCALING + FEATURE SELECTION
# ============================================================
X_train = np.nan_to_num(X_train, nan=0.0, posinf=0.0, neginf=0.0)
X_test  = np.nan_to_num(X_test,  nan=0.0, posinf=0.0, neginf=0.0)

scaler = StandardScaler()
X_train_s = scaler.fit_transform(X_train)
X_test_s  = scaler.transform(X_test)

selector = SelectKBest(f_classif, k=min(2000, X_train.shape[1]))
X_train_sel = selector.fit_transform(X_train_s, y_train)
X_test_sel  = selector.transform(X_test_s)
print(f"\n  Selected features: {X_train_sel.shape[1]}")

# ============================================================
# STEP 5: XGBOOST TRAINING (XGBoost 2.0.3 Compatible)
# ============================================================

print("\nSTEP 5: Training XGBoost...")
sample_w = compute_sample_weight('balanced', y_train)

xgb = XGBClassifier(
    n_estimators=1000,
    max_depth=8,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    min_child_weight=3,
    gamma=0.1,
    reg_alpha=0.1,
    reg_lambda=1.0,
    random_state=42,
    n_jobs=2,
    tree_method='hist',
    eval_metric='mlogloss',
    verbosity=1
)

# XGBoost 2.0.3 mein early_stopping_rounds .fit() mein chalta hai
xgb.fit(X_train_sel, y_train,
        sample_weight=sample_w,
        eval_set=[(X_test_sel, y_test)],
        early_stopping_rounds=50,
        verbose=True)

print("\n  Calibrating (Pre-fit mode)...")
model = CalibratedClassifierCV(xgb, method='isotonic', cv='prefit')
model.fit(X_train_sel, y_train)

# ============================================================
# STEP 6: RESULTS
# ============================================================
y_pred   = model.predict(X_test_sel)
test_acc = accuracy_score(y_test, y_pred)*100
tr_acc   = accuracy_score(y_train, model.predict(X_train_sel))*100
gap      = tr_acc - test_acc

print(f"\n  Train: {tr_acc:.2f}%")
print(f"  Test:  {test_acc:.2f}%")
print(f"  Gap:   {gap:.2f}%", end=" ")
if gap<5: print("No overfitting!")
elif gap<10: print("Thoda — OK")
else: print("Overfitting!")

print("\n--- Report ---")
print(classification_report(y_test, y_pred, target_names=CLASS_NAMES))

# ============================================================
# STEP 7: CROSS VALIDATION (Fresh Model - No Data Leakage)
# ============================================================
import gc
try:
    del X_train_l, y_train_l, X_test_l, y_test_l, X_train, X_test 
except NameError:
    pass
gc.collect()

print("\n  Calculating 5-Fold CV...")

# CV ke liye FRESH model — bina eval_set/early_stopping ke
xgb_cv = XGBClassifier(
    n_estimators=500,
    max_depth=8,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    min_child_weight=3,
    gamma=0.1,
    reg_alpha=0.1,
    reg_lambda=1.0,
    random_state=42,
    n_jobs=2,
    tree_method='hist',
    eval_metric='mlogloss',
    verbosity=0
)

cv_sc = cross_val_score(xgb_cv, X_train_sel, y_train, cv=5, n_jobs=2, scoring='accuracy')
print(f"  5-Fold CV: {cv_sc.mean()*100:.2f}% +/- {cv_sc.std()*100:.2f}%")

# ============================================================
# STEP 8: CONFUSION MATRIX PLOT
# ============================================================
plt.figure(figsize=(8,6))
sns.heatmap(confusion_matrix(y_test,y_pred), annot=True, fmt='d',
            cmap='Greens', xticklabels=CLASS_NAMES,
            yticklabels=CLASS_NAMES)
plt.title('Potato Disease — XGBoost v3')
plt.tight_layout()
plt.savefig('potato_v3_confusion_matrix.png', dpi=150)
plt.show()

# ============================================================
# STEP 9: SAVE
# ============================================================
joblib.dump({
    "model": model, "scaler": scaler,
    "selector": selector, "class_names": CLASS_NAMES,
    "img_size": IMG_SIZE
}, "potato_disease_model_v3.pkl")
print("\n  potato_disease_model_v3.pkl saved!")  