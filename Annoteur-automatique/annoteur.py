import os
import json
import numpy as np
from PIL import Image,ImageFile
import webcolors
from sklearn.cluster import KMeans 

DATA_DIR = "/data"
INPUT_FILE = os.path.join(DATA_DIR, "metadata.json")
OUTPUT_FILE = os.path.join(DATA_DIR, "annotations.json")
Image.MAX_IMAGE_PIXELS = None
ImageFile.LOAD_TRUNCATED_IMAGES = True

with open(INPUT_FILE, "r", encoding="utf-8") as f:
    metadata_list = json.load(f)

def closest_color_name(hex_color):
    target_rgb = webcolors.hex_to_rgb(hex_color)
    min_distance = float("inf")
    closest_name = None

    for name in webcolors.names("css3"):
        rgb = webcolors.name_to_rgb(name)
        distance = sum((target_rgb[i] - rgb[i]) ** 2 for i in range(3))
        if distance < min_distance:
            min_distance = distance
            closest_name = name
            
    return closest_name

def get_dominant_colors(image_path, k=3):
    image = Image.open(image_path)
    image = image.resize((150, 150)) 
    pixels = np.array(image).reshape(-1, 3)
    kmeans = KMeans(n_clusters=k, n_init=10)
    kmeans.fit(pixels)
    
    colors = kmeans.cluster_centers_.astype(int)
    hex_colors = ["#{:02x}{:02x}{:02x}".format(*color) for color in colors]
    return [closest_color_name(hex_color) for hex_color in hex_colors]

def generate_tags(metadata):
    tags = set()

    taille = ""
    if metadata["taille"]["largeur"] <= 150 and  metadata["taille"]["hauteur"] <= 150:
       taille="thumbnail "
    elif  metadata["taille"]["largeur"] <= 800 and metadata["taille"]["hauteur"] <= 600:
        taille="medium-size"
    elif  metadata["taille"]["largeur"] <= 1920 and metadata["taille"]["hauteur"] <= 1080:
        taille="large-size"
    else:
        taille="extra-large"

    return list(tags),taille

annotated_data = []
for metadata in metadata_list:
    image_path = os.path.join(DATA_DIR + "/images",metadata["nom_fichier"])
    if not os.path.exists(image_path):
        print(f"Image non trouvée: {image_path}")
        continue
    metadata["couleurs_dominantes"] = get_dominant_colors(image_path)
    metadata["tags"], metadata["taille_image"] = generate_tags(metadata)
    annotated_data.append(metadata)

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(annotated_data, f, ensure_ascii=False, indent=4)

print("Annotation terminée et enregistrée dans annotations.json")
