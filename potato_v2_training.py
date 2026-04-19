import os
import cv2
import numpy as np
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.preprocessing import StandardScaler
from skimage.feature import hog, local_binary_pattern, graycomatrix, graycoprops
import matplotlib.pyplot as plt
import seaborn as sns
import warnings
warnings.filterwarnings('ignore')

# --- CONFIG ---
DATASET_PATH = r"D:\PlantvillageFYP"
POTATO_CLASSES = [
    "Potato___Early_blight",
    "Potato___Late_blight",
    "Potato___healthy"
]
CLASS_NAMES = ["Early Blight", "Late Blight", "Healthy"]
IMG_SIZE = (128, 128)

# ============================================================
# PREPROCESSING — Same jo app.py mein hoga
# ============================================================
def preprocess_image(img):
    """
    Real world images ke liye preprocessing.
    App.py mein BILKUL same function hoga.
    """
    # CLAHE — lighting normalize
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    lab[:, :, 0] = clahe.apply(lab[:, :, 0])
    img = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

    # Color normalization — dataset vs real ka farq kam karo
    img = img.astype(np.float32)
    for c in range(3):
        ch = img[:, :, c]
        mn, mx = ch.min(), ch.max()
        if mx > mn:
            img[:, :, c] = (ch - mn) / (mx - mn) * 255
    img = img.astype(np.uint8)

    return img

# ============================================================
# FEATURE EXTRACTION — App.py se 100% match
# ============================================================
def extract_features(img):
    """
    Ek processed image se features nikalo.
    App.py mein BILKUL same rahega.
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Color Histogram — BGR + HSV
    hist_bgr = cv2.calcHist([img], [0,1,2], None,
                             [8,8,8], [0,256,0,256,0,256])
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    hist_hsv = cv2.calcHist([hsv], [0,1,2], None,
                             [8,8,8], [0,180,0,256,0,256])
    f_color = np.hstack([hist_bgr.flatten(), hist_hsv.flatten()])

    # HOG
    f_hog = hog(gray, orientations=9,
                pixels_per_cell=(8, 8),
                cells_per_block=(2, 2),
                visualize=False)

    # LBP
    radius, n_points = 2, 16
    lbp = local_binary_pattern(gray, n_points, radius, method='uniform')
    h_lbp, _ = np.histogram(lbp.ravel(),
                             bins=np.arange(0, n_points + 3),
                             range=(0, n_points + 2))
    h_lbp = h_lbp.astype("float")
    f_lbp = h_lbp / (h_lbp.sum() + 1e-7)

    # GLCM
    glcm = graycomatrix(gray, distances=[1, 2],
                        angles=[0, np.pi/4, np.pi/2, 3*np.pi/4],
                        levels=256, symmetric=True, normed=True)
    f_glcm = np.array([
        graycoprops(glcm, p).mean()
        for p in ['contrast','correlation','energy',
                  'homogeneity','dissimilarity']
    ])

    return np.hstack([f_color, f_hog, f_lbp, f_glcm])

# ============================================================
# AUGMENTATION — Real world conditions simulate karo
# ============================================================
def augment_image(img):
    """
    Real world conditions:
    - Alag lighting (tej dhoop, shadow, cloudy)
    - Alag angle (tilted phone)
    - Blur (door se photo, shaky hand)
    - Flip (patta ulta)
    """
    augmented = []
    h, w = img.shape[:2]

    # 1. Flip
    augmented.append(cv2.flip(img, 1))

    # 2. Dim — cloudy ya shadow
    augmented.append(cv2.convertScaleAbs(img, alpha=0.5, beta=0))

    # 3. Bright — tej dhoop
    augmented.append(cv2.convertScaleAbs(img, alpha=1.5, beta=30))

    # 4. Rotate 90
    r = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
    augmented.append(cv2.resize(r, IMG_SIZE))

    # 5. Rotate 45 — tilted phone
    M = cv2.getRotationMatrix2D((w//2, h//2), 45, 1.0)
    r45 = cv2.warpAffine(img, M, (w, h))
    augmented.append(cv2.resize(r45, IMG_SIZE))

    # 6. Blur — shaky/far camera
    augmented.append(cv2.GaussianBlur(img, (7, 7), 0))

    # 7. Center crop — zoom effect
    m = 20
    crop = img[m:h-m, m:w-m]
    augmented.append(cv2.resize(crop, IMG_SIZE))

    # 8. Yellow tint — sunny outdoor
    yellow = img.copy().astype(np.float32)
    yellow[:,:,2] = np.clip(yellow[:,:,2] * 1.3, 0, 255)
    yellow[:,:,1] = np.clip(yellow[:,:,1] * 1.1, 0, 255)
    augmented.append(yellow.astype(np.uint8))

    # 9. Blue tint — shade/indoor
    blue = img.copy().astype(np.float32)
    blue[:,:,0] = np.clip(blue[:,:,0] * 1.3, 0, 255)
    augmented.append(blue.astype(np.uint8))

    # 10. Random noise — phone camera noise
    noise = np.random.randint(-20, 20, img.shape, dtype=np.int16)
    noisy = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    augmented.append(noisy)

    return augmented  # 10 augmented versions

# ============================================================
# STEP 1: PATHS SPLIT — No data leakage
# ============================================================
print("=" * 55)
print("STEP 1: Collecting paths...")
print("=" * 55)

all_paths, all_labels = [], []

for label_idx, class_name in enumerate(POTATO_CLASSES):
    folder = os.path.join(DATASET_PATH, class_name)
    if not os.path.exists(folder):
        print(f"  Skip: {folder}")
        continue
    images = [f for f in os.listdir(folder)
              if f.lower().endswith(('.jpg','.jpeg','.png'))]
    print(f"  {class_name}: {len(images)}")
    for img_name in images:
        all_paths.append(os.path.join(folder, img_name))
        all_labels.append(label_idx)

print(f"\n  Total: {len(all_paths)}")

# Split paths — pehle split phir extract
train_paths, test_paths, y_train_paths, y_test_paths = train_test_split(
    all_paths, all_labels,
    test_size=0.2,
    random_state=42,
    stratify=all_labels
)
print(f"  Train: {len(train_paths)} | Test: {len(test_paths)}")

# ============================================================
# STEP 2: TEST SET — clean, no augmentation
# ============================================================
print("\n" + "=" * 55)
print("STEP 2: Processing clean test set...")
print("=" * 55)

X_test_list, y_test_list = [], []
for p, lbl in zip(test_paths, y_test_paths):
    try:
        img = cv2.imread(p)
        if img is None: continue
        img = cv2.resize(img, IMG_SIZE)
        img = preprocess_image(img)
        feats = extract_features(img)
        X_test_list.append(feats)
        y_test_list.append(lbl)
    except:
        pass

X_test = np.array(X_test_list)
y_test = np.array(y_test_list)
print(f"  Test set: {len(X_test)} samples")

# ============================================================
# STEP 3: TRAIN SET — original + 10 augmentations
# ============================================================
print("\n" + "=" * 55)
print("STEP 3: Augmenting train set (10x)...")
print("=" * 55)

X_train_list, y_train_list = [], []

for i, (p, lbl) in enumerate(zip(train_paths, y_train_paths)):
    try:
        img = cv2.imread(p)
        if img is None: continue
        img = cv2.resize(img, IMG_SIZE)
        img = preprocess_image(img)

        # Original
        feats = extract_features(img)
        X_train_list.append(feats)
        y_train_list.append(lbl)

        # 10 augmented
        for aug in augment_image(img):
            aug = cv2.resize(aug, IMG_SIZE)
            feats_aug = extract_features(aug)
            X_train_list.append(feats_aug)
            y_train_list.append(lbl)

    except:
        pass

    if (i+1) % 500 == 0:
        print(f"  {i+1}/{len(train_paths)} done...")

X_train = np.array(X_train_list)
y_train = np.array(y_train_list)
print(f"\n  Augmented train: {len(X_train)} samples")
print(f"  (Original + 10x aug = ~{len(train_paths)*11} expected)")

# ============================================================
# STEP 4: SCALING
# ============================================================
print("\n" + "=" * 55)
print("STEP 4: Scaling...")
print("=" * 55)

X_train = np.nan_to_num(X_train, nan=0.0, posinf=0.0, neginf=0.0)
X_test  = np.nan_to_num(X_test,  nan=0.0, posinf=0.0, neginf=0.0)

scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled  = scaler.transform(X_test)
print(f"  Feature size: {X_train.shape[1]}")

# ============================================================
# STEP 5: TRAINING
# ============================================================
print("\n" + "=" * 55)
print("STEP 5: Training...")
print("=" * 55)

model = RandomForestClassifier(
    n_estimators=500,       # Zyada trees = zyada stable
    max_depth=20,
    min_samples_split=5,
    min_samples_leaf=3,
    max_features='sqrt',
    class_weight='balanced',
    random_state=42,
    n_jobs=-1
)
model.fit(X_train_scaled, y_train)
print("  Done!")

# ============================================================
# STEP 6: EVALUATION
# ============================================================
print("\n" + "=" * 55)
print("STEP 6: Results...")
print("=" * 55)

y_pred    = model.predict(X_test_scaled)
test_acc  = accuracy_score(y_test, y_pred) * 100
train_acc = accuracy_score(y_train, model.predict(X_train_scaled)) * 100
gap = train_acc - test_acc

print(f"\n  Train: {train_acc:.2f}%")
print(f"  Test:  {test_acc:.2f}%")
print(f"  Gap:   {gap:.2f}%", end=" ")
if gap < 5:    print("No overfitting!")
elif gap < 10: print("Thoda — acceptable")
else:          print("Overfitting!")

print("\n--- Report ---")
print(classification_report(y_test, y_pred, target_names=CLASS_NAMES))

# CV
cv = cross_val_score(model, X_train_scaled, y_train, cv=5)
print(f"\n  5-Fold CV: {cv.mean()*100:.2f}% +/- {cv.std()*100:.2f}%")

# Confusion Matrix
plt.figure(figsize=(8, 6))
cm = confusion_matrix(y_test, y_pred)
sns.heatmap(cm, annot=True, fmt='d', cmap='Greens',
            xticklabels=CLASS_NAMES, yticklabels=CLASS_NAMES)
plt.title('Potato Disease Detection')
plt.tight_layout()
plt.savefig('potato_expert_confusion_matrix.png', dpi=150)
plt.show()

# ============================================================
# STEP 7: SAVE
# ============================================================
joblib.dump({
    "model":       model,
    "scaler":      scaler,
    "class_names": CLASS_NAMES
}, "potato_disease_model_v2.pkl")
print("\n  potato_disease_model_v2.pkl saved!")
print("=" * 55)
print("DONE!") 
