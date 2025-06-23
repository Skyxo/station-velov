# Projet Web Vélo’v (Sujet C)

## 📦 Installation

1. **Télécharger le projet**  
   Clonez ou téléchargez la branche `main` du dépôt GitLab contenant le projet.

2. **Lancer le serveur Python**  
   - Ouvrir le fichier `serveur_velov.py` avec le logiciel **Spyder**.  
   - Aller dans le menu **Exécution** > **Configuration par fichier**.  
   - Sélectionner **Exécuter un fichier avec une configuration personnalisée**.  
   - Dans l’onglet **Console**, choisir **Exécuter dans une nouvelle console dédiée**.  
   - Cliquer sur **Exécuter**.  

   Si tout fonctionne, la console affichera :  
   `Serveur lancé sur port 8080`

3. **Ouvrir l’application**  
   Dans un navigateur web, entrez l’adresse suivante :  
   `http://localhost:8080/index.html`

---

## 🗺️ Fonctionnement général

L'application web affiche une carte interactive de la ville de **Lyon**.  
Chaque station Vélo’v y est représentée par un **marqueur en forme de vélo**.

### 🔍 Interprétation des marqueurs

- **Taille du marqueur** : : elle reflète le nombre total de vélos disponibles dans la station. Plus un marqueur est grand, plus la station contient de vélos.
- **Couleur du marqueur** : le marqueur est composé de deux couleurs qui indiquent la répartition entre vélos mécaniques et vélos électriques.
  - **Bleu** : proportion de vélos électriques.
  - **Vert** : proportion de vélos mécaniques.

Au survol du marqueur, une barre de proportion apparaît montrant :
- Part de vélos mécaniques (vert)
- Part de vélos électriques (bleu)
- Part de places libres (gris)

Au clic sur un marqueur, des **informations détaillées** s’affichent :
- Nom de la station
- Adresse
- Capacité totale
- Nombre de vélos disponibles
- Répartition vélos mécaniques / électriques
- Nombre de places libres

---

## 📈 Affichage de l’historique

1. Cliquer sur une station
2. Indiquer une **date de début** et une **date de fin**
3. Cliquer sur **Afficher l’historique**

Un graphique montrera l’évolution de :
- Nombre de vélos disponibles
- Nombre de places disponibles
- Nombre de vélos mécaniques
- Nombre de vélos électriques

ℹ️ *Si un graphique a déjà été généré, celui-ci est réutilisé afin d’optimiser les
performances.*

---

## 🧭 Filtres de stations

Un menu de filtres est accessible en bas à gauche de la page. Il permet de n’afficher que certaines catégories de stations :
- Toutes les stations
- Stations avec vélos **électriques**
- Stations avec vélos **mécaniques**
- Stations **vides** (aucun vélo, mais places disponibles)
- Stations **fermées**

---

## 🚴‍♂️ Fonctionnalité Itinéraire

Un bouton **Itinéraire** (en haut à droite) permet de planifier un trajet combinant marche et vélo.

### Deux modes de saisie :
1. **Adresses manuelles** : entrée des points de départ/arrivée
2. **Sélection sur carte** :
   - Premier clic : **départ** (curseur vert)
   - Second clic : **arrivée** (curseur rouge)

### Type de vélo sélectionnable :
- Vélo **mécanique**
- Vélo **électrique**
- **Indifférent**

Le trajet s’affiche en 3 segments :
- 🟢 Départ → station (à pied)
- 🔵 Station → station (à vélo)
- 🔴 Station → arrivée (à pied)

Un bouton permet de **réinitialiser** l’itinéraire.

---

## 👥 Équipe du projet

Ce projet a été réalisé par :
- **Carole Lamy**
- **Margot Mauny**
- **Charles Bergeat**
- **Arthur Kowalski**
