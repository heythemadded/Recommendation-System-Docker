## Architecture : 

![Texte alternatif](image.png)

## Utilisation : 
Pour lancer le projet la première fois, vous devez faire un docker-compose up --scale-annoteur=x --scale-collecteur=x. Ou x représente le nombre de contenair par service que vous voulez.

Ensuite vous laisser les collecteurs et les annoteurs faire leur magie. Lorsque cette phase du projet est fini (plus de message ready sur RabbitMQ).
Vous devez lancer le serveur web annotation manuelle pour mettre les tags spécifique de chaque image.

Dès que vous submit les nouvelles tags, la recommandation est lancé.
Vous pouvez utiliser le docker visualisation pour voir les recommandation dans le fichiers prédéfini recommandation.ipynb.

### 1. Lancement initial

Démarrez le projet avec plusieurs conteneurs `collecteur` et `annoteur` (exemple : 2 de chaque) :

```bash
docker-compose up --scale collecteur=2 --scale annoteur=2

Ces services tourneront en continu pour traiter les images automatiquement.

### 2. Attente de fin de traitement
Laisse les collecteurs et annoteurs travailler. Une fois que RabbitMQ ne contient plus de messages "ready", tu peux passer à la suite.

### 3. Annotation manuelle
Lance l’interface web manuelle :
    - Depuis le navigateur, accède à http://localhost:5000 pour corriger ou ajouter des tags aux images.

Une fois les tags soumis, le service de recommandation se déclenche automatiquement.

### 4. Visualisation
Tu peux maintenant visualiser les recommandations dans le notebook :
rends-toi sur http://localhost:8888 et ouvre le fichier recommandation.ipynb pour consulter les résultats.
