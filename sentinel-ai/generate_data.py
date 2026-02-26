import psycopg2
import random
import datetime
import time

# Connexion à la base de données PostgreSQL
max_retries = 30
conn = None
for i in range(max_retries):
    try:
        conn = psycopg2.connect(
            dbname="sentinel",
            user="postgres",
            password="postgres",
            host="db",
            port="5433"
        )
        print("Connecté à la base de données !")
        break
    except Exception as e:
        print(f"Erreur de connexion à la base (essai {i+1}/{max_retries}): {e}")
        time.sleep(2)

if not conn:
    print("Impossible de se connecter à la base de données. Abandon.")
    exit(1)

cursor = conn.cursor()

# Attente de la création de la table par l'API (sentinel-api)
print("Vérification de la présence de la table 'api_logs'...")
table_exists = False
for i in range(30):
    try:
        cursor.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'api_logs');")
        if cursor.fetchone()[0]:
            table_exists = True
            break
    except Exception:
        conn.rollback()
    
    print("Table non trouvée, nouvelle tentative dans 2 secondes...")
    time.sleep(2)

if not table_exists:
    print("La table n'a pas été trouvée après 60 secondes d'attente. Abandon.")
    exit(1)

# Vérification si les données ont déjà été générées
cursor.execute("SELECT COUNT(*) FROM api_logs;")
if cursor.fetchone()[0] > 0:
    print("La table contient déjà des données. Génération ignorée.")
    cursor.close()
    conn.close()
    exit(0)
# Variables pour générer les données
endpoints = ["/api/auth/login", "/api/data", "/api/users", "/api/products"]
methods = ["GET", "POST"]
user_agents = ["Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)", "PostmanRuntime/7.28.0", "curl/7.68.0"]

now = datetime.datetime.now()

print("Génération du trafic normal...")
normal_count = 800
for i in range(normal_count):
    # Simulation de plusieurs adresses IP normales
    ip_address = f"192.168.1.{random.randint(1, 50)}"
    timestamp = now - datetime.timedelta(minutes=random.randint(0, 1000))
    endpoint = random.choice(endpoints)
    # Les logins sont en POST, le reste majoritairement en GET
    method = "POST" if endpoint == "/api/auth/login" else "GET"
    status_code = 200 if random.random() > 0.05 else 404 # Quelquefois une erreur normale de page non trouvée
    response_time = random.randint(20, 150) # Temps de réponse rapide
    user_agent = random.choice(user_agents[:2]) # IP normales utilisent des navigateurs normaux
    
    cursor.execute("""
        INSERT INTO api_logs (ip_address, timestamp, endpoint, method, status_code, response_time, user_agent)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (ip_address, timestamp, endpoint, method, status_code, response_time, user_agent))

print("Génération du trafic malveillant (Attaque Brute Force)...")
# Attaque 1: Brute Force (une seule IP essaie beaucoup de logins échoués)
bf_ip = "10.0.0.45"
for i in range(150):
    timestamp = now - datetime.timedelta(minutes=5) + datetime.timedelta(seconds=i)
    # Echecs de connexion (status 401 Unauthorized), venant d'un outil comme Postman
    cursor.execute("""
        INSERT INTO api_logs (ip_address, timestamp, endpoint, method, status_code, response_time, user_agent)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (bf_ip, timestamp, "/api/auth/login", "POST", 401, random.randint(30, 80), "PostmanRuntime/7.28.0"))

print("Génération du trafic malveillant (Injections SQL)...")
# Attaque 2: SQL Injection (Payload suspect dans l'URL)
sqli_ip = "45.33.22.11"
for i in range(20):
    timestamp = now - datetime.timedelta(minutes=10) + datetime.timedelta(seconds=i*30)
    # L'API met plus de temps à répondre (500) sur une injection SQL
    cursor.execute("""
        INSERT INTO api_logs (ip_address, timestamp, endpoint, method, status_code, response_time, user_agent, suspected_payload)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """, (sqli_ip, timestamp, "/api/data", "GET", 500, random.randint(200, 600), "curl/7.68.0", "id=1' OR '1'='1"))

conn.commit()
cursor.close()
conn.close()

print("Succès: Jeu de données synthétiques injecté dans PostgreSQL avec succès !")
