import requests
import pika
import json
import time

# --- Config Wikimedia Commons ---
COMMONS_API_URL = "https://commons.wikimedia.org/w/api.php"
HEADERS = {"User-Agent": "RecommenderImages/1.0 (addedheythem@gmail.com)"}
SEARCH_QUERY = "national parks"
NB_IMAGES = 150
BATCH_SIZE = 50

# --- Fonction : récupère les titres d’images Wikimedia ---
def get_titles_from_commons(query, max_images):
    titles = []
    sroffset = 0
    print(f"Recherche d’images pour : '{query}'")
    
    while len(titles) < max_images:
        params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "srnamespace": "6",
            "srlimit": 50,
            "sroffset": sroffset,
            "format": "json"
        }
        response = requests.get(COMMONS_API_URL, params=params, headers=HEADERS)
        if response.status_code != 200:
            print("Erreur API Wikimedia")
            break

        data = response.json()
        search_results = data.get("query", {}).get("search", [])
        if not search_results:
            break

        titles.extend([result["title"] for result in search_results])
        sroffset = data.get("continue", {}).get("sroffset", 0)

        if "continue" not in data:
            break

    print(f"{len(titles)} titres d’images récupérés.")
    return titles[:max_images]

# --- Fonction : récupère les URLs des images ---
def get_image_urls(titles):
    image_urls = []
    for i in range(0, len(titles), 50):
        batch = titles[i:i+50]
        params = {
            "action": "query",
            "titles": "|".join(batch),
            "prop": "imageinfo",
            "iiprop": "url",
            "format": "json"
        }
        response = requests.get(COMMONS_API_URL, params=params, headers=HEADERS)
        if response.status_code != 200:
            continue
        data = response.json()
        pages = data.get("query", {}).get("pages", {})
        for page in pages.values():
            info = page.get("imageinfo", [])
            if info:
                url = info[0].get("url")
                if url and not url.endswith(".svg"):
                    image_urls.append(url)
        time.sleep(1)  # respect API Wikimedia

    print(f"{len(image_urls)} URLs d’images valides extraites.")
    return image_urls

# --- Fonction : divise une liste en batchs ---
def split_list(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i+n]

# --- Connexion à RabbitMQ ---
def envoyer_batchs_rabbitmq(image_urls, batch_size):
    try:
        credentials = pika.PlainCredentials('user', 'password')
        connection = pika.BlockingConnection(pika.ConnectionParameters(host="rabbitmq",credentials=credentials))
        channel = connection.channel()
        channel.queue_declare(queue='batch_images', durable=True)

        batches = list(split_list(image_urls, batch_size))
        for i, batch in enumerate(batches):
            body = json.dumps(batch)
            channel.basic_publish(exchange='', routing_key='batch_images', body=body)
            print(f"Batch {i+1}/{len(batches)} envoyé ({len(batch)} images)")
        
        connection.close()
        print("Tous les batchs ont été envoyés avec succès.")

    except Exception as e:
        print(f"Erreur RabbitMQ : {e}")


# --- Exécution principale ---
if __name__ == "__main__":
    titles = get_titles_from_commons(SEARCH_QUERY, NB_IMAGES)
    urls = get_image_urls(titles)
    envoyer_batchs_rabbitmq(urls, BATCH_SIZE)
