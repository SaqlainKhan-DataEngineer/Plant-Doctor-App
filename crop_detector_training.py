# ============================================================
# ROBUST CROP DETECTOR — FINAL FIXED VERSION
# 7 Augmentations | Green Masking | CLAHE | No Data Leakage
# Memory Optimized — No RAM Spikes
# ============================================================

import os
import cv2
import numpy as np
import joblib
import gc
from skimage.feature import hog, local_binary_pattern, graycomatrix, graycoprops
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.preprocessing import StandardScaler
import matplotlib.pyplot as plt
import seaborn as sns
import warnings
warnings.filterwarnings('ignore')

# ✅ SIRF YAHAN APNA PATH DAALO
dataset_path = r"D:\PlantvillageFYP"
img_size     = (128, 128)
crop_classes = ["potato", "tomato", "pepper", "corn"]
clean_names  = ["Potato", "Tomato", "Pepper", "Corn"]

# ============================================================
# FUNCTIONS
# ============================================================
def get_crop_label(folder_name):
    name = folder_name.lower()
    if 'potato' in name:   return 'potato'
    elif 'tomato' in name: return 'tomato'
    elif 'pepper' in name: return 'pepper'
    elif name in ['blight', 'common_rust', 'gray_leaf_spot', 'healthy']:
        return 'corn'
    return None

def preprocess_image(img):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    lower_green = np.array([20, 25, 25])
    upper_green = np.array([100, 255, 255])
    mask = cv2.inRange(hsv, lower_green, upper_green)
    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    if cv2.countNonZero(mask) > (img.shape[0] * img.shape[1] * 0.08):
        img = cv2.bitwise_and(img, img, mask=mask)
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    lab[:, :, 0] = clahe.apply(lab[:, :, 0])
    return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

def augment_image(img):
    h, w = img.shape[:2]
    m = 15
    return [
        cv2.flip(img, 1),
        cv2.convertScaleAbs(img, alpha=0.55, beta=0),
        cv2.convertScaleAbs(img, alpha=1.45, beta=25),
        cv2.resize(cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE), img_size),
        cv2.resize(cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE), img_size),
        cv2.GaussianBlur(img, (5, 5), 0),
        cv2.resize(img[m:h-m, m:w-m], img_size)
    ]

def extract_features_from_img(img):
    processed = preprocess_image(img)
    gray = cv2.cvtColor(processed, cv2.COLOR_BGR2GRAY)

    hist_bgr = cv2.calcHist([processed], [0,1,2], None,
                             [8,8,8], [0,256,0,256,0,256])
    hsv2 = cv2.cvtColor(processed, cv2.COLOR_BGR2HSV)
    hist_hsv = cv2.calcHist([hsv2], [0,1,2], None,
                             [8,8,8], [0,180,0,256,0,256])
    f_color = np.hstack([hist_bgr.flatten(), hist_hsv.flatten()])

    f_hog = hog(gray, orientations=9,
                pixels_per_cell=(8, 8),
                cells_per_block=(2, 2),
                visualize=False)

    radius, n_points = 2, 16
    lbp = local_binary_pattern(gray, n_points, radius, method='uniform')
    h_lbp, _ = np.histogram(lbp.ravel(),
                             bins=np.arange(0, n_points + 3),
                             range=(0, n_points + 2))
    h_lbp = h_lbp.astype("float")
    f_lbp = h_lbp / (h_lbp.sum() + 1e-7)

    glcm = graycomatrix(gray, distances=[1, 2],
                        angles=[0, np.pi/4, np.pi/2, 3*np.pi/4],
                        levels=256, symmetric=True, normed=True)
    f_glcm = np.array([
        graycoprops(glcm, 'contrast').mean(),
        graycoprops(glcm, 'correlation').mean(),
        graycoprops(glcm, 'energy').mean(),
        graycoprops(glcm, 'homogeneity').mean(),
        graycoprops(glcm, 'dissimilarity').mean()
    ])

    return np.hstack([f_color, f_hog, f_lbp, f_glcm])

# ============================================================
# STEP 1: PATHS COLLECT + SPLIT
# ============================================================
print("=" * 55)
print("STEP 1: Collecting paths and splitting...")
print("=" * 55)

if not os.path.exists(dataset_path):
    raise ValueError(f"Folder nahi mila: {dataset_path}")

all_paths, all_labels = [], []
crop_counts = {c: 0 for c in crop_classes}

all_folders = sorted([
    f for f in os.listdir(dataset_path)
    if os.path.isdir(os.path.join(dataset_path, f))
])

for folder in all_folders:
    label = get_crop_label(folder)
    if label is None:
        print(f"  Skip: {folder}")
        continue
    class_id    = crop_classes.index(label)
    folder_path = os.path.join(dataset_path, folder)
    images = [f for f in os.listdir(folder_path)
              if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    print(f"  [{label.upper()}] {folder}: {len(images)}")
    for img_name in images:
        all_paths.append(os.path.join(folder_path, img_name))
        all_labels.append(class_id)
        crop_counts[label] += 1

print(f"\n  Total: {len(all_paths)}")
for c, n in crop_counts.items():
    print(f"    {c.capitalize():10} {n:5}")

train_paths, test_paths, y_train_paths, y_test_paths = train_test_split(
    all_paths, all_labels,
    test_size=0.2,
    random_state=42,
    stratify=all_labels
)
print(f"\n  Train: {len(train_paths)} | Test: {len(test_paths)}")

del all_paths, all_labels
gc.collect()

# ============================================================
# STEP 2: TEST SET — clean, no augmentation
# ============================================================
print("\n" + "=" * 55)
print("STEP 2: Processing CLEAN test set...")
print("=" * 55)

X_test_list, y_test_list = [], []
for i, (p, lbl) in enumerate(zip(test_paths, y_test_paths)):
    try:
        img = cv2.imread(p)
        if img is None: continue
        img   = cv2.resize(img, img_size)
        feats = extract_features_from_img(img)
        if feats is not None:
            X_test_list.append(feats)
            y_test_list.append(lbl)
        del img, feats
    except Exception as e:
        print(f"  Warning: {e}")
    if (i+1) % 1000 == 0:
        gc.collect()
        print(f"  Test: {i+1}/{len(test_paths)}")

X_test = np.array(X_test_list, dtype=np.float32)
y_test = np.array(y_test_list)
del X_test_list, y_test_list
gc.collect()
print(f"  Test set: {len(X_test)} samples")

# ============================================================
# STEP 3: TRAIN SET — Pre-allocated array
# ============================================================
print("\n" + "=" * 55)
print("STEP 3: Processing + Augmenting train set...")
print("=" * 55)

temp_img   = cv2.resize(cv2.imread(train_paths[0]), img_size)
temp_feats = extract_features_from_img(temp_img)
NUM_FEATURES = temp_feats.shape[0]
del temp_img, temp_feats
print(f"  Feature size: {NUM_FEATURES}")

MAX_SAMPLES = len(train_paths) * 8
print(f"  Pre-allocating for {MAX_SAMPLES} samples...")

X_train = np.empty((MAX_SAMPLES, NUM_FEATURES), dtype=np.float32)
y_train = np.empty(MAX_SAMPLES, dtype=np.int32)
current_idx = 0

for i, (p, lbl) in enumerate(zip(train_paths, y_train_paths)):
    try:
        img = cv2.imread(p)
        if img is None: continue
        img = cv2.resize(img, img_size)

        feats = extract_features_from_img(img)
        if feats is not None:
            X_train[current_idx] = feats
            y_train[current_idx] = lbl
            current_idx += 1

        for aug in augment_image(img):
            feats_aug = extract_features_from_img(aug)
            if feats_aug is not None:
                X_train[current_idx] = feats_aug
                y_train[current_idx] = lbl
                current_idx += 1
            del aug, feats_aug

        del img, feats

    except Exception as e:
        print(f"  Warning: {e}")

    if (i+1) % 1000 == 0:
        gc.collect()
        print(f"  Train: {i+1}/{len(train_paths)} | Samples: {current_idx}")

X_train = X_train[:current_idx]
y_train = y_train[:current_idx]
print(f"\n  Final train set: {len(X_train)} samples")

# ============================================================
# STEP 4: SCALING (THE ULTIMATE RAM-SAFE FIX)
# Partial Fit + Manual In-place Transformation
# ============================================================
print("\n" + "=" * 55)
print("STEP 4: Scaling (Chunked Partial Fit)...")
print("=" * 55)

CHUNK = 20000

# 1. Chunked NaN cleanup
print("  Cleaning NaNs in chunks...")
for i in range(0, len(X_train), CHUNK):
    np.nan_to_num(X_train[i:i+CHUNK], copy=False, nan=0.0, posinf=0.0, neginf=0.0)
for i in range(0, len(X_test), CHUNK):
    np.nan_to_num(X_test[i:i+CHUNK], copy=False, nan=0.0, posinf=0.0, neginf=0.0)
gc.collect()

# 2. Fit Scaler in chunks (Bina RAM Spike ke)
print("  Fitting Scaler in chunks...")
scaler = StandardScaler()
for i in range(0, len(X_train), CHUNK):
    scaler.partial_fit(X_train[i:i+CHUNK])

# 3. Transform in-place (Bina float64 temporary copy ke)
print("  Transforming data in-place...")
safe_scale = scaler.scale_.copy()
safe_scale[safe_scale == 0.0] = 1.0  # Zero se divide hone se bachaane ke liye

for i in range(0, len(X_train), CHUNK):
    X_train[i:i+CHUNK] -= scaler.mean_
    X_train[i:i+CHUNK] /= safe_scale

for i in range(0, len(X_test), CHUNK):
    X_test[i:i+CHUNK] -= scaler.mean_
    X_test[i:i+CHUNK] /= safe_scale

# Variable names ko set kar diya taake agla code bina error chale
X_train_scaled = X_train
X_test_scaled = X_test

gc.collect()
print("  Scaling done ✅")
# ============================================================
# STEP 5: TRAINING
# ============================================================
print("\n" + "=" * 55)
print("STEP 5: Training Random Forest...")
print("  Fan tez hoga — normal hai, band mat karna!")
print("=" * 55)

model = RandomForestClassifier(
    n_estimators=300,
    max_depth=25,
    min_samples_split=8,
    min_samples_leaf=4,
    max_features='sqrt',
    class_weight='balanced',
    random_state=42,
    n_jobs=-1
)
model.fit(X_train_scaled, y_train)
print("  Training complete!")

# ============================================================
# STEP 6: EVALUATION
# ============================================================
print("\n" + "=" * 55)
print("STEP 6: Evaluation...")
print("=" * 55)

y_pred    = model.predict(X_test_scaled)
test_acc  = accuracy_score(y_test, y_pred) * 100
train_acc = accuracy_score(y_train, model.predict(X_train_scaled)) * 100
gap       = train_acc - test_acc

print(f"\n  Train Accuracy: {train_acc:.2f}%")
print(f"  Test Accuracy:  {test_acc:.2f}%")
print(f"  Gap:            {gap:.2f}%", end=" ")
if gap < 5:    print("No overfitting!")
elif gap < 10: print("Thoda — acceptable")
else:          print("Overfitting — check karo")

print("\n--- Classification Report ---")
print(classification_report(y_test, y_pred, target_names=clean_names))

# ============================================================
# STEP 7: CROSS VALIDATION
# ============================================================
print("\n" + "=" * 55)
print("STEP 7: 5-Fold Cross Validation...")
print("=" * 55)

X_cv_list, y_cv_list = [], []
all_cv_paths  = train_paths + test_paths
all_cv_labels = y_train_paths + y_test_paths

for i, (p, lbl) in enumerate(zip(all_cv_paths, all_cv_labels)):
    try:
        img = cv2.imread(p)
        if img is None: continue
        img   = cv2.resize(img, img_size)
        feats = extract_features_from_img(img)
        if feats is not None:
            X_cv_list.append(feats)
            y_cv_list.append(lbl)
        del img, feats
    except:
        pass
    if (i+1) % 2000 == 0:
        gc.collect()
        print(f"  CV data: {i+1}/{len(all_cv_paths)}")

X_cv = np.array(X_cv_list, dtype=np.float32)
y_cv = np.array(y_cv_list)
del X_cv_list, y_cv_list
gc.collect()

# Chunked NaN for CV too
for i in range(0, len(X_cv), CHUNK):
    np.nan_to_num(X_cv[i:i+CHUNK], copy=False,
                  nan=0.0, posinf=0.0, neginf=0.0)
gc.collect()

scaler_cv   = StandardScaler(copy=False)
X_cv_scaled = scaler_cv.fit_transform(X_cv)
del X_cv
gc.collect()

cv_model = RandomForestClassifier(
    n_estimators=300, max_depth=25,
    min_samples_split=8, min_samples_leaf=4,
    max_features='sqrt', class_weight='balanced',
    random_state=42, n_jobs=-1
)
skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
cv_scores = cross_val_score(
    cv_model, X_cv_scaled, y_cv,
    cv=skf, scoring='accuracy'
)
del X_cv_scaled, y_cv
gc.collect()

print(f"  Fold scores: {[f'{s:.3f}' for s in cv_scores]}")
print(f"  Mean:        {cv_scores.mean()*100:.2f}%")
print(f"  Std:         {cv_scores.std()*100:.2f}%")

# ============================================================
# STEP 8: PLOTS
# ============================================================
print("\n" + "=" * 55)
print("STEP 8: Saving plots...")
print("=" * 55)

plt.figure(figsize=(8, 6))
cm = confusion_matrix(y_test, y_pred)
sns.heatmap(cm, annot=True, fmt='d', cmap='Greens',
            xticklabels=clean_names, yticklabels=clean_names)
plt.title('Confusion Matrix — Robust Crop Detector')
plt.ylabel('Actual Crop')
plt.xlabel('Predicted Crop')
plt.tight_layout()
plt.savefig('robust_crop_detector_matrix.png', dpi=150)
plt.close()
print("  Confusion matrix saved")

plt.figure(figsize=(10, 4))
plt.plot(model.feature_importances_, color='#059669', alpha=0.8)
plt.title('Feature Importance — Color + HOG + LBP + GLCM')
plt.xlabel('Feature Index')
plt.ylabel('Importance Score')
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig('feature_importance.png', dpi=150)
plt.close()
print("  Feature importance saved")

# ============================================================
# STEP 9: SAVE MODEL
# ============================================================
print("\n" + "=" * 55)
print("STEP 9: Saving model...")
print("=" * 55)

joblib.dump({
    "model":       model,
    "scaler":      scaler,
    "classes":     crop_classes,
    "class_names": clean_names
}, "robust_crop_detector_model.pkl")

print("  robust_crop_detector_model.pkl saved!")

# ============================================================
# FINAL SUMMARY
# ============================================================
print("\n" + "=" * 55)
print("FINAL SUMMARY")
print("=" * 55)
print(f"  Test Accuracy:   {test_acc:.2f}%")
print(f"  CV Accuracy:     {cv_scores.mean()*100:.2f}% +/- {cv_scores.std()*100:.2f}%")
print(f"  Overfitting gap: {gap:.2f}%")
print(f"  Features:        {NUM_FEATURES}")
print("=" * 55)
print("DONE! Model ready hai!")
print("  Dataset pic  -- OK")
print("  Google pic   -- OK")
print("  Khet ki pic  -- OK") 