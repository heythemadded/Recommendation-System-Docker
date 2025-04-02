import os
import requests
import json
import time
from PIL import Image, ExifTags
from PIL.TiffImagePlugin import IFDRational
from io import BytesIO

# --- Configuration ---
USER_AGENT = "RecommenderImages/1.0 (addedheythem@gmail.com)"  
HEADERS = {"User-Agent": USER_AGENT}
COMMONS_API_URL = "https://commons.wikimedia.org/w/api.php"

OUTPUT_DIR = "/data/images"
ANNOTATION_FILE = "/data/metadata.json"

members = []
search_query = "national parks"
nombre_images = 150  # Limite d'images

# Crée un dossier partagé pour stocker les images
os.makedirs(OUTPUT_DIR, exist_ok=True)
print(f"Récupération de la liste d'images pour le thème: {search_query}...")

params_search = {
    "action": "query",
    "list": "search",
    "srsearch": search_query,
    "srnamespace": "6",
    "srlimit": nombre_images,
    "format": "json"
}

while True:
    response_category = requests.get(COMMONS_API_URL, params=params_search, headers=HEADERS)
    if response_category.status_code != 200:
        print("Erreur lors de la récupération de la liste d'images. Code d'erreur :", response_category.status_code)
        exit(1)
    try:
        data_category = response_category.json()
    except Exception as e:
        print("Erreur JSON :", e)
        exit(1)

    batch_members = data_category.get("query", {}).get("search", [])
    members.extend(batch_members)

    if "continue" in data_category:
        params_search["sroffset"] = data_category["continue"]["sroffset"]
    else:
        break

    if len(members) >= nombre_images:
        break

if len(members) < nombre_images:
    print(f"Seulement {len(members)} images trouvées.")
else:
    print(f"{len(members)} images récupérées.")

members = members[:nombre_images]
titles = [member["title"] for member in members]

# --- Traitement par lots ---
def chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i+n]

imageinfo_results = {}
batch_size = 50

for batch in chunks(titles, batch_size):
    params_imageinfo = {
        "action": "query",
        "titles": "|".join(batch),
        "prop": "imageinfo",
        "iiprop": "url|size|mime",
        "format": "json"
    }
    response_imageinfo = requests.get(COMMONS_API_URL, params=params_imageinfo, headers=HEADERS)
    if response_imageinfo.status_code != 200:
        continue
    try:
        data_batch = response_imageinfo.json()
    except Exception:
        continue

    pages = data_batch.get("query", {}).get("pages", {})
    imageinfo_results.update(pages)
    time.sleep(1)

if not imageinfo_results:
    print("Aucune information d'image récupérée.")
    exit(1)

# --- Téléchargement des images ---
metadata_list = []
count = 0
print("Téléchargement et traitement des images...")

for page_id, page_data in imageinfo_results.items():
    imageinfo = page_data.get("imageinfo", [])
    if not imageinfo:
        continue
    info = imageinfo[0]
    image_url = info.get("url")
    mime_type = info.get("mime", "")

    if mime_type == "image/svg+xml":
        continue

    try:
        response_image = requests.get(image_url, headers=HEADERS)
        if response_image.status_code != 200:
            continue

        image_data = response_image.content
        image = Image.open(BytesIO(image_data))
        width, height = image.size
        format_image = image.format

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

        extension = image_url.split('.')[-1].split('?')[0]
        count += 1
        filename = f"{OUTPUT_DIR}/image_{count}.{extension}"

        with open(filename, "wb") as f:
            f.write(image_data)

        meta = {
            "nom_fichier": os.path.basename(filename),
            "url_source": image_url,
            "taille": {"largeur": width, "hauteur": height},
            "format": format_image,
            "orientation": orientation,
            "mime": mime_type,
            "exif": exif_data
        }
        if "DateTimeOriginal" in exif_data:
            meta["date_creation"] = exif_data["DateTimeOriginal"]
        if "Make" in exif_data:
            meta["modele_appareil"] = exif_data["Make"]

        metadata_list.append(meta)

    except Exception as e:
        print(f"Erreur image {image_url}: {e}")

# --- Sauvegarde JSON ---
def default_converter(o):
    if isinstance(o, IFDRational):
        try:
            return float(o)
        except ZeroDivisionError:
            return 0.0
    if isinstance(o, bytes):
        try:
            return o.decode("utf-8")
        except Exception:
            return str(o)
    raise TypeError(f"Non-sérialisable: {o.__class__.__name__}")

with open(ANNOTATION_FILE, "w", encoding="utf-8") as f:
    json.dump(metadata_list, f, ensure_ascii=False, indent=4, default=default_converter)

print("Téléchargement et extraction terminés.")
