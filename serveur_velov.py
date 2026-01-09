#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Serveur web pour le projet carte interactive de vélos en libre-service
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

# Configuration
PORT = 8080
DB_NAME = "velov.sqlite"
STATIC_DIR = 'client'
COURBES_DIR = os.path.join(STATIC_DIR, 'courbes')
os.makedirs(COURBES_DIR, exist_ok=True)

def init_cache():
    """Initialise le cache des graphiques"""
    print("Initialisation du cache des graphiques...")
    
    # Nettoyer dossier courbes
    if os.path.exists(COURBES_DIR):
        for file in os.listdir(COURBES_DIR):
            file_path = os.path.join(COURBES_DIR, file)
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
            except Exception as e:
                print(f"Erreur suppression: {e}")
    
    # Créer table cache
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
    
    # Vider la table
    c.execute('DELETE FROM "cache_graphiques"')
    conn.commit()
    print("Cache réinitialisé.")

class RequestHandler(http.server.SimpleHTTPRequestHandler):
    """Gestionnaire des requêtes HTTP"""
    static_dir = 'client'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=self.static_dir, **kwargs)
    
    def do_GET(self):
        """Traite les requêtes GET"""
        self.init_params()
        
        # Routage des requêtes
        if self.path_info[0] == 'center':
            self.send_center()
        elif self.path_info[0] == 'regions':
            self.send_regions()
        elif self.path_info[0] == 'stations_full':
            self.send_all_stations_with_details()
        elif self.path_info[0] == 'station' and len(self.path_info) > 1:
            self.send_station_details(self.path_info[1])
        elif self.path_info[0] == 'history_png' and len(self.path_info) > 1:
            self.send_station_history_png(self.path_info[1])
        else:
            super().do_GET()
    
    def send_all_stations_with_details(self):
        """Envoie toutes les stations avec leurs données en une seule requête"""
        try:
            c = conn.cursor()
            
            # Récupérer infos de base
            c.execute('''
                SELECT idstation, nom, adresse1, adresse2, commune, nbbornettes, 
                      stationbonus, pole, ouverte, lon, lat
                FROM "velov-stations"
            ''')
            
            stations_data = c.fetchall()
            stations = []
            
            # Récupérer dernières données disponibles
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
            
            # Dictionnaire pour accès rapide
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
                
                # Ajouter historique si disponible
                station_id = str(station[0])
                if station_id in histo_data:
                    station_info.update(histo_data[station_id])
                else:
                    # Valeurs par défaut
                    station_info.update({
                        'horodate': None,
                        'status': 'UNKNOWN',
                        'capacity': station[5] or 0,
                        'bikes': 0,
                        'stands': 0,
                        'electricalBikes': 0,
                        'mechanicalBikes': 0,
                        'electricalInternalBatteryBikes': 0,
                        'electricalRemovableBatteryBikes': 0
                    })
                
                stations.append(station_info)
                
            # Envoi réponse
            body = json.dumps(stations)
            headers = [('Content-Type', 'application/json')]
            self.send(body, headers)
            
        except sqlite3.Error as e:
            self.send_error(500, f"Erreur SQLite : {e}")
            print(f"Erreur SQLite : {e}")

    def send_station_details(self, station_id):
        """Envoie les détails d'une station spécifique"""
        try:
            c = conn.cursor()
            
            # Récupération infos station
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
            
            # Récupération dernières données
            c.execute('''
                SELECT horodate, status, capacity, bikes, stands,
                        electricalBikes, mechanicalBikes, 
                        electricalInternalBatteryBikes, electricalRemovableBatteryBikes
                FROM "velov-histo"
                WHERE number = ?
                ORDER BY horodate DESC
                LIMIT 1
            ''', (station_info[0],))
            
            histo_data = c.fetchone()
            
            # Création réponse
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
            
            # Ajout données historiques
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
            
            # Envoi réponse
            body = json.dumps(response)
            headers = [('Content-Type', 'application/json')]
            self.send(body, headers)
            
        except sqlite3.Error as e:
            self.send_error(500, f"Erreur SQLite : {e}")
            print(f"Erreur SQLite : {e}")
            

    def send_station_history_png(self, station_id):
        """Génère un graphique PNG pour une station"""
        print(f"Graphique demandé pour station {station_id}")
        c = conn.cursor()

        # Paramètres
        start = self.params.get('start', [None])[0]
        end = self.params.get('end', [None])[0]
        print(f"Période: {start} au {end}")
        
        # Correction du format de date si nécessaire
        if start and not start.endswith(':00'):
            start = f"{start}:00"
        if end and not end.endswith(':00'):
            end = f"{end}:00"
        
        # Options d'affichage
        show_total = self.params.get('show_total', ['1'])[0] == '1'
        show_stands = self.params.get('show_stands', ['1'])[0] == '1'
        show_mechanical = self.params.get('show_mechanical', ['1'])[0] == '1'
        show_electric = self.params.get('show_electric', ['1'])[0] == '1'
        
        # Vérifier si le graphique est déjà en cache
        # On crée ici un nom de fichier unique basé sur les paramètres
        start_str = start.replace(' ', '_').replace(':', '-') if start else 'all'
        end_str = end.replace(' ', '_').replace(':', '-') if end else 'all'
        opt_str = f"t{int(show_total)}s{int(show_stands)}m{int(show_mechanical)}e{int(show_electric)}"
        filename = f"station_{station_id}_start_{start_str}_end_{end_str}_{opt_str}.png"
        filepath = os.path.join(COURBES_DIR, filename)
        
        # Vérifier si le fichier existe déjà en cache
        if os.path.exists(filepath):
            print(f"Utilisation du graphique en cache: {filename}")
            with open(filepath, 'rb') as f:
                png = f.read()
            self.send(png, [('Content-Type','image/png')])
            return
        
        # Construire requête
        args = [station_id]
        where = ["number = ?"]
        
        # Important: utiliser substr pour extraire la partie date sans le fuseau horaire
        fmt = "substr(horodate, 1, 19)"
        
        if start:
            where.append(f"{fmt} >= ?")
            args.append(start)
        if end:
            where.append(f"{fmt} <= ?")
            args.append(end)

        sql = f"""
        SELECT horodate, bikes, stands, mechanicalBikes, electricalBikes
        FROM "velov-histo"
        WHERE {" AND ".join(where)}
        ORDER BY {fmt} ASC
        """
        
        # Afficher la requête pour débogage
        print(f"SQL Query: {sql}")
        print(f"Args: {args}")
        
        c.execute(sql, args)
        rows = c.fetchall()
        
        # Afficher le nombre de résultats
        print(f"Nombre de résultats: {len(rows)}")

        # Si pas de données
        if not rows:
            self.send(b'', [('Content-Type','image/png')])
            return

        # Préparation données - important: tronquer à 19 caractères pour ignorer le fuseau
        dates = [datetime.strptime(r[0][:19], '%Y-%m-%d %H:%M:%S') for r in rows]
        bikes = [r[1] for r in rows]
        stands = [r[2] for r in rows]
        mechanical = [r[3] for r in rows]
        electrical = [r[4] for r in rows]

        # Création graphique
        fig, ax = plt.subplots()
        
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
        ax.xaxis.set_major_formatter(pltd.DateFormatter('%d/%m %H:%M'))
        
        # Sauvegarde
        fig.savefig(filepath, format='png', bbox_inches='tight')
        
        # Mise en cache
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        c.execute('''
            INSERT INTO "cache_graphiques" 
            (station_id, start_date, end_date, filename, creation_date) 
            VALUES (?, ?, ?, ?, ?)
        ''', (station_id, start, end, filename, now))
        conn.commit()
        
        print(f"Nouveau graphique mis en cache: {filename}")

        # Envoi
        buf = io.BytesIO()
        fig.savefig(buf, format='png', bbox_inches='tight')
        plt.close(fig)
        buf.seek(0)
        png = buf.read()

        self.send(png, [('Content-Type','image/png')])


    def send_regions(self):
        """Envoie la liste des stations"""
        c = conn.cursor()
        c.execute("SELECT idstation, nom, lat, lon FROM 'velov-stations'")
        r = c.fetchall()
        body = json.dumps([{'idstation':id, 'nom':n, 'lat':lat, 'lon': lon} 
                          for (id,n,lat,lon) in r])    
        headers = [('Content-Type','application/json')]
        self.send(body, headers)

    def send_center(self):
        """Calcule et envoie le centre des stations"""
        try:
            c = conn.cursor()
            c.execute("SELECT lat, lon FROM 'velov-stations'")
            rows = c.fetchall()

            if not rows:
                self.send_error(404, "Aucune station trouvée")
                return

            latitudes = [row[0] for row in rows]
            longitudes = [row[1] for row in rows]

            center_lat = (max(latitudes) + min(latitudes)) / 2
            center_lon = (max(longitudes) + min(longitudes)) / 2

            body = json.dumps({'lat': center_lat, 'lon': center_lon})
            headers = [('Content-Type', 'application/json')]
            self.send(body, headers)

        except sqlite3.Error as e:
            self.send_error(500, f"Erreur SQLite : {e}")

    def send(self, body, headers=[]):
        """Envoie la réponse au client"""
        if isinstance(body, (bytes, bytearray)):
            encoded = body
        else:
            encoded = body.encode('utf-8')

        self.send_response(200)

        for k, v in headers:
            self.send_header(k, v)
        self.send_header('Content-Length', str(len(encoded)))
        self.end_headers()

        self.wfile.write(encoded)

    def init_params(self):
        """Analyse la requête"""
        info = urlparse(self.path)
        self.path_info = [unquote(v) for v in info.path.split('/')[1:]]
        self.query_string = info.query
        self.params = parse_qs(info.query)

        length = self.headers.get('Content-Length')
        ctype = self.headers.get('Content-Type')
        if length:
            self.body = str(self.rfile.read(int(length)),'utf-8')
            if ctype == 'application/x-www-form-urlencoded': 
                self.params = parse_qs(self.body)
            elif ctype == 'application/json':
                self.params = json.loads(self.body)
        else:
            self.body = ''

# Point d'entrée
if __name__ == '__main__':
    # Vérification DB
    if not os.path.exists(DB_NAME):
        raise FileNotFoundError(f"Base de données {DB_NAME} non trouvée!")
    
    # Connexion DB
    conn = sqlite3.connect(DB_NAME)
    
    # Initialisation cache
    init_cache()
    
    # Démarrage serveur
    httpd = socketserver.TCPServer(("", PORT), RequestHandler)
    print(f"Serveur lancé sur port {PORT}")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("Serveur arrêté par l'utilisateur")
    finally:
        conn.close()
        httpd.server_close()