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


# numéro du port TCP utilisé par le serveur
port_serveur = 8080
# nom de la base de données
BD_name ="velov.sqlite"

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

    # le chemin d'accès commence par /station/{id}
    elif self.path_info[0] == 'station' and len(self.path_info) > 1:
      self.send_station_details(self.path_info[1])
      return

    # le chemin d'accès commence par /ponctualite
    elif self.path_info[0] == 'ponctualite':
      self.send_ponctualite()
      return
  
    # le chemin d'accès commence par /history_png
    elif self.path_info[0] == 'history_png' and len(self.path_info) > 1:
        self.send_station_history_png(self.path_info[1])
        return


    # sinon appel de la méthode parente...
    else:
      super().do_GET()

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
    """
    c = conn.cursor()

    # bornes optionnelles
    start = self.params.get('start', [None])[0]
    end   = self.params.get('end',   [None])[0]

    where = ['number = ?']
    args  = [station_id]
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

    # si pas de données, on renvoie vide
    if not rows:
        self.send(b'', [('Content-Type','image/png')])
        return

    # préparer les listes
    dates      = [datetime.strptime(r[0][:19], '%Y-%m-%d %H:%M:%S') for r in rows]
    bikes      = [r[1] for r in rows]
    stands     = [r[2] for r in rows]
    mechanical = [r[3] for r in rows]
    electrical = [r[4] for r in rows]

    # tracé
    fig, ax = plt.subplots()
    ax.plot(dates, bikes,      label='Vélos totaux')
    ax.plot(dates, stands,     label='Bornettes libres')
    ax.plot(dates, mechanical, label='Mécaniques')
    ax.plot(dates, electrical, label='Électriques')
    ax.set_xlabel('Date')
    ax.set_ylabel('Nombre')
    ax.legend()
    fig.autofmt_xdate()
    # optionnel : formater l’axe x
    ax.xaxis.set_major_formatter(pltd.DateFormatter('%d/%m %H:%M'))

    # écrire dans un buffer mémoire
    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    png = buf.read()

    # renvoyer le PNG
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
    if isinstance(body, (bytes, bytearray)):
        content = body
    else:
        content = body.encode('utf-8')

    self.send_response(200)
    for k, v in headers:
        self.send_header(k, v)
    self.send_header('Content-Length', str(len(content)))
    self.end_headers()
    self.wfile.write(content)


    # on envoie la ligne de statut
    self.send_response(200)

    # on envoie les lignes d'entête et la ligne vide
    [self.send_header(*t) for t in headers]
    self.send_header('Content-Length', int(len(encoded)))
    self.end_headers()

    # on envoie le corps de la réponse
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

# Instanciation et lancement du serveur
httpd = socketserver.TCPServer(("", port_serveur), RequestHandler)
print("Serveur lancé sur port : ", port_serveur)
httpd.serve_forever()
