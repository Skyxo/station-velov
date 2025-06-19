# -*- coding: utf-8 -*-
"""
Serveur web permettant de faire tourner le projet web C: carte interactive de location de vélos

@author: Groupe C A2Bg, 2025
"""

import http.server
import socketserver
from urllib.parse import urlparse, parse_qs, unquote
import json
import io
import os
import sqlite3
import matplotlib.pyplot as plt
import matplotlib.dates as pltd
from datetime import datetime
import shutil

# on s'assure que le dossier client/courbes existe
STATIC_DIR = 'client'
COURBES_DIR = os.path.join(STATIC_DIR, 'courbes')
os.makedirs(COURBES_DIR, exist_ok=True)

# numéro du port TCP utilisé par le serveur
port_serveur = 8080
# nom de la base de données
BD_name ="velov.sqlite"

# Fonction pour initialiser le cache
def init_cache():
    """Initialise ou réinitialise le cache des graphiques"""
    print("Initialisation du cache des graphiques...")
    
    # Vider le dossier des courbes
    if os.path.exists(COURBES_DIR):
        for file in os.listdir(COURBES_DIR):
            file_path = os.path.join(COURBES_DIR, file)
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
            except Exception as e:
                print(f"Erreur lors de la suppression du fichier {file_path}: {e}")
    
    # Créer la table de cache si elle n'existe pas
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS "cache_graphiques" (
            "id" INTEGER PRIMARY KEY AUTOINCREMENT,
            "station_id" TEXT,
            "start_date" TEXT,
            "end_date" TEXT,
            "filename" TEXT,
            "creation_date" TEXT
        )
    ''')
    
    # Vider la table de cache
    c.execute('DELETE FROM "cache_graphiques"')
    conn.commit()
    print("Cache des graphiques réinitialisé.")

class RequestHandler(http.server.SimpleHTTPRequestHandler):
  """"Classe dérivée pour traiter les requêtes entrantes du serveur"""

  # sous-répertoire racine des documents statiques
  static_dir = 'client'
  
  def __init__(self, *args, **kwargs):
    """Surcharge du constructeur pour imposer 'client' comme sous répertoire racine"""

    super().__init__(*args, directory=self.static_dir, **kwargs)
    
  def do_GET(self):
    """Traiter les requêtes GET (surcharge la méthode héritée)"""

    # On récupère les étapes du chemin d'accès
    self.init_params()

    if self.path_info[0] == 'center':
        self.send_center()
        return
    
    # le chemin d'accès commence par /regions
    elif self.path_info[0] == 'regions':
        self.send_regions()
        return
    
    # Nouvelle route pour obtenir toutes les stations avec leurs détails
    elif self.path_info[0] == 'stations_full':
        self.send_all_stations_with_details()
        return

    # le chemin d'accès commence par /station/{id}
    elif self.path_info[0] == 'station' and len(self.path_info) > 1:
        self.send_station_details(self.path_info[1])
        return
    
    # le chemin d'accès commence par /history_png/{id}
    elif self.path_info[0] == 'history_png' and len(self.path_info) > 1:
        self.send_station_history_png(self.path_info[1])
        return

    # sinon appel de la méthode parente...
    else:
        super().do_GET()

  def send_all_stations_with_details(self):
      """Envoie toutes les stations avec leurs données détaillées en une seule requête"""
      try:
          c = conn.cursor()
          
          # Récupérer les informations de base des stations
          c.execute('''
              SELECT idstation, nom, adresse1, adresse2, commune, nbbornettes, 
                    stationbonus, pole, ouverte, lon, lat
              FROM "velov-stations"
          ''')
          
          stations_data = c.fetchall()
          stations = []
          
          # Récupérer les dernières données disponibles pour toutes les stations en une seule requête
          c.execute('''
              SELECT h1.number, h1.horodate, h1.status, h1.capacity, h1.bikes, h1.stands,
                    h1.electricalBikes, h1.mechanicalBikes, 
                    h1.electricalInternalBatteryBikes, h1.electricalRemovableBatteryBikes
              FROM "velov-histo" h1
              INNER JOIN (
                  SELECT number, MAX(horodate) as max_horodate
                  FROM "velov-histo"
                  GROUP BY number
              ) h2 ON h1.number = h2.number AND h1.horodate = h2.max_horodate
          ''')
          
          # Créer un dictionnaire pour un accès rapide
          histo_data = {}
          for row in c.fetchall():
              histo_data[str(row[0])] = {
                  'horodate': row[1],
                  'status': row[2],
                  'capacity': row[3],
                  'bikes': row[4],
                  'stands': row[5],
                  'electricalBikes': row[6],
                  'mechanicalBikes': row[7],
                  'electricalInternalBatteryBikes': row[8],
                  'electricalRemovableBatteryBikes': row[9]
              }
          
          # Combiner les données
          for station in stations_data:
              station_info = {
                  'idstation': station[0],
                  'nom': station[1],
                  'adresse1': station[2],
                  'adresse2': station[3],
                  'commune': station[4],
                  'nbbornettes': station[5],
                  'stationbonus': station[6],
                  'pole': station[7],
                  'ouverte': station[8],
                  'lon': station[9],
                  'lat': station[10]
              }
              
              # Ajouter les données d'historique si disponibles
              station_id = str(station[0])
              if station_id in histo_data:
                  station_info.update(histo_data[station_id])
              else:
                  # Valeurs par défaut si aucune donnée d'historique
                  station_info.update({
                      'horodate': None,
                      'status': 'UNKNOWN',
                      'capacity': station[5] or 0,  # nbbornettes
                      'bikes': 0,
                      'stands': 0,
                      'electricalBikes': 0,
                      'mechanicalBikes': 0,
                      'electricalInternalBatteryBikes': 0,
                      'electricalRemovableBatteryBikes': 0
                  })
              
              stations.append(station_info)
              
          # Envoi de la réponse
          body = json.dumps(stations)
          headers = [('Content-Type', 'application/json')]
          self.send(body, headers)
          
      except sqlite3.Error as e:
          self.send_error(500, f"Erreur SQLite : {e}")
          print(f"Erreur SQLite dans send_all_stations_with_details : {e}")

  def send_station_details(self, station_id):
    """Envoyer les détails d'une station spécifique avec les données historiques récentes"""
    try:
        c = conn.cursor()
        
        # Récupération des informations de la station
        c.execute('''
            SELECT idstation, nom, adresse1, adresse2, commune, nbbornettes, 
                    stationbonus, pole, ouverte, lon, lat
            FROM "velov-stations" 
            WHERE idstation = ? OR nom = ?
        ''', (station_id, station_id))
        
        station_info = c.fetchone()
        
        if not station_info:
            self.send_error(404, "Station non trouvée")
            return
        
        # Récupération des dernières données de disponibilité
        c.execute('''
            SELECT horodate, status, capacity, bikes, stands,
                    electricalBikes, mechanicalBikes, 
                    electricalInternalBatteryBikes, electricalRemovableBatteryBikes
            FROM "velov-histo"
            WHERE number = ?
            ORDER BY horodate DESC
            LIMIT 1
        ''', (station_info[0],))  # Utilise l'idstation pour la correspondance
        
        histo_data = c.fetchone()
        
        # Création du dictionnaire de réponse
        response = {
            'idstation': station_info[0],
            'nom': station_info[1],
            'adresse1': station_info[2],
            'adresse2': station_info[3],
            'commune': station_info[4],
            'nbbornettes': station_info[5],
            'stationbonus': station_info[6],
            'pole': station_info[7],
            'ouverte': station_info[8],
            'lon': station_info[9],
            'lat': station_info[10]
        }
        
        # Ajout des données historiques si disponibles
        if histo_data:
            response.update({
                'horodate': histo_data[0],
                'status': histo_data[1],
                'capacity': histo_data[2],
                'bikes': histo_data[3],
                'stands': histo_data[4],
                'electricalBikes': histo_data[5],
                'mechanicalBikes': histo_data[6],
                'electricalInternalBatteryBikes': histo_data[7],
                'electricalRemovableBatteryBikes': histo_data[8]
            })
        
        # Envoi de la réponse
        body = json.dumps(response)
        headers = [('Content-Type', 'application/json')]
        self.send(body, headers)
        
    except sqlite3.Error as e:
        self.send_error(500, f"Erreur SQLite : {e}")
        print(f"Erreur SQLite dans send_station_details : {e}")
        
  def send_station_history_png(self, station_id):
      """
      Génère un PNG contenant la courbe de la station station_id
      sur la plage start/end passée en query string.
      Utilise un cache pour éviter de regénérer les graphiques identiques.
      """
      print(f"Demande de graphique pour station_id = {station_id}")
      c = conn.cursor()

      # bornes optionnelles
      start = self.params.get('start', [None])[0]
      end = self.params.get('end', [None])[0]
      print(f"Période demandée : du {start} au {end}")
      
      # Options d'affichage des séries
      show_total = self.params.get('show_total', ['1'])[0] == '1'
      show_stands = self.params.get('show_stands', ['1'])[0] == '1'
      show_mechanical = self.params.get('show_mechanical', ['1'])[0] == '1'
      show_electric = self.params.get('show_electric', ['1'])[0] == '1'
      
      # Créer une clé de cache qui inclut les options d'affichage
      cache_key = f"station_{station_id}"
      if start:
          # Remplacer les caractères non autorisés dans le nom de fichier
          safe_start = start.replace(':', '-').replace(' ', '_')
          cache_key += f"_start_{safe_start}"
      if end:
          # Remplacer les caractères non autorisés dans le nom de fichier
          safe_end = end.replace(':', '-').replace(' ', '_')
          cache_key += f"_end_{safe_end}"
      
      # Ajouter les options d'affichage à la clé de cache
      cache_key += f"_t{int(show_total)}s{int(show_stands)}m{int(show_mechanical)}e{int(show_electric)}"
      
      filename = cache_key + ".png"
      filepath = os.path.join(COURBES_DIR, filename)
      
      # Vérifier si le graphique est dans le cache
      c.execute('''
          SELECT filename FROM "cache_graphiques" 
          WHERE station_id = ? AND 
                (start_date IS NULL OR start_date = ?) AND 
                (end_date IS NULL OR end_date = ?) AND
                filename = ?
      ''', (station_id, start, end, filename))
      
      cached = c.fetchone()
      
      # Si le graphique est dans le cache et le fichier existe, on l'utilise
      if cached and os.path.exists(os.path.join(COURBES_DIR, cached[0])):
          print(f"Utilisation du graphique en cache: {cached[0]}")
          with open(os.path.join(COURBES_DIR, cached[0]), 'rb') as f:
              self.send(f.read(), [('Content-Type', 'image/png')])
          return
      
      # Sinon, on génère le graphique
      where = ['number = ?']
      args = [station_id]
      fmt = "datetime(substr(horodate,1,19))"
      if start:
          where.append(f"{fmt} >= ?"); args.append(start)
      if end:
          where.append(f"{fmt} <= ?"); args.append(end)

      sql = f"""
        SELECT horodate, bikes, stands, mechanicalBikes, electricalBikes
        FROM "velov-histo"
        WHERE {" AND ".join(where)}
        ORDER BY {fmt} ASC
      """
      c.execute(sql, args)
      rows = c.fetchall()

      # Si pas de données, on renvoie vide
      if not rows:
          self.send(b'', [('Content-Type','image/png')])
          return

      # Préparer les listes
      dates = [datetime.strptime(r[0][:19], '%Y-%m-%d %H:%M:%S') for r in rows]
      bikes = [r[1] for r in rows]
      stands = [r[2] for r in rows]
      mechanical = [r[3] for r in rows]
      electrical = [r[4] for r in rows]

      # Tracé
      fig, ax = plt.subplots()
      
      # Tracer seulement les séries sélectionnées
      if show_total:
          ax.plot(dates, bikes, label='Vélos totaux')
      if show_stands:
          ax.plot(dates, stands, label='Places libres')
      if show_mechanical:
          ax.plot(dates, mechanical, label='Vélos mécaniques')
      if show_electric:
          ax.plot(dates, electrical, label='Vélos électriques')
      
      ax.set_xlabel('Date')
      ax.set_ylabel('Nombre')
      ax.legend()
      fig.autofmt_xdate()
      # Formater l'axe x
      ax.xaxis.set_major_formatter(pltd.DateFormatter('%d/%m %H:%M'))
      
      # On enregistre la figure
      fig.savefig(filepath, format='png', bbox_inches='tight')
      
      # On enregistre dans le cache
      now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
      c.execute('''
          INSERT INTO "cache_graphiques" 
          (station_id, start_date, end_date, filename, creation_date) 
          VALUES (?, ?, ?, ?, ?)
      ''', (station_id, start, end, filename, now))
      conn.commit()
      
      print(f"Nouveau graphique généré et mis en cache: {filename}")

      # Écrire dans un buffer mémoire
      buf = io.BytesIO()
      fig.savefig(buf, format='png', bbox_inches='tight')
      plt.close(fig)
      buf.seek(0)
      png = buf.read()

      # Renvoyer le PNG
      self.send(png, [('Content-Type','image/png')])


  def send_regions(self):
      """Génèrer une réponse avec la liste des régions (version TD3, §5.1)"""
  
      # création du curseur (la connexion a été créée par le programme principal)
      c = conn.cursor()
      
      # récupération de la liste des régions et coordonnées (import de regions.csv)
      c.execute("SELECT idstation, nom, lat, lon FROM 'velov-stations'")
      r = c.fetchall()
      body = json.dumps([{'idstation':id, 'nom':n, 'lat':lat, 'lon': lon} 
                        for (id,n,lat,lon) in r])    
      # envoi de la réponse
      headers = [('Content-Type','application/json')];
      self.send(body,headers)


  def send_center(self):
    """Calculer et envoyer le centre géographique des stations depuis SQLite"""
    if not os.path.exists(BD_name):
        self.send_error(404, "Base de données non trouvée")
        return

    # Connexion à la base de données SQLite
    try:
        c = conn.cursor()
        # Récupération des latitudes et longitudes depuis la table velov-stations
        c.execute("SELECT lat, lon FROM 'velov-stations'")
        rows = c.fetchall()

        if not rows:
            self.send_error(404, "Aucune station trouvée dans la base de données")
            return

        # Extraction des latitudes et longitudes
        latitudes = [row[0] for row in rows]
        longitudes = [row[1] for row in rows]

        # Calcul du centre
        center_lat = (max(latitudes) + min(latitudes)) / 2
        center_lon = (max(longitudes) + min(longitudes)) / 2

        # Conversion en JSON
        body = json.dumps({'lat': center_lat, 'lon': center_lon})

        # Envoi de la réponse
        headers = [('Content-Type', 'application/json')]
        self.send(body, headers)

    except sqlite3.Error as e:
        self.send_error(500, f"Erreur SQLite : {e}")


  def creer_graphique(self, region, nom_fichier):
    """Générer un graphique de ponctualite et l'enregistrer dans le cache"""
    
    # création du curseur (la connexion a été créée par le programme principal)
    c = conn.cursor()

    # configuration du tracé
    plt.figure(figsize=(18,6))
    plt.ylim(80,100)
    plt.grid(which='major', color='#888888', linestyle='-')
    plt.grid(which='minor',axis='x', color='#888888', linestyle=':')
    
    ax = plt.subplot(111)
    loc_major = pltd.YearLocator()
    loc_minor = pltd.MonthLocator()
    ax.xaxis.set_major_locator(loc_major)
    ax.xaxis.set_minor_locator(loc_minor)
    format_major = pltd.DateFormatter('%B %Y')
    ax.xaxis.set_major_formatter(format_major)
    ax.xaxis.set_tick_params(labelsize=10)
    
    # interrogation de la base de données pour les données de la région
    c.execute("SELECT * FROM 'regularite-mensuelle-ter' WHERE Région=? ORDER BY Date", (region,))
    r = c.fetchall()
    # recupération de la date (1ère colonne) et transformation dans le format de pyplot
    x = [pltd.date2num(date(int(a[0][:4]),int(a[0][5:]),1)) for a in r if not a[6] == '']
    # récupération de la régularité (7e colonne)
    y = [float(a[6]) for a in r if not a[6] == '']
    # tracé de la courbe
    plt.plot_date(x,y,linewidth=1, linestyle='-', color='blue', label=region)
        
    # légendes
    plt.legend(loc='lower right')
    plt.title('Régularité des TER (en %) pour la Région {}'.format(region),fontsize=16)
    plt.ylabel('% de régularité')
    plt.xlabel('Date')
    
    # enregistrement de la courbe dans un fichier PNG
    plt.savefig(nom_fichier)
    plt.close()


  def send(self, body, headers=[]):
      """
      Envoyer la réponse au client.
      body peut être bytes ou str.
      headers : liste de tuples (clé, valeur).
      """
      # Encodage du corps de la réponse
      if isinstance(body, (bytes, bytearray)):
          encoded = body  # Si body est déjà en bytes, on l'utilise tel quel
      else:
          encoded = body.encode('utf-8')  # Sinon, on encode en UTF-8

      # Envoi de la ligne de statut
      self.send_response(200)

      # Envoi des en-têtes
      for k, v in headers:
          self.send_header(k, v)
      self.send_header('Content-Length', str(len(encoded)))  # Taille du contenu
      self.end_headers()

      # Envoi du corps de la réponse
      self.wfile.write(encoded)

  def init_params(self):
    """Analyse la requête pour initialiser nos paramètres"""

    # analyse de l'adresse
    info = urlparse(self.path)
    self.path_info = [unquote(v) for v in info.path.split('/')[1:]]
    self.query_string = info.query
    
    # récupération des paramètres dans la query string
    self.params = parse_qs(info.query)

    # récupération du corps et des paramètres (2 encodages traités)
    length = self.headers.get('Content-Length')
    ctype = self.headers.get('Content-Type')
    if length:
      self.body = str(self.rfile.read(int(length)),'utf-8')
      if ctype == 'application/x-www-form-urlencoded' : 
        self.params = parse_qs(self.body)
      elif ctype == 'application/json' :
        self.params = json.loads(self.body)
    else:
      self.body = ''

    # traces
    print('init_params|info_path =', self.path_info)
    print('init_params|body =', length, ctype, self.body)
    print('init_params|params =', self.params)

# Ouverture d'une connexion avec la base de données après vérification de sa présence
if not os.path.exists(BD_name):
    raise FileNotFoundError("BD {} non trouvée !".format(BD_name))
conn = sqlite3.connect(BD_name)

# Initialiser ou réinitialiser le cache au démarrage du serveur
init_cache()

# Instanciation et lancement du serveur
httpd = socketserver.TCPServer(("", port_serveur), RequestHandler)
print("Serveur lancé sur port : ", port_serveur)
try:
    httpd.serve_forever()
except KeyboardInterrupt:
    print("Serveur arrêté par l'utilisateur")
finally:
    # Fermeture propre de la connexion
    conn.close()
    httpd.server_close()