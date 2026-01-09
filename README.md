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

<p align="center">
  <img width="1919" height="1079" alt="Vue globale de la carte" src="https://github.com/user-attachments/assets/e41104ce-ea36-41df-af0c-b852f2a46eb4" />
  <br>
  <em>Vue globale de la carte</em>
</p>

L'application web affiche une carte interactive de la ville de **Lyon**.  
Chaque station Vélo’v y est représentée par un **marqueur en forme de vélo**.

### 🔍 Interprétation des marqueurs

- **Taille du marqueur** : : elle reflète le nombre total de vélos disponibles dans la station. Plus un marqueur est grand, plus la station contient de vélos.
- **Couleur du marqueur** : le marqueur est composé de deux couleurs qui indiquent la répartition entre vélos mécaniques et vélos électriques.
  - **Bleu** : proportion de vélos électriques.
  - **Vert** : proportion de vélos mécaniques.

<p align="center">
  <img width="256" height="184" alt="Détail d'un marqueur" src="https://github.com/user-attachments/assets/b7c8f23c-57f0-4fbd-a0f2-8a9f383161c3" />
  <br>
  <em>Détail d'un marqueur</em>
</p>

Au survol du marqueur, une barre de proportion apparaît montrant :
- Part de vélos mécaniques (vert)
- Part de vélos électriques (bleu)
- Part de places libres (gris)

<p align="center">
  <img width="1919" height="1079" alt="image" src="https://github.com/user-attachments/assets/73105a21-7699-48d9-b375-97c21a73b538" />
  <br>
  <em>Graphique d'historique</em>
</p>

<p align="center">
  <img width="1919" height="1079" alt="Graphique d'historique" src="https://github.com/user-attachments/assets/289a51e5-1ac7-46c8-925b-cbff70f07ac7" />
  <br>
  <em>Graphique d'historique</em>
</p>

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

Graphique d'historique
<img width="652" height="882" alt="image" src="https://github.com/user-attachments/assets/0ad130f1-ea96-49a5-adb7-81aeaafbe465" />


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

