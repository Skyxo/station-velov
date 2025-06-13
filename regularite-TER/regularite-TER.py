# -*- coding: utf-8 -*-
"""
Serveur web permettant d'afficher les courbes de résularité des TER

Correspond au corrigé du dernier exercice du TD3, §5.1 (TD3-s7.py)
Contient une version basique du cache

@author: Ecole Centrale de Lyon, 2024
"""

import http.server
import socketserver
from urllib.parse import urlparse, parse_qs, unquote
import json

import datetime as dt
import os
import sqlite3

import matplotlib.pyplot as plt
import matplotlib.dates as pltd

# numéro du port TCP utilisé par le serveur
port_serveur = 8080
# nom de la base de données
BD_name = "ter.sqlite"

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

    # le chemin d'accès commence par /regions
    if self.path_info[0] == 'regions':
      self.send_regions()

    # le chemin d'accès commence par /ponctualite
    elif self.path_info[0] == 'ponctualite':
      self.send_ponctualite()

    # sinon appel de la méthode parente...
    else:
      super().do_GET()


  def send_regions(self):
    """Génèrer une réponse avec la liste des régions (version TD3, §5.1)"""
 
    # création du curseur (la connexion a été créée par le programme principal)
    c = conn.cursor()
    
    # récupération de la liste des régions et coordonnées (import de regions.csv)
    c.execute("SELECT * FROM 'regions'")
    r = c.fetchall()
    body = json.dumps([{'nom':n, 'lat':lat, 'lon': lon} 
                       for (n,lat,lon) in r])    

    # envoi de la réponse
    headers = [('Content-Type','application/json')];
    self.send(body,headers)


  def send_ponctualite(self):
    """Retourner une réponse faisant référence au graphique de ponctualite"""

    # création du curseur (la connexion a été créée par le programme principal)
    c = conn.cursor()

    # si pas de paramètre => erreur pas de région
    if len(self.path_info) <= 1 or self.path_info[1] == '' :
        # Région non spécifiée -> erreur 400 Bad Request
        print ('Erreur pas de nom')
        self.send_error(400)
        return None
    else:
        # on récupère le nom de la région dans le 1er paramètre
        region = self.path_info[1]
        # On teste que la région demandée existe bien
        c.execute("SELECT * FROM 'regions' WHERE nom=?",(region,))
        r = c.fetchone()
        if r == None:
            # Région non trouvée -> erreur 404 Not Found
            print ('Erreur nom')
            self.send_error(404)    
            return None
    
    # Test de la présence du fichier dans le cache
    URL_graphique = 'courbes/ponctualite_{}.png'.format(region)
    fichier = self.static_dir + '/{}'.format(URL_graphique)
    if not os.path.exists(fichier):
        print('creer_graphique : ', region)
        self.creer_graphique (region, fichier)
    
    # réponse au format JSON
    body = json.dumps({
            'title': 'Régularité TER {}'.format(region), \
            'img': '/{}'.format(URL_graphique) \
             });
     
    # envoi de la réponse
    headers = [('Content-Type','application/json')];
    self.send(body,headers)


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
    x = [pltd.date2num(dt.date(int(a[0][:4]),int(a[0][5:]),1)) for a in r if not a[6] == '']
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
    """Envoyer la réponse au client avec le corps et les en-têtes fournis
    
    Arguments:
    body: corps de la réponse
    headers: liste de tuples d'en-têtes Cf. HTTP (par défaut : liste vide)
    """
    # on encode la chaine de caractères à envoyer
    encoded = bytes(body, 'UTF-8')

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
