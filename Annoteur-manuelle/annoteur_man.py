import os
import json
from flask import Flask, render_template, request, jsonify, send_from_directory
import pika

app = Flask(__name__, template_folder="templates", static_folder="static")

ANNOTATION_FILE = "/data/annotations.jsonl"

# Charger toutes les annotations depuis un fichier .jsonl
annotations = []
if os.path.exists(ANNOTATION_FILE):
    with open(ANNOTATION_FILE, "r", encoding="utf-8") as f:
        for line in f:
            try:
                annotations.append(json.loads(line))
            except json.JSONDecodeError as e:
                print(f"Ligne JSON invalide ignorée : {e}")

@app.route("/images/<filename>")
def serve_image(filename):
    return send_from_directory("/data/images", filename)

@app.route("/")
def index():
    return render_template("index.html", images=annotations)

@app.route("/submit", methods=["POST"])
def submit_tags():
    data = request.json
    updated = False
    for image_data in data["images"]:
        for image in annotations:
            if image["nom_fichier"] == image_data["nom_fichier"]:
                image["tags"] = list(set(image.get("tags", [])) | set(image_data["tags"]))
                updated = True
                break

    if updated:
        temp_file = "/data/annotations1.jsonl"
        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                for ann in annotations:
                    f.write(json.dumps(ann, ensure_ascii=False) + "\n")

            try:
                credentials = pika.PlainCredentials('user', 'password')
                connection = pika.BlockingConnection(pika.ConnectionParameters(host="rabbitmq",credentials=credentials))
                channel = connection.channel()
                channel.queue_declare(queue="start_reco_queue", durable=True)
                channel.basic_publish(exchange="", routing_key="start_reco_queue", body="start_reco")
                connection.close()
                print("Message de démarrage de la recommandation envoyé.")

            except Exception as mq_error:
                print(f"Erreur d'envoi RabbitMQ : {mq_error}")

            return jsonify({"message": "Tags enregistrés avec succès !"})
        except Exception as e:
            return jsonify({"message": f"Erreur lors de l'enregistrement : {e}"}), 500
    else:
        return jsonify({"message": "Aucune annotation mise à jour."}), 400

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
