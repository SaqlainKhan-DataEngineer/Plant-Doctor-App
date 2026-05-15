# train_model_only.py
# Complete training script with safety checks
# Run this AFTER extract_features_only.py completes successfully

import numpy as np, joblib, gc, warnings, os, sys
warnings.filterwarnings('ignore')

from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.feature_selection import SelectKBest, f_classif
from sklearn.model_selection import cross_val_score, StratifiedKFold
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.calibration import CalibratedClassifierCV
from sklearn.utils.class_weight import compute_sample_weight
from xgboost import XGBClassifier
import matplotlib.pyplot as plt
import seaborn as sns

# ═══════════════════════════════════════════════════════
# CONFIG — CHANGE THESE PATHS IF NEEDED
# ═══════════════════════════════════════════════════════
SAVE_DIR   = r"D:\\mega plant dataset\\extracted_features_v3"
OUTPUT_DIR = r"D:\\mega plant dataset\\model_outputs"

os.makedirs(OUTPUT_DIR, exist_ok=True)

crop_classes = ["potato", "tomato", "pepper", "corn"]
clean_names  = ["Potato", "Tomato", "Pepper", "Corn"]

print("=" * 60)
print("  MODEL TRAINING — Features already extracted!")
print("=" * 60)

# ═══════════════════════════════════════════════════════
# STEP 0: CHECK FILES EXIST AND ARE VALID
# ═══════════════════════════════════════════════════════
print("\n[STEP 0] Checking extracted feature files...")

required_files = {
    'X_train.npy': 'Training features',
    'y_train.npy': 'Training labels',
    'X_test.npy':  'Test features',
    'y_test.npy':  'Test labels'
}

for fname, desc in required_files.items():
    fpath = os.path.join(SAVE_DIR, fname)

    if not os.path.exists(fpath):
        print(f"\n  ❌ FILE MISSING: {fname}")
        print(f"     Path: {fpath}")
        print(f"\n  💡 SOLUTION:")
        print(f"     1. Run 'extract_features_only.py' first")
        print(f"     2. Make sure it completes without errors")
        print(f"     3. Check that '{SAVE_DIR}' exists")
        sys.exit(1)

    size_mb = os.path.getsize(fpath) / (1024 * 1024)

    if size_mb < 1:
        print(f"\n  ❌ FILE TOO SMALL: {fname} ({size_mb:.2f} MB)")
        print(f"     Feature extraction probably failed midway.")
        print(f"\n  💡 SOLUTION: Re-run 'extract_features_only.py'")
        sys.exit(1)

    print(f"  ✅ {fname:15} | {size_mb:8.1f} MB | {desc}")

# ═══════════════════════════════════════════════════════
# STEP 1: LOAD FEATURES
# ═══════════════════════════════════════════════════════
print("\n[STEP 1] Loading features into memory...")

# Load with memory mapping first (doesnt load full data into RAM)
X_train_mmap = np.load(os.path.join(SAVE_DIR, "X_train.npy"), mmap_mode='r')
y_train_mmap = np.load(os.path.join(SAVE_DIR, "y_train.npy"), mmap_mode='r')
X_test_mmap  = np.load(os.path.join(SAVE_DIR, "X_test.npy"),  mmap_mode='r')
y_test_mmap  = np.load(os.path.join(SAVE_DIR, "y_test.npy"),  mmap_mode='r')

print(f"  Mmapped shapes:")
print(f"    X_train: {X_train_mmap.shape}")
print(f"    y_train: {y_train_mmap.shape}")
print(f"    X_test:  {X_test_mmap.shape}")
print(f"    y_test:  {y_test_mmap.shape}")

# 🚨 CRITICAL VALIDATION CHECKS
print("\n  Validating data integrity...")

if X_train_mmap.ndim != 2:
    raise ValueError(
        f"\n❌ X_train has {X_train_mmap.ndim} dimensions (expected 2).\n"
        f"   Shape: {X_train_mmap.shape}\n"
        f"   Feature extraction failed. Re-run extract_features_only.py"
    )

if X_test_mmap.ndim != 2:
    raise ValueError(
        f"\n❌ X_test has {X_test_mmap.ndim} dimensions (expected 2).\n"
        f"   Shape: {X_test_mmap.shape}\n"
        f"   Feature extraction failed. Re-run extract_features_only.py"
    )

if X_train_mmap.shape[0] == 0:
    raise ValueError(
        f"\n❌ X_train is EMPTY (0 samples)!\n"
        f"   Feature extraction produced no data."
    )

if X_test_mmap.shape[0] == 0:
    raise ValueError(
        f"\n❌ X_test is EMPTY (0 samples)!\n"
        f"   Feature extraction produced no data."
    )

if X_train_mmap.shape[0] != y_train_mmap.shape[0]:
    raise ValueError(
        f"\n❌ MISMATCH: X_train has {X_train_mmap.shape[0]} samples, "
        f"but y_train has {y_train_mmap.shape[0]} labels!"
    )

if X_test_mmap.shape[0] != y_test_mmap.shape[0]:
    raise ValueError(
        f"\n❌ MISMATCH: X_test has {X_test_mmap.shape[0]} samples, "
        f"but y_test has {y_test_mmap.shape[0]} labels!"
    )

print("  ✅ All validation checks passed!")

# Convert to actual arrays in memory (float32 to save RAM)
print("\n  Converting to float32 arrays...")
X_train = np.array(X_train_mmap, dtype=np.float32)
y_train = np.array(y_train_mmap)
X_test  = np.array(X_test_mmap,  dtype=np.float32)
y_test  = np.array(y_test_mmap)

# Free mmap references
del X_train_mmap, y_train_mmap, X_test_mmap, y_test_mmap
gc.collect()

print(f"  Memory loaded:")
print(f"    X_train: {X_train.shape} | {X_train.nbytes / 1e9:.2f} GB")
print(f"    X_test:  {X_test.shape}  | {X_test.nbytes / 1e9:.2f} GB")

# ═══════════════════════════════════════════════════════
# STEP 2: CLEAN NaN/INF VALUES
# ═══════════════════════════════════════════════════════
print("\n[STEP 2] Cleaning NaN / Inf values...")

nan_train = np.isnan(X_train).sum()
nan_test  = np.isnan(X_test).sum()
inf_train = np.isinf(X_train).sum()
inf_test  = np.isinf(X_test).sum()

if nan_train > 0 or nan_test > 0 or inf_train > 0 or inf_test > 0:
    print(f"  Found {nan_train} NaN in train, {nan_test} NaN in test")
    print(f"  Found {inf_train} Inf in train, {inf_test} Inf in test")
    X_train = np.nan_to_num(X_train, nan=0.0, posinf=0.0, neginf=0.0)
    X_test  = np.nan_to_num(X_test,  nan=0.0, posinf=0.0, neginf=0.0)
    print("  ✅ Cleaned!")
else:
    print("  ✅ No NaN/Inf found")

# ═══════════════════════════════════════════════════════
# STEP 3: SCALING
# ═══════════════════════════════════════════════════════
print("\n[STEP 3] Standard Scaling...")
scaler = StandardScaler()
Xtr_s = scaler.fit_transform(X_train).astype(np.float32)
Xte_s = scaler.transform(X_test).astype(np.float32)

del X_train, X_test
gc.collect()

print(f"  Scaled size: {Xtr_s.nbytes / 1e9:.2f} GB")

# ═══════════════════════════════════════════════════════
# STEP 4: VARIANCE THRESHOLD (Manual — no float64 conversion)
# ═══════════════════════════════════════════════════════
print("\n[STEP 4] Variance Threshold (manual float32)...")

# Calculate variance in float32 to avoid sklearn's nanvar float64 conversion
variances = np.var(Xtr_s, axis=0, dtype=np.float32)
keep_mask = variances > 0.0001

Xtr_vt = Xtr_s[:, keep_mask]
Xte_vt = Xte_s[:, keep_mask]

removed = Xtr_s.shape[1] - Xtr_vt.shape[1]
print(f"  {Xtr_s.shape[1]} → {Xtr_vt.shape[1]} features (removed {removed})")

del Xtr_s, Xte_s
gc.collect()

# ═══════════════════════════════════════════════════════
# STEP 5: PCA
# ═══════════════════════════════════════════════════════
print("\n[STEP 5] PCA dimensionality reduction...")

n_comp = min(1000, Xtr_vt.shape[1], Xtr_vt.shape[0])
print(f"  Using {n_comp} components...")

pca = PCA(
    n_components=n_comp,
    random_state=42,
    svd_solver='randomized'  # Memory efficient for large data
)

Xtr_pca = pca.fit_transform(Xtr_vt)
Xte_pca = pca.transform(Xte_vt)

explained_var = sum(pca.explained_variance_ratio_) * 100
print(f"  Components kept: {pca.n_components_}")
print(f"  Explained variance: {explained_var:.1f}%")
print(f"  PCA size: {Xtr_pca.nbytes / 1e6:.1f} MB")

del Xtr_vt, Xte_vt
gc.collect()

# ═══════════════════════════════════════════════════════
# STEP 6: SELECT KBEST
# ═══════════════════════════════════════════════════════
print("\n[STEP 6] SelectKBest feature selection...")

k_final = min(500, Xtr_pca.shape[1])
sel = SelectKBest(f_classif, k=k_final)

Xtr_sel = sel.fit_transform(Xtr_pca, y_train)
Xte_sel = sel.transform(Xte_pca)

print(f"  Selected top {Xtr_sel.shape[1]} features")
print(f"  Final array size: {Xtr_sel.nbytes / 1e6:.1f} MB")

del Xtr_pca, Xte_pca
gc.collect()

# ═══════════════════════════════════════════════════════
# STEP 7: SAVE PROCESSED FEATURES (for fast resume)
# ═══════════════════════════════════════════════════════
print("\n[STEP 7] Saving processed features...")

np.save(os.path.join(OUTPUT_DIR, "X_train_processed.npy"), Xtr_sel)
np.save(os.path.join(OUTPUT_DIR, "X_test_processed.npy"),  Xte_sel)
np.save(os.path.join(OUTPUT_DIR, "y_train.npy"), y_train)
np.save(os.path.join(OUTPUT_DIR, "y_test.npy"),  y_test)

print(f"  Saved to: {OUTPUT_DIR}")
print("  (Next time you can skip directly to training from these files)")

# ═══════════════════════════════════════════════════════
# STEP 8: TRAIN XGBOOST
# ═══════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("  STEP 8: Training XGBoost Classifier")
print("=" * 60)

# Compute balanced sample weights
sw = compute_sample_weight('balanced', y_train)
print(f"  Sample weights computed for {len(sw)} samples")

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
    n_jobs=2,              # Use 2 cores (adjust based on your CPU)
    tree_method='hist',    # Fast histogram-based method
    eval_metric='mlogloss',
    verbosity=1
)

print("\n  Training... (this may take 10-30 minutes)")

xgb.fit(
    Xtr_sel, y_train,
    sample_weight=sw,
    eval_set=[(Xte_sel, y_test)],
    early_stopping_rounds=50,
    verbose=True
)

print(f"\n  Best iteration: {xgb.best_iteration}")
print(f"  Best score: {xgb.best_score:.4f}")

# ═══════════════════════════════════════════════════════
# STEP 9: CALIBRATION
# ═══════════════════════════════════════════════════════
print("\n[STEP 9] Calibrating probabilities...")

model = CalibratedClassifierCV(xgb, method='isotonic', cv='prefit')
model.fit(Xtr_sel, y_train)

print("  ✅ Calibration complete")

# ═══════════════════════════════════════════════════════
# STEP 10: EVALUATION
# ═══════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("  STEP 10: Evaluation")
print("=" * 60)

y_pred   = model.predict(Xte_sel)
test_acc = accuracy_score(y_test, y_pred) * 100
tr_acc   = accuracy_score(y_train, model.predict(Xtr_sel)) * 100
gap      = tr_acc - test_acc

print(f"\n  📊 RESULTS:")
print(f"     Train Accuracy: {tr_acc:.2f}%")
print(f"     Test Accuracy:  {test_acc:.2f}%")
print(f"     Gap:            {gap:.2f}%", end=" ")

if gap < 5:
    print("✅ No overfitting!")
elif gap < 10:
    print("⚠️  Mild overfitting — acceptable")
else:
    print("❌ High overfitting!")

print("\n  📋 Classification Report:")
print(classification_report(y_test, y_pred, target_names=clean_names))

# ═══════════════════════════════════════════════════════
# STEP 11: CONFUSION MATRIX PLOT
# ═══════════════════════════════════════════════════════
print("\n[STEP 11] Saving confusion matrix plot...")

plt.figure(figsize=(8, 6))
cm = confusion_matrix(y_test, y_pred)
sns.heatmap(
    cm,
    annot=True,
    fmt='d',
    cmap='Greens',
    xticklabels=clean_names,
    yticklabels=clean_names
)
plt.title('Confusion Matrix — Crop Detector v3 Ultimate')
plt.ylabel('Actual Crop')
plt.xlabel('Predicted Crop')
plt.tight_layout()

plot_path = os.path.join(OUTPUT_DIR, 'confusion_matrix.png')
plt.savefig(plot_path, dpi=150)
plt.show()
print(f"  ✅ Saved: {plot_path}")

# ═══════════════════════════════════════════════════════
# STEP 12: CROSS VALIDATION
# ═══════════════════════════════════════════════════════
print("\n[STEP 12] 3-Fold Cross Validation...")
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
cv_scores = cross_val_score(
    xgb_cv, Xtr_sel, y_train,
    cv=skf, scoring='accuracy', n_jobs=1
)

print(f"  3-Fold CV: {cv_scores.mean() * 100:.2f}% ± {cv_scores.std() * 100:.2f}%")

# ═══════════════════════════════════════════════════════
# STEP 13: SAVE FINAL MODEL
# ═══════════════════════════════════════════════════════
print("\n[STEP 13] Saving final model...")

model_data = {
    "model":              model,
    "scaler":             scaler,
    "pca":                pca,
    "selector":           sel,
    "classes":            crop_classes,
    "class_names":        clean_names,
    "img_size":           (128, 128)
}

model_path = os.path.join(OUTPUT_DIR, "crop_detector_v3_ultimate.pkl")
joblib.dump(model_data, model_path)

print(f"  ✅ Model saved: {model_path}")
print(f"  📦 File size: {os.path.getsize(model_path) / (1024*1024):.1f} MB")

# ═══════════════════════════════════════════════════════
# FINAL SUMMARY
# ═══════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("  ✅ CROP DETECTOR v3 ULTIMATE — TRAINING COMPLETE!")
print("=" * 60)
print(f"  Test Accuracy:   {test_acc:.2f}%")
print(f"  CV Accuracy:     {cv_scores.mean() * 100:.2f}%")
print(f"  Overfitting Gap: {gap:.2f}%")
print(f"  Model saved:     {model_path}")
print(f"  Plots saved:     {OUTPUT_DIR}")
print("=" * 60)
