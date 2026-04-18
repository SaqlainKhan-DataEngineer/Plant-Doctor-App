import os
import cv2
import numpy as np
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.metrics import classification_report
from skimage.feature import hog, local_binary_pattern
import matplotlib.pyplot as plt
import seaborn as sns

# --- CONFIGURATION ---
DATASET_PATH = r"D:\PlantvillageFYP" # r lagaya hai taake path ka masla na aye
POTATO_CLASSES = [
    "Potato___Early_blight",
    "Potato___Late_blight",
    "Potato___healthy"
]

def extract_robust_features(image_path):
    """Features nikalne ka behtar function jo app.py se 100% match karta hai."""
    img = cv2.imread(image_path)
    if img is None:
        return None
        
    # 1. AUTO-ZOOM (Center Crop)
    h, w = img.shape[:2]
    crop_h, crop_w = int(h * 0.8), int(w * 0.8)  
    start_y, start_x = (h - crop_h) // 2, (w - crop_w) // 2
    img = img[start_y:start_y+crop_h, start_x:start_x+crop_w]
    
    # 2. AUTO-SHARPEN 
    kernel = np.array([[0, -0.5, 0], 
                       [-0.5, 3, -0.5], 
                       [0, -0.5, 0]], dtype=np.float32)
    img = cv2.filter2D(img, -1, kernel)

    # Resize
    img = cv2.resize(img, (128, 128))
    
    # Color
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    hist_hsv = cv2.calcHist([hsv], [0, 1, 2], None, [8, 8, 8], [0, 180, 0, 256, 0, 256])
    cv2.normalize(hist_hsv, hist_hsv)
    f_color = hist_hsv.flatten()
    
    # HOG
    gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    f_hog = hog(gray_img, orientations=9, pixels_per_cell=(8, 8), 
                cells_per_block=(2, 2), visualize=False)
    
    # LBP
    radius, n_points = 2, 16
    lbp = local_binary_pattern(gray_img, n_points, radius, method='uniform')
    hist_lbp, _ = np.histogram(lbp.ravel(), bins=np.arange(0, n_points + 3), range=(0, n_points + 2))
    hist_lbp = hist_lbp.astype("float")
    hist_lbp /= (hist_lbp.sum() + 1e-7)
    
    return np.hstack([f_color, f_hog, hist_lbp])

def train_potato_expert_with_cv():
    print("🥔 Starting Potato Expert Training with Cross-Validation...")
    X, y = [], []
    
    # Load Data
    for label_idx, class_name in enumerate(POTATO_CLASSES):
        folder_path = os.path.join(DATASET_PATH, class_name)
        if not os.path.exists(folder_path):
            print(f"⚠️ Folder nahi mila: {class_name}")
            continue
            
        images = os.listdir(folder_path)
        print(f"Loading {len(images)} images from {class_name}...")
        
        for img_name in images:
            img_path = os.path.join(folder_path, img_name)
            features = extract_robust_features(img_path)
            if features is not None:
                X.append(features)
                y.append(label_idx)

    X = np.array(X)
    y = np.array(y)
    print(f"\nTotal Potato Data Loaded: {X.shape[0]} images.")
    
    # Split Data
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    
    print("\nSetting up GridSearchCV (Cross-Validation + Hyperparameter Tuning)...")
    print("Yeh thora time lega, please wait...")
    
    # Hum model ko option de rahe hain ke in mein se best setting khud dhoondo
    param_grid = {
        'n_estimators': [100, 200, 300],        # Kitne trees honay chahiye
        'max_depth': [15, 20, 25],              # Ratta marne se roknay ke liye depth
        'min_samples_split': [2, 5, 10],        # Strictness
        'class_weight': ['balanced']
    }
    
    rf = RandomForestClassifier(random_state=42, n_jobs=-1)
    
    # cv=5 ka matlab 5-Fold Cross Validation hai
    grid_search = GridSearchCV(estimator=rf, param_grid=param_grid, 
                               cv=5, scoring='accuracy', n_jobs=-1, verbose=2)
    
    # Training start
    grid_search.fit(X_train, y_train)
    
    print("\n🏆 Best Parameters Found by Cross-Validation:")
    print(grid_search.best_params_)
    
    # Best model select kar liya gaya hai
    best_rf = grid_search.best_estimator_
    
    print("\nEvaluating Best Model on Test Data...")
    y_pred = best_rf.predict(X_test)
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred, target_names=POTATO_CLASSES))
    
    # Save Final Best Model
    model_data = {
        'model': best_rf,
        'scaler': None,  
        'class_names': POTATO_CLASSES
    }
    joblib.dump(model_data, 'potato_disease_expert.pkl')
    print("\n✅ Cross-Validated Model Saved as 'potato_disease_expert.pkl'")

if __name__ == "__main__":
    train_potato_expert_with_cv() 