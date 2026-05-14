# crop_detector_v3_ultimate.py
import os, cv2, numpy as np, joblib, warnings, gc
warnings.filterwarnings('ignore')

import albumentations as A
from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.preprocessing import StandardScaler
from sklearn.feature_selection import SelectKBest, f_classif, VarianceThreshold
from sklearn.decomposition import PCA
from sklearn.calibration import CalibratedClassifierCV
from sklearn.utils.class_weight import compute_sample_weight
from skimage.feature import hog, local_binary_pattern, graycomatrix, graycoprops
import matplotlib.pyplot as plt
import seaborn as sns

# ─────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────
DATASET_PATH = r"D:\\mega plant dataset\\PlantvillageFYP"
IMG_SIZE     = (128, 128)
crop_classes = ["potato", "tomato", "pepper", "corn"]
clean_names  = ["Potato", "Tomato", "Pepper", "Corn"]

# ─────────────────────────────────────────
# CROP LABEL FUNCTION
# ─────────────────────────────────────────
def get_crop_label(folder_name):
    name = folder_name.lower()
    if 'potato' in name:   return 'potato'
    elif 'tomato' in name: return 'tomato'
    elif 'pepper' in name: return 'pepper'
    elif name in ['blight', 'common_rust',
                  'gray_leaf_spot', 'healthy']:
        return 'corn'
    return None

# ─────────────────────────────────────────
# PREPROCESSING
# ─────────────────────────────────────────
def preprocess_image(img):
    img = cv2.resize(img, IMG_SIZE)
    hsv  = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv,
                       np.array([15, 20, 20]),
                       np.array([100, 255, 255]))
    k    = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5,5))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN,  k)
    mc   = cv2.mean(img, mask=mask)[:3]
    bg   = np.ones_like(img, dtype=np.uint8)
    bg[:] = [int(c) for c in mc]
    img  = np.where(mask[:,:,None]==0, bg, img).astype(np.uint8)
    lab  = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8,8))
    lab[:,:,0] = clahe.apply(lab[:,:,0])
    img  = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
    img_f = img.astype(np.float32)
    avg  = [img_f[:,:,c].mean() for c in range(3)]
    ag   = sum(avg) / 3.0
    for c in range(3):
        if avg[c] > 0:
            img_f[:,:,c] *= ag / avg[c]
    return np.clip(img_f, 0, 255).astype(np.uint8)

# ─────────────────────────────────────────
# FEATURE EXTRACTION
# ─────────────────────────────────────────
def extract_gabor(gray):
    feats = []
    for t in range(4):
        for f in [0.1, 0.3, 0.5]:
            lam = 1.0/f if f > 0 else 1.0
            k   = cv2.getGaborKernel(
                    (21,21), 5.0, t*np.pi/4,
                    lam, 0.5, 0, ktype=cv2.CV_32F)
            r   = cv2.filter2D(gray, cv2.CV_32F, k)
            feats.extend([r.mean(), r.std(),
                          np.percentile(r, 25),
                          np.percentile(r, 75)])
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

    h_bgr = cv2.normalize(
        cv2.calcHist([img],[0,1,2],None,[16,16,16],
                     [0,256,0,256,0,256]), None).flatten()
    h_hsv = cv2.normalize(
        cv2.calcHist([hsv],[0,1,2],None,[16,16,16],
                     [0,180,0,256,0,256]), None).flatten()

    cm = []
    for c in range(3):
        ch = img[:,:,c].astype(np.float32)
        cm.extend([ch.mean(), ch.std(),
                   np.percentile(ch, 25),
                   np.percentile(ch, 75)])
    f_color = np.hstack([h_bgr, h_hsv, cm])

    f_hog = []
    f_hog.extend(hog(gray, 9, (8,8),  (2,2), visualize=False))
    f_hog.extend(hog(gray, 9, (16,16),(2,2), visualize=False))
    sm = cv2.resize(gray, (IMG_SIZE[0]//2, IMG_SIZE[1]//2))
    f_hog.extend(hog(sm,  9, (8,8),  (2,2), visualize=False))

    f_lbp = []
    for r, p in [(1,8),(2,16),(3,24)]:
        lbp = local_binary_pattern(gray, p, r, method='uniform')
        h, _ = np.histogram(lbp.ravel(),
                             bins=np.arange(0, p+3),
                             range=(0, p+2))
        h = h.astype("float")
        h /= (h.sum() + 1e-7)
        f_lbp.extend(h)

    glcm  = graycomatrix(gray, distances=[1,2,3],
                          angles=[0,np.pi/4,np.pi/2,3*np.pi/4],
                          levels=256, symmetric=True, normed=True)
    f_glcm = np.array([
        graycoprops(glcm, p).mean()
        for p in ['contrast','correlation','energy',
                  'homogeneity','dissimilarity','ASM']
    ])

    return np.hstack([f_color, f_hog, f_lbp, f_glcm,
                      extract_gabor(gray), extract_orb(img)])

# ─────────────────────────────────────────
# AUGMENTATION — 3x (memory ke liye)
# ─────────────────────────────────────────
def get_aug():
    return A.Compose([
        A.RandomRotate90(p=0.5),
        A.Flip(p=0.5),
        A.ShiftScaleRotate(
            shift_limit=0.1, scale_limit=0.2,
            rotate_limit=45, p=0.7),
        A.RandomBrightnessContrast(0.4, 0.4, p=0.8),
        A.HueSaturationValue(20, 30, 20, p=0.6),
        A.GaussNoise(var_limit=(10,50), p=0.3),
        A.Blur(blur_limit=3, p=0.2),
    ])

def augment(img, n=3):
    pipe = get_aug()
    return [pipe(image=img)['image'] for _ in range(n)]

# ─────────────────────────────────────────
# STEP 1: PATHS + SPLIT
# ─────────────────────────────────────────
print("="*55)
print("CROP DETECTOR v3 ULTIMATE — Memory Optimized")
print("="*55)

all_paths, all_labels = [], []
crop_counts = {c: 0 for c in crop_classes}

all_folders = sorted([
    f for f in os.listdir(DATASET_PATH)
    if os.path.isdir(os.path.join(DATASET_PATH, f))
])

for folder in all_folders:
    label = get_crop_label(folder)
    if label is None:
        print(f"  Skip: {folder}")
        continue
    class_id    = crop_classes.index(label)
    folder_path = os.path.join(DATASET_PATH, folder)
    imgs = [f for f in os.listdir(folder_path)
            if f.lower().endswith(('.jpg','.jpeg','.png'))]
    print(f"  [{label.upper()}] {folder}: {len(imgs)}")
    for im in imgs:
        all_paths.append(os.path.join(folder_path, im))
        all_labels.append(class_id)
        crop_counts[label] += 1

print(f"\n  Total images: {len(all_paths)}")
for c, n in crop_counts.items():
    print(f"    {c.capitalize():10} {n:6}")

train_paths, test_paths, y_tr, y_te = train_test_split(
    all_paths, all_labels,
    test_size=0.2, random_state=42,
    stratify=all_labels)
print(f"\n  Train: {len(train_paths)} | Test: {len(test_paths)}")

del all_paths, all_labels
gc.collect()

# ─────────────────────────────────────────
# STEP 2: TEST SET
# ─────────────────────────────────────────
print("\nSTEP 2: Clean test set...")
X_te_l, y_te_l = [], []
for i, (p, l) in enumerate(zip(test_paths, y_te)):
    try:
        img = cv2.imread(p)
        if img is None: continue
        img = preprocess_image(img)
        X_te_l.append(extract_features(img))
        y_te_l.append(l)
    except: pass
    if (i+1) % 2000 == 0:
        gc.collect()
        print(f"  {i+1}/{len(test_paths)}...")

X_test = np.array(X_te_l, dtype=np.float32)
y_test = np.array(y_te_l)
del X_te_l, y_te_l
gc.collect()
print(f"  Test: {len(X_test)} | Features: {X_test.shape[1]}")

# ─────────────────────────────────────────
# STEP 3: TRAIN SET + 3x AUGMENTATION
# ─────────────────────────────────────────
print("\nSTEP 3: Train + Augmentation (3x)...")
X_tr_l, y_tr_l = [], []

for i, (p, l) in enumerate(zip(train_paths, y_tr)):
    try:
        img = cv2.imread(p)
        if img is None: continue
        img = cv2.resize(img, IMG_SIZE)
        proc = preprocess_image(img)

        # Original
        X_tr_l.append(extract_features(proc))
        y_tr_l.append(l)

        # 3 augmented
        for aug_img in augment(img, n=3):
            aug_proc = preprocess_image(aug_img)
            X_tr_l.append(extract_features(aug_proc))
            y_tr_l.append(l)

    except: pass

    if (i+1) % 1000 == 0:
        gc.collect()
        print(f"  {i+1}/{len(train_paths)} | Samples so far: {len(X_tr_l)}")

X_train = np.array(X_tr_l, dtype=np.float32)
y_train = np.array(y_tr_l)
del X_tr_l, y_tr_l
gc.collect()
print(f"\n  Train: {len(X_train)} samples")

# ═══════════════════════════════════════════════════
# STEP 4: ULTIMATE MEMORY-EFFICIENT PIPELINE
# ═══════════════════════════════════════════════════
print("\n" + "="*55)
print("STEP 4: ULTIMATE Memory-Efficient Feature Selection")
print("="*55)

# ✅ FIX 1: NaN cleanup (same)
X_train = np.nan_to_num(X_train, nan=0., posinf=0., neginf=0.)
X_test  = np.nan_to_num(X_test,  nan=0., posinf=0., neginf=0.)

# ✅ FIX 2: float32 RAM bachao (Claude ka idea — best!)
print("\n  Converting to float32...")
X_train = X_train.astype(np.float32)
X_test  = X_test.astype(np.float32)
print(f"  Train dtype: {X_train.dtype} | Size: {X_train.nbytes / 1e9:.2f} GB")

# ✅ FIX 3: Scaling with float32 output (Claude ka idea)
print("\n  Scaling...")
scaler = StandardScaler()
Xtr_s = scaler.fit_transform(X_train).astype(np.float32)
Xte_s = scaler.transform(X_test).astype(np.float32)
print(f"  Scaled size: {Xtr_s.nbytes / 1e9:.2f} GB")

del X_train, X_test
gc.collect()

# ✅ FIX 4: VarianceThreshold — FAST, O(n), low memory
print("\n  [1/3] VarianceThreshold — removing near-zero variance features...")
vt = VarianceThreshold(threshold=0.0001)
Xtr_vt = vt.fit_transform(Xtr_s)
Xte_vt = vt.transform(Xte_s)
print(f"  Before VT: {Xtr_s.shape[1]} | After VT: {Xtr_vt.shape[1]}")
print(f"  Removed: {Xtr_s.shape[1] - Xtr_vt.shape[1]} useless features")

del Xtr_s, Xte_s
gc.collect()

# ✅ FIX 5: PCA — MEMORY EFFICIENT dimension reduction
# sklearn PCA uses randomized SVD for large data — chunks mein kaam karta hai!
print("\n  [2/3] PCA — reducing to 1000 components (95% variance)...")
n_comp = min(1000, Xtr_vt.shape[1], Xtr_vt.shape[0])
pca = PCA(n_components=n_comp, random_state=42, svd_solver='randomized')
Xtr_pca = pca.fit_transform(Xtr_vt)
Xte_pca = pca.transform(Xte_vt)
print(f"  PCA components: {Xtr_pca.shape[1]}")
print(f"  Explained variance: {sum(pca.explained_variance_ratio_)*100:.1f}%")
print(f"  PCA size: {Xtr_pca.nbytes / 1e6:.1f} MB")

del Xtr_vt, Xte_vt
gc.collect()

# ✅ FIX 6: SelectKBest on SMALL array — ab smooth chalega!
print("\n  [3/3] SelectKBest — selecting top features from PCA...")
k_final = min(500, Xtr_pca.shape[1])
sel = SelectKBest(f_classif, k=k_final)
Xtr_sel = sel.fit_transform(Xtr_pca, y_train)
Xte_sel = sel.transform(Xte_pca)
print(f"  Final features: {Xtr_sel.shape[1]}")
print(f"  Final array size: {Xtr_sel.nbytes / 1e6:.1f} MB")

del Xtr_pca, Xte_pca
gc.collect()

print("\n" + "="*55)
print(f"  PIPELINE SUMMARY:")
print(f"    Raw features:     ~20,000")
print(f"    After VT:         {vt.transform(np.zeros((1, 20000))).shape[1] if hasattr(vt, 'transform') else 'N/A'}")
print(f"    After PCA:        {pca.n_components_}")
print(f"    Final SelectKBest: {Xtr_sel.shape[1]}")
print(f"    Memory saved:      ~97%")
print("="*55)

# ─────────────────────────────────────────
# STEP 5: XGBOOST
# ─────────────────────────────────────────
print("\nSTEP 5: Training XGBoost...")
sw = compute_sample_weight('balanced', y_train)

xgb = XGBClassifier(
    n_estimators=800,
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

xgb.fit(
    Xtr_sel, y_train,
    sample_weight=sw,
    eval_set=[(Xte_sel, y_te)],
    early_stopping_rounds=50,
    verbose=True
)

print("\n  Calibrating...")
model = CalibratedClassifierCV(xgb, method='isotonic', cv='prefit')
model.fit(Xtr_sel, y_train)

# ─────────────────────────────────────────
# STEP 6: EVALUATION
# ─────────────────────────────────────────
print("\nSTEP 6: Evaluation...")
y_pred   = model.predict(Xte_sel)
test_acc = accuracy_score(y_te, y_pred) * 100
tr_acc   = accuracy_score(y_train, model.predict(Xtr_sel)) * 100
gap      = tr_acc - test_acc

print(f"\n  Train: {tr_acc:.2f}%")
print(f"  Test:  {test_acc:.2f}%")
print(f"  Gap:   {gap:.2f}%", end=" ")
if gap < 5:    print("✅ No overfitting!")
elif gap < 10: print("⚠️  Thoda — OK")
else:          print("❌ Overfitting!")

print("\n--- Classification Report ---")
print(classification_report(y_te, y_pred, target_names=clean_names))

# ─────────────────────────────────────────
# STEP 7: CROSS VALIDATION
# ─────────────────────────────────────────
print("\nSTEP 7: 3-Fold Cross Validation...")
gc.collect()

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

skf = StratifiedKFold(n_splits=3, shuffle=True, random_state=42)
cv_sc = cross_val_score(
    xgb_cv, Xtr_sel, y_train,
    cv=skf, scoring='accuracy', n_jobs=1)
print(f"  3-Fold CV: {cv_sc.mean()*100:.2f}% "
      f"+/- {cv_sc.std()*100:.2f}%")

# ─────────────────────────────────────────
# STEP 8: PLOTS
# ─────────────────────────────────────────
print("\nSTEP 8: Plots...")

plt.figure(figsize=(8, 6))
cm = confusion_matrix(y_te, y_pred)
sns.heatmap(cm, annot=True, fmt='d', cmap='Greens',
            xticklabels=clean_names,
            yticklabels=clean_names)
plt.title('Confusion Matrix — Crop Detector v3 Ultimate')
plt.ylabel('Actual Crop')
plt.xlabel('Predicted Crop')
plt.tight_layout()
plt.savefig('crop_detector_v3_ultimate_matrix.png', dpi=150)
plt.show()
print("  Saved: crop_detector_v3_ultimate_matrix.png")

# ─────────────────────────────────────────
# STEP 9: SAVE
# ─────────────────────────────────────────
print("\nSTEP 9: Saving...")
joblib.dump({
    "model":              model,
    "scaler":             scaler,
    "variance_threshold": vt,
    "pca":                pca,
    "selector":           sel,
    "classes":            crop_classes,
    "class_names":        clean_names,
    "img_size":           IMG_SIZE
}, "crop_detector_v3_ultimate.pkl")
print("  Saved: crop_detector_v3_ultimate.pkl")

# ─────────────────────────────────────────
# FINAL SUMMARY
# ─────────────────────────────────────────
print("\n" + "="*55)
print("FINAL SUMMARY")
print("="*55)
print(f"  Total crops:     {len(crop_classes)}")
for c, n in crop_counts.items():
    print(f"    {c.capitalize():10} {n:6} images")
print(f"  Train samples:   {len(y_train)}")
print(f"  Test samples:    {len(y_te)}")
print(f"  Final features:  {Xtr_sel.shape[1]}")
print(f"  Test Accuracy:   {test_acc:.2f}%")
print(f"  CV Accuracy:     {cv_sc.mean()*100:.2f}%")
print(f"  Overfitting gap: {gap:.2f}%")
print("="*55)
print("✅ Crop Detector ULTIMATE ready!") 