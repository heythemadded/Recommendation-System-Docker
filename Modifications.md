J'expose une API qui permet d'afficher les images recommandée et les images choisit par les utilisateurs simulés
Je lance un docker qui génére des visualisations et les exposes par API ----- Soit je fais en sorte que les visualisations sont affichées directement sur un site web


-------------------
Après le Submit du formulaire de l'annotation manuelle ce même site web fait une redirection vers une home page et lorsque les recommandations, les choix utilisateurs et les visualisations sont réalisées il deviennent accessible par bouton. 
Je peux créer un reverse proxy qui gére les appels API pour ce dernier (a voir)
Je peux faire un manager qui sépare les tâches de collecte et annotation automatique des images parceque ça prend énormement du temps. 

Manager avec deux nodes collecte et deux node annotation.