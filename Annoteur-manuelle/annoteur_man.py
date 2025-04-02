import os
import json
from flask import Flask, render_template, request, jsonify
from flask import send_from_directory

app = Flask(__name__, template_folder="templates", static_folder="static")

ANNOTATION_FILE = "/data/annotations.json"

if os.path.exists(ANNOTATION_FILE):
    with open(ANNOTATION_FILE, "r", encoding="utf-8") as f:
        annotations = json.load(f)
else:
    annotations = []


@app.route("/images/<filename>")
def serve_image(filename):
    return send_from_directory("/data/images", filename)

@app.route("/")
def index():
    return render_template("index.html", images=annotations)

@app.route("/submit", methods=["POST"])
def submit_tags():
    data = request.json
    for image_data in data["images"]:
        for image in annotations:
            if image["nom_fichier"] == image_data["nom_fichier"]:
                if "tags" not in image:
                    image["tags"] = []
                image["tags"] = list(set(image["tags"]) | set(image_data["tags"]))
                break
    with open(ANNOTATION_FILE, "w", encoding="utf-8") as f:
        json.dump(annotations, f, ensure_ascii=False, indent=4)
    return jsonify({"message": "✅ Tags enregistrés avec succès !"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
