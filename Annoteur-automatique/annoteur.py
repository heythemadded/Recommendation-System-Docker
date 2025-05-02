import os
import json
import pika
import numpy as np
from PIL import Image,ImageFile
import webcolors
from sklearn.cluster import KMeans 

# --- Config ---
DATA_DIR = "/data"
IMAGES_DIR = os.path.join(DATA_DIR, "images")
ANNOTATION_FILE = os.path.join(DATA_DIR, "annotations.jsonl")
QUEUE_NAME = "images_a_traiter"

Image.MAX_IMAGE_PIXELS = None
ImageFile.LOAD_TRUNCATED_IMAGES = True

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
    image = Image.open(image_path).convert("RGB")
    image = image.resize((150, 150))
    pixels = np.array(image).reshape(-1, 3)
    kmeans = KMeans(n_clusters=k, n_init=10)
    kmeans.fit(pixels)
    colors = kmeans.cluster_centers_.astype(int)
    hex_colors = ["#{:02x}{:02x}{:02x}".format(*color) for color in colors]
    return [closest_color_name(hex_color) for hex_color in hex_colors]

def generate_tags(metadata):
    tags = set()
    largeur = metadata["taille"]["largeur"]
    hauteur = metadata["taille"]["hauteur"]

    if largeur <= 150 and hauteur <= 150:
        taille = "thumbnail"
    elif largeur <= 800 and hauteur <= 600:
        taille = "medium-size"
    elif largeur <= 1920 and hauteur <= 1080:
        taille = "large-size"
    else:
        taille = "extra-large"

    return list(tags), taille

def annotate_and_save(metadata):
    image_path = os.path.join(IMAGES_DIR, metadata["nom_fichier"])
    if not os.path.exists(image_path):
        print(f"Image non trouvée: {image_path}")
        return

    metadata["couleurs_dominantes"] = get_dominant_colors(image_path)
    metadata["tags"], metadata["taille_image"] = generate_tags(metadata)

    try:
        with open(ANNOTATION_FILE, "a", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False)
            f.write("\n")
            print(f"Annotée : {metadata['nom_fichier']}")
    except Exception as e:
        print(f"Erreur écriture annotation.jsonl : {e}")
    

# --- Callback RabbitMQ ---
def callback(ch, method, properties, body):
    try:
        metadata = json.loads(body)
        annotate_and_save(metadata)
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        print("Erreur lors de l’annotation :", e)

# --- Connexion RabbitMQ ---
try:
    credentials = pika.PlainCredentials('user', 'password')
    connection = pika.BlockingConnection(pika.ConnectionParameters(host="rabbitmq",credentials=credentials))
    channel = connection.channel()
    channel.queue_declare(queue=QUEUE_NAME,durable=True)
    print("Annotateur connecté à RabbitMQ. En attente de messages...")

    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=QUEUE_NAME, on_message_callback=callback, auto_ack=False)
    channel.start_consuming()

except Exception as e:
    print("Connexion RabbitMQ échouée :", e)
    
