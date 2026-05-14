import os
import shutil

# --- PATH (archive_3) ---
ARCHIVE_3_TAIWAN = r"D:\Mega_dataset\Compressed\archive_3\data"
DEST_DIR = r"D:\mega plant dataset\Extra_Datasets_Sorted\Tomato"

def extract_taiwan_tomato(src, dest):
    if not os.path.exists(src):
        print(f"Path nahi mili: {src}")
        return
        
    print("Taiwan Tomato Dataset (archive_3) extract ho raha hai...")
    total_copied = 0
    
    if not os.path.exists(dest):
        os.makedirs(dest)
    
    for root, dirs, files in os.walk(src):
        folder_name = os.path.basename(root)
        
        # 'data', 'train', 'test' jaise main folders ke naam ignore karein
        if folder_name.lower() in ['data', 'train', 'test', 'val']:
            continue
            
        # Sirf tasveerein (images) nikalen
        images = [f for f in files if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        
        if len(images) > 0:
            # Folder ka naam seedha bimari ka naam hoga (e.g., bacterial_spot)
            disease_name = f"Tomato___{folder_name}"
            dest_disease_dir = os.path.join(dest, disease_name)
            
            if not os.path.exists(dest_disease_dir):
                os.makedirs(dest_disease_dir)
                
            for img in images:
                src_img = os.path.join(root, img)
                # 'Taiwan_' prefix laga rahe hain taake PlantVillage se naam match na kare
                dest_img = os.path.join(dest_disease_dir, f"Taiwan_{img}")
                
                if not os.path.exists(dest_img):
                    shutil.copy2(src_img, dest_img)
                    total_copied += 1
                    
    print("-" * 40)
    print(f"Zabardast! Taiwan Dataset se {total_copied} Tamatar ki tasveerein copy ho gayin!")

extract_taiwan_tomato(ARCHIVE_3_TAIWAN, DEST_DIR)