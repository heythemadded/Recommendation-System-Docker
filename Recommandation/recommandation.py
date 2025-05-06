import json
import os
import numpy as np
from collections import Counter
from pyspark.sql import SparkSession
from pyspark.sql.functions import udf, col, size
from pyspark.sql.types import *
import pika
from sklearn.preprocessing import LabelEncoder
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

# Spark session
spark = SparkSession.builder.appName("RecommandationImageSpark").getOrCreate()


def start_reco():
    print("Lancement de la recommandation...")

    # -----------------------------
    # 1. Filtrer les images non intéressantes
    # -----------------------------
    file_path = "/data/annotations1.jsonl"
    tag_to_filter = "not interessting"

    with open(file_path, "r", encoding="utf-8") as f:
        annotations = [json.loads(line) for line in f if line.strip()]

    filtered_annotations = [ann for ann in annotations if tag_to_filter not in ann.get("tags", [])]

    with open(file_path, "w", encoding="utf-8") as f:
        for record in filtered_annotations:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"{len(annotations) - len(filtered_annotations)} image(s) avec le tag '{tag_to_filter}' supprimées.")

    # -----------------------------
    # 2. Chargement des données
    # -----------------------------
    columns = ["color1", "color2", "color3", "orientation", "size", "animal", "mountain", "waterfall", "lake", "forest", "grass", "desert", "safari", "rocks"]
    image_data = []

    for image in filtered_annotations:
        colors = image.get("couleurs_dominantes", [])
        color1, color2, color3 = (colors + ["None"] * 3)[:3]
        size = image.get("taille_image", "unknown")
        orientation = image.get("orientation", "unknown")
        tags = image.get("tags", [])
        tag_dict = {tag: 1 if tag in tags else 0 for tag in columns[5:]}
        image_info = [color1, color2, color3, orientation, size] + list(tag_dict.values())
        image_data.append(image_info)

    import pandas as pd
    df = pd.DataFrame(image_data, columns=columns)

    encoders = {}
    for col in ["color1", "color2", "color3", "orientation", "size"]:
        encoders[col] = LabelEncoder()
        df[col] = encoders[col].fit_transform(df[col])

    # Conversion vers DataFrame Spark
    spark_df = spark.createDataFrame(df)

    # -----------------------------
    # 3. Split des données
    # -----------------------------
    TRAIN_SIZE = 80
    NUM_USERS = 5
    NUM_IMAGES_PER_USER = 5

    df_train_test = df[:TRAIN_SIZE]
    df_real_sim = df[TRAIN_SIZE:]

    data_train_test = filtered_annotations[:TRAIN_SIZE]
    data_real_sim = filtered_annotations[TRAIN_SIZE:]

    X_train, X_test, train_idx, test_idx = train_test_split(df_train_test, range(TRAIN_SIZE), test_size=0.2, random_state=42)

    # -----------------------------
    # 4. Entraînement
    # -----------------------------
    user_models = {}
    user_profiles = {}
    labels_dict = {}

    for user_id in range(1, NUM_USERS + 1):
        selected_images = list(np.random.choice(data_train_test, NUM_IMAGES_PER_USER, replace=False))
        labels = np.array([1 if img in selected_images else 0 for img in data_train_test])

        y_train = labels[list(train_idx)]
        y_test = labels[list(test_idx)]
        labels_dict[user_id] = (y_train, y_test)

        model = RandomForestClassifier(n_estimators=100, random_state=42)
        model.fit(X_train, y_train.ravel())
        user_models[user_id] = model

        # Profil utilisateur
        favorite_colors = Counter()
        favorite_tags = Counter()
        orientations = Counter()

        for img in selected_images:
            favorite_colors.update(img.get("couleurs_dominantes", []))
            orientations[img.get("orientation", "unknown")] += 1
            favorite_tags.update(img.get("tags", []))

        user_profiles[user_id] = {
            "preferred_colors": [c for c, _ in favorite_colors.most_common(3)],
            "preferred_tags": [t for t, _ in favorite_tags.most_common(10)],
            "preferred_orientation": orientations.most_common(1)[0][0],
            "favorite_images": [img["nom_fichier"] for img in selected_images]
        }

    with open("/data/user_profiles.json", "w", encoding="utf-8") as f:
        json.dump(user_profiles, f, ensure_ascii=False, indent=4)

    # -----------------------------
    # 5. Evaluation
    # -----------------------------
    for user_id, model in user_models.items():
        y_train, y_test = labels_dict[user_id]
        y_pred = model.predict(X_test)
        acc = accuracy_score(y_test, y_pred)
        print(f"Précision pour l'utilisateur {user_id} : {acc:.2f}")



    # -------------------------------
    # 6. Recommandation
    # -------------------------------
    def recommend_real_simulation(user_id, top_n=5):
        if user_id not in user_models:
            print(f"Utilisateur {user_id} non trouvé.")
            return []
        
        model = user_models[user_id]
        predictions = model.predict_proba(df_real_sim)[:, 1]
        sorted_indices = np.argsort(predictions)[::-1]

        return [data_real_sim[i]["nom_fichier"] for i in sorted_indices[:top_n]]


    recommendations = {}
    for user_id in range(1, NUM_USERS + 1):
        recs = recommend_real_simulation(user_id, top_n=5)
        recommendations[user_id] = recs

    with open("/data/recommandations.json", "w", encoding="utf-8") as f:
        json.dump(recommendations, f, ensure_ascii=False, indent=4)

def callback(ch, method, properties, body):
    if body.decode() == "start_reco":
        start_reco()
        ch.basic_ack(delivery_tag=method.delivery_tag)

credentials = pika.PlainCredentials('user', 'password')
connection = pika.BlockingConnection(pika.ConnectionParameters(host="rabbitmq",credentials=credentials))
channel = connection.channel()
channel.queue_declare(queue="start_reco_queue", durable=True)
print("En attente du signal de démarrage de la recommandation...")
channel.basic_consume(queue="start_reco_queue", on_message_callback=callback, auto_ack=False)
channel.start_consuming()