import os
import requests
import json
import time
import pika
import warnings
import uuid
from PIL import Image, ExifTags
from PIL.TiffImagePlugin import IFDRational
from io import BytesIO

# --- Configuration ---
USER_AGENT = "RecommenderImages/1.0 (addedheythem@gmail.com)"
HEADERS = {"User-Agent": USER_AGENT}
OUTPUT_DIR = "/data/images"
ANNOTATION_FILE = "/data/metadata.json"
QUEUE_INPUT = "batch_images"
QUEUE_OUTPUT = "images_a_traiter"

os.makedirs(OUTPUT_DIR, exist_ok=True)

warnings.simplefilter('ignore', Image.DecompressionBombWarning)
Image.MAX_IMAGE_PIXELS = None

# --- Conversion EXIF JSON-safe ---
def default_converter(o):
    if isinstance(o, IFDRational):
        try:
            return float(o)
        except ZeroDivisionError:
            return 0.0  # Ou renvoyer None selon vos besoins
    if isinstance(o, bytes):
        try:
            return o.decode("utf-8")
        except Exception:
            return str(o)
    raise TypeError(f"Object of type {o.__class__.__name__} is not JSON serializable")

# --- Traitement d’un batch ---
def process_image(image_url, filename):
    if not image_url.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.webp')):
        print(f"Fichier ignoré (non image): {image_url}")
        return None
    try:
        response = requests.get(image_url, headers=HEADERS, timeout=10)
        if response.status_code != 200:
            return None

        image_data = response.content
        image = Image.open(BytesIO(image_data))
        width, height = image.size
        format_image = image.format
        
        # Déterminer l'orientation
        if width > height:
            orientation = "paysage"
        elif width < height:
            orientation = "portrait"
        else:
            orientation = "carré"
        
        exif_data = {}
        if hasattr(image, "_getexif"):
            
            raw_exif = image._getexif()
            if raw_exif:
                for tag, value in raw_exif.items():
                    decoded = ExifTags.TAGS.get(tag, tag)
                    exif_data[decoded] = value
            
        filepath = os.path.join(OUTPUT_DIR, filename)

        with open(filepath, "wb") as f:
            f.write(image_data)

        meta = {
            "nom_fichier": filename,
            "url_source": image_url,
            "taille": {"largeur": width, "hauteur": height},
            "format": format_image,
            "orientation": orientation,
            "mime": image.get_format_mimetype(),
            "exif": exif_data
        }
        if "DateTimeOriginal" in exif_data:
            meta["date_creation"] = exif_data["DateTimeOriginal"]
        if "Make" in exif_data:
            meta["modele_appareil"] = exif_data["Make"]
        
        time.sleep(1)  # Pause pour éviter les problèmes de surcharge du serveur
        return meta
    
    except Exception as e:
        print(f"Erreur traitement image {image_url} : {e}")
        return None

# --- Callback RabbitMQ ---
def callback(ch, method, properties, body):
    try:
        urls = json.loads(body)
        print(f"Batch reçu ({len(urls)} images)")

        metadata_batch = []
        for url in urls:
            print(f"Traitement de l’image : {url}")
            unique_id = str(uuid.uuid4())
            extension = url.split('.')[-1].split('?')[0]
            filename = f"image_{unique_id}.{extension}"
            meta = process_image(url, filename)
            
            if meta:
                metadata_batch.append(meta)

                ch.basic_publish(
                    exchange='',
                    routing_key=QUEUE_OUTPUT,
                    body=json.dumps(meta, default=default_converter)
                )
                print(f"Envoi metadata image : {meta['nom_fichier']}")

        # Enregistrer les métadonnées localement
        if metadata_batch:
            if os.path.exists(ANNOTATION_FILE):
                with open(ANNOTATION_FILE, "r", encoding="utf-8") as f:
                    existing = json.load(f)
            else:
                existing = []
            existing.extend(metadata_batch)
            with open(ANNOTATION_FILE, "w", encoding="utf-8") as f:
                json.dump(existing, f, ensure_ascii=False, indent=4, default=default_converter)
            print("Métadonnées batch sauvegardées.")

        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        print("Erreur lors du traitement du batch :", e)

# --- Connexion RabbitMQ ---
def main() : 
    try:
        print("Connexion à RabbitMQ...")
        credentials = pika.PlainCredentials('user', 'password')
        connection = pika.BlockingConnection(pika.ConnectionParameters(host="rabbitmq",credentials=credentials))
        channel = connection.channel()
        channel.queue_declare(queue=QUEUE_INPUT, durable=True)
        channel.queue_declare(queue=QUEUE_OUTPUT, durable=True)
        print("Collecteur connecté à RabbitMQ. En attente de batchs...")

        channel.basic_qos(prefetch_count=1)
        channel.basic_consume(queue=QUEUE_INPUT, on_message_callback=callback, auto_ack=False)
        channel.start_consuming()

    except Exception as e:
        print("Erreur de connexion RabbitMQ :", e)

if __name__ == "__main__":
    print("Démarrage du worker...")
    main()
