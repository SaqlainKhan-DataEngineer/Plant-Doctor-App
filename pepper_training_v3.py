# pepper_training_v3_fixed.py
import os, cv2, numpy as np, joblib, warnings, gc
warnings.filterwarnings('ignore')

import albumentations as A
from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.feature_selection import SelectKBest, f_classif, VarianceThreshold
from sklearn.decomposition import PCA
from sklearn.calibration import CalibratedClassifierCV
from sklearn.utils.class_weight import compute_sample_weight
from skimage.feature import hog, local_binary_pattern, graycomatrix, graycoprops
import matplotlib.pyplot as plt
import seaborn as sns

DATASET_PATH = r"D:\\mega plant dataset\\PlantvillageFYP"  
IMG_SIZE = (128, 128)

# ============================================================
# AUTO-DETECT PEPPER CLASSES
# ============================================================
all_folders = [f for f in os.listdir(DATASET_PATH)
               if os.path.isdir(os.path.join(DATASET_PATH,f)) and "Pepper" in f]
CLASSES    = sorted(all_folders)
CLASS_NAMES = [c.replace("Pepper,_bell___","").replace("Pepper__bell___","")
                .replace("_"," ").title() for c in CLASSES]
print(f"Pepper classes: {CLASSES}")
print(f"Class names:    {CLASS_NAMES}")

# ============================================================
# PREPROCESSING
# ============================================================
def preprocess_image(img):
    img=cv2.resize(img,IMG_SIZE)
    hsv=cv2.cvtColor(img,cv2.COLOR_BGR2HSV)
    mask=cv2.inRange(hsv,np.array([15,20,20]),np.array([100,255,255]))
    k=cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(5,5))
    mask=cv2.morphologyEx(mask,cv2.MORPH_CLOSE,k)
    mask=cv2.morphologyEx(mask,cv2.MORPH_OPEN,k)
    mc=cv2.mean(img,mask=mask)[:3]
    bg=np.ones_like(img,dtype=np.uint8); bg[:]=[int(c) for c in mc]
    img=np.where(mask[:,:,None]==0,bg,img).astype(np.uint8)
    lab=cv2.cvtColor(img,cv2.COLOR_BGR2LAB)
    clahe=cv2.createCLAHE(clipLimit=2.5,tileGridSize=(8,8))
    lab[:,:,0]=clahe.apply(lab[:,:,0])
    img=cv2.cvtColor(lab,cv2.COLOR_LAB2BGR)
    img_f=img.astype(np.float32)
    avg=[img_f[:,:,c].mean() for c in range(3)]; ag=sum(avg)/3.0
    for c in range(3):
        if avg[c]>0: img_f[:,:,c]*=ag/avg[c]
    return np.clip(img_f,0,255).astype(np.uint8)

# ============================================================
# FEATURE EXTRACTION
# ============================================================
def extract_gabor(gray):
    feats=[]
    for t in range(4):
        for f in [0.1,0.3,0.5]:
            k=cv2.getGaborKernel((21,21),5.0,t*np.pi/4,
                                  1.0/f if f>0 else 1.0,0.5,0,ktype=cv2.CV_32F)
            r=cv2.filter2D(gray,cv2.CV_32F,k)
            feats.extend([r.mean(),r.std(),np.percentile(r,25),np.percentile(r,75)])
    return np.array(feats)

def extract_orb(img):
    orb=cv2.ORB_create(nfeatures=300)
    gray=cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
    _,des=orb.detectAndCompute(gray,None)
    if des is None or len(des)==0: return np.zeros(32)
    return np.mean(des,axis=0).astype(np.float32)

def extract_features(img):
    gray=cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
    hsv=cv2.cvtColor(img,cv2.COLOR_BGR2HSV)
    h_bgr=cv2.normalize(cv2.calcHist([img],[0,1,2],None,[16,16,16],
                        [0,256,0,256,0,256]),None).flatten()
    h_hsv=cv2.normalize(cv2.calcHist([hsv],[0,1,2],None,[16,16,16],
                        [0,180,0,256,0,256]),None).flatten()
    cm=[]
    for c in range(3):
        ch=img[:,:,c].astype(np.float32)
        cm.extend([ch.mean(),ch.std(),np.percentile(ch,25),np.percentile(ch,75)])
    f_hog=[]
    f_hog.extend(hog(gray,9,(8,8),(2,2),visualize=False))
    f_hog.extend(hog(gray,9,(16,16),(2,2),visualize=False))
    sm=cv2.resize(gray,(IMG_SIZE[0]//2,IMG_SIZE[1]//2))
    f_hog.extend(hog(sm,9,(8,8),(2,2),visualize=False))
    f_lbp=[]
    for r,p in [(1,8),(2,16),(3,24)]:
        lbp=local_binary_pattern(gray,p,r,method='uniform')
        h,_=np.histogram(lbp.ravel(),bins=np.arange(0,p+3),range=(0,p+2))
        h=h.astype("float"); h/=(h.sum()+1e-7); f_lbp.extend(h)
    glcm=graycomatrix(gray,distances=[1,2,3],
                      angles=[0,np.pi/4,np.pi/2,3*np.pi/4],
                      levels=256,symmetric=True,normed=True)
    f_glcm=np.array([graycoprops(glcm,p).mean()
                     for p in ['contrast','correlation','energy',
                               'homogeneity','dissimilarity','ASM']])
    return np.hstack([h_bgr,h_hsv,cm,f_hog,f_lbp,f_glcm,
                      extract_gabor(gray),extract_orb(img)])

# ============================================================
# AUGMENTATION — FIXED for albumentations v1.3+
# ============================================================
def get_aug():
    return A.Compose([
        A.RandomRotate90(p=0.5),
        A.HorizontalFlip(p=0.5),   # ✅ FIX: Flip → HorizontalFlip
        A.VerticalFlip(p=0.3),       # ✅ FIX: Added VerticalFlip
        A.ShiftScaleRotate(shift_limit=0.1, scale_limit=0.2, rotate_limit=45, p=0.7),
        A.RandomBrightnessContrast(0.4,0.4,p=0.8),
        A.HueSaturationValue(20,30,20,p=0.6),
        A.GaussNoise(var_limit=(10,50),p=0.3),
        A.Blur(blur_limit=3,p=0.2),
    ])

def augment(img,n=5):  # 5x only — memory ke liye
    pipe=get_aug()
    return [pipe(image=img)['image'] for _ in range(n)]

# ============================================================
# STEP 1: PATHS + SPLIT
# ============================================================
print("="*55)
print("PEPPER v3 — XGBoost + Advanced Features (FIXED)")
print("="*55)

all_paths,all_labels=[],[]
for idx,cls in enumerate(CLASSES):
    folder=os.path.join(DATASET_PATH,cls)
    imgs=[f for f in os.listdir(folder)
          if f.lower().endswith(('.jpg','.jpeg','.png'))]
    print(f"  {cls}: {len(imgs)}")
    for im in imgs:
        all_paths.append(os.path.join(folder,im)); all_labels.append(idx)

print(f"\n  Total: {len(all_paths)}")

# ===== FIX: Check unique classes before split =====
unique_labels = sorted(set(all_labels))
print(f"  Unique classes in dataset: {unique_labels}")
print(f"  Number of classes: {len(unique_labels)}")
if len(unique_labels) < 2:
    print("ERROR: Need at least 2 classes for classification!")
    exit(1)

train_paths,test_paths,y_tr,y_te=train_test_split(
    all_paths,all_labels,test_size=0.2,random_state=42,stratify=all_labels)
print(f"  Train: {len(train_paths)} | Test: {len(test_paths)}")

# ===== FIX: Verify stratify worked correctly =====
print(f"  Train labels: {sorted(set(y_tr))}")
print(f"  Test labels:  {sorted(set(y_te))}")

# ============================================================
# STEP 2: TEST SET
# ============================================================
print("\nSTEP 2: Clean test set...")
X_te_l,y_te_l=[],[]
for p,l in zip(test_paths,y_te):
    try:
        img=cv2.imread(p)
        if img is None: continue
        X_te_l.append(extract_features(preprocess_image(img))); y_te_l.append(l)
    except Exception as e:
        print(f"    Error processing {p}: {e}")
        continue

# ===== FIX: Convert to numpy and verify labels =====
X_test=np.array(X_te_l, dtype=np.float32); y_test=np.array(y_te_l)
print(f"  Test: {len(X_test)} samples | Features: {X_test.shape[1]}")
print(f"  Test unique labels: {sorted(set(y_test))}")

# ============================================================
# STEP 3: TRAIN SET + AUGMENTATION
# ============================================================
print("\nSTEP 3: Train + Aug (5x)...")
X_tr_l,y_tr_l=[],[]
for i,(p,l) in enumerate(zip(train_paths,y_tr)):
    try:
        img=cv2.imread(p)
        if img is None: 
            print(f"    Warning: Could not read {p}")
            continue
        img=cv2.resize(img,IMG_SIZE)
        proc=preprocess_image(img)
        X_tr_l.append(extract_features(proc)); y_tr_l.append(l)
        for a in augment(img,n=5):
            X_tr_l.append(extract_features(preprocess_image(a))); y_tr_l.append(l)
    except Exception as e:
        print(f"    Error processing {p}: {e}")
        continue
    if (i+1)%200==0: print(f"  {i+1}/{len(train_paths)}...")

# ===== FIX: Convert to numpy and verify =====
X_train=np.array(X_tr_l, dtype=np.float32); y_train=np.array(y_tr_l)
print(f"  Train: {len(X_train)} samples")
print(f"  Train unique labels BEFORE dedup: {sorted(set(y_train))}")

# ===== FIX: Ensure labels are contiguous 0,1,2,... =====
le = LabelEncoder()
y_train = le.fit_transform(y_train)
y_test = le.transform(y_test)
print(f"  Train unique labels AFTER encoding: {sorted(set(y_train))}")
print(f"  Test unique labels AFTER encoding:  {sorted(set(y_test))}")
print(f"  Label mapping: {dict(zip(le.classes_, range(len(le.classes_))))}")

# ============================================================
# STEP 4: SCALING + MEMORY-EFFICIENT FEATURE SELECTION
# ============================================================
print("\n" + "="*55)
print("STEP 4: Memory-Efficient Feature Selection")
print("="*55)

X_train=np.nan_to_num(X_train,nan=0.,posinf=0.,neginf=0.)
X_test =np.nan_to_num(X_test, nan=0.,posinf=0.,neginf=0.)

# float32 RAM bachao
X_train = X_train.astype(np.float32)
X_test = X_test.astype(np.float32)

scaler=StandardScaler()
Xtr_s=scaler.fit_transform(X_train).astype(np.float32)
Xte_s=scaler.transform(X_test).astype(np.float32)
print(f"  Scaled: {Xtr_s.shape} | Size: {Xtr_s.nbytes/1e6:.1f} MB")

del X_train, X_test
gc.collect()

# VarianceThreshold — remove near-zero variance features
print("\n  [1/3] VarianceThreshold...")
vt = VarianceThreshold(threshold=0.0001)
Xtr_vt = vt.fit_transform(Xtr_s)
Xte_vt = vt.transform(Xte_s)
print(f"  Before: {Xtr_s.shape[1]} | After: {Xtr_vt.shape[1]}")

del Xtr_s, Xte_s
gc.collect()

# PCA — memory efficient dimension reduction
print("\n  [2/3] PCA...")
n_comp = min(500, Xtr_vt.shape[1], Xtr_vt.shape[0])
pca = PCA(n_components=n_comp, random_state=42, svd_solver='randomized')
Xtr_pca = pca.fit_transform(Xtr_vt)
Xte_pca = pca.transform(Xte_vt)
print(f"  Components: {Xtr_pca.shape[1]} | Variance: {sum(pca.explained_variance_ratio_)*100:.1f}%")

del Xtr_vt, Xte_vt
gc.collect()

# SelectKBest on small array
print("\n  [3/3] SelectKBest...")
k_final = min(300, Xtr_pca.shape[1])
sel = SelectKBest(f_classif, k=k_final)
Xtr_sel = sel.fit_transform(Xtr_pca, y_train)
Xte_sel = sel.transform(Xte_pca)
print(f"  Final features: {Xtr_sel.shape[1]}")

del Xtr_pca, Xte_pca
gc.collect()

# ===== FIX: Final verification before training =====
num_classes = len(np.unique(y_train))
print(f"\n  Final num_classes: {num_classes}")
print(f"  y_train range: [{y_train.min()}, {y_train.max()}]")

if num_classes < 2:
    print("ERROR: Less than 2 classes!")
    exit(1)

# ============================================================
# STEP 5: XGBOOST TRAINING
# ============================================================
print("\nSTEP 5: Training XGBoost...")
sw=compute_sample_weight('balanced',y_train)

xgb=XGBClassifier(
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
    objective='multi:softprob',
    num_class=num_classes,
    verbosity=1
)

xgb.fit(Xtr_sel,y_train,
        sample_weight=sw,
        eval_set=[(Xte_sel,y_test)],
        early_stopping_rounds=50,
        verbose=True)

print("\n  Calibrating...")
model=CalibratedClassifierCV(xgb,method='isotonic',cv='prefit')
model.fit(Xtr_sel,y_train)

# ============================================================
# STEP 6: RESULTS
# ============================================================
y_pred=model.predict(Xte_sel)
test_acc=accuracy_score(y_test,y_pred)*100
tr_acc=accuracy_score(y_train, model.predict(Xtr_sel))*100
gap=tr_acc-test_acc

print(f"\n  Train: {tr_acc:.2f}%")
print(f"  Test:  {test_acc:.2f}%")
print(f"  Gap:   {gap:.2f}%", end=" ")
if gap<5: print("✅ No overfitting!")
elif gap<10: print("⚠️ Thoda — OK")
else: print("❌ Overfitting!")

print("\n--- Report ---")
print(classification_report(y_test,y_pred,target_names=CLASS_NAMES))

# ============================================================
# STEP 7: CROSS VALIDATION
# ============================================================
print("\n  Cleaning RAM...")
try:
    del X_tr_l, y_tr_l, X_te_l, y_te_l
except NameError:
    pass
gc.collect()

print("\n  Calculating 5-Fold CV...")
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
    objective='multi:softprob',
    num_class=num_classes,
    verbosity=0
)

cv_sc = cross_val_score(xgb_cv, Xtr_sel, y_train, cv=5, n_jobs=1, scoring='accuracy')
print(f"  5-Fold CV: {cv_sc.mean()*100:.2f}% +/- {cv_sc.std()*100:.2f}%")

# ============================================================
# STEP 8: CONFUSION MATRIX
# ============================================================
plt.figure(figsize=(8,6))
sns.heatmap(confusion_matrix(y_test,y_pred),annot=True,fmt='d',cmap='Greens',
            xticklabels=CLASS_NAMES,yticklabels=CLASS_NAMES)
plt.title('Pepper — XGBoost v3 (Fixed)'); plt.tight_layout()
plt.savefig('pepper_v3_confusion_matrix.png',dpi=150); plt.show()

# ============================================================
# STEP 9: SAVE
# ============================================================
joblib.dump({
    "model": model,
    "scaler": scaler,
    "variance_threshold": vt,
    "pca": pca,
    "selector": sel,
    "class_names": CLASS_NAMES,
    "img_size": IMG_SIZE,
    "label_encoder": le
}, "pepper_disease_model_v3.pkl")
print("\n  ✅ pepper_disease_model_v3.pkl saved!") 