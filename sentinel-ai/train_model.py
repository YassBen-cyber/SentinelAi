import psycopg2
import pandas as pd
from sklearn.ensemble import IsolationForest
import joblib

print("Connexion à la base de données...")
conn = psycopg2.connect(
    dbname="sentinel",
    user="yacine",
    password="joueur12",
    host="localhost",
    port="5432"
)

# Phase 2: Extraction des données (= Exporter logs)
print("Extraction des logs depuis PostgreSQL...")
query = "SELECT ip_address, timestamp, endpoint, method, status_code, response_time, suspected_payload FROM api_logs"
df = pd.read_sql_query(query, conn)
conn.close()

if df.empty:
    print("Erreur: Aucune donnée trouvée dans api_logs. Avez-vous exécuté generate_data.py ?")
    exit(1)

print(f"{len(df)} requêtes trouvées. Nettoyage et Feature Engineering (Créer dataset)...")

# Feature 1 : Y a-t-il un payload suspect ? (1 oui, 0 non)
df['has_suspected_payload'] = df['suspected_payload'].notnull().astype(int)

# Feature 2 : Taux d'erreur par adresse IP (Comportement global de cette IP)
df['is_error'] = (df['status_code'] >= 400).astype(int)
error_rates = df.groupby('ip_address')['is_error'].mean().reset_index().rename(columns={'is_error': 'error_rate'})
df = df.merge(error_rates, on='ip_address', how='left')

# Feature 3 : Volume des requêtes par IP (Comportement global type 'Scan' ou 'Brute Force')
request_counts = df.groupby('ip_address').size().reset_index(name='request_count')
df = df.merge(request_counts, on='ip_address', how='left')

# Nous choisissons de garder uniquement les colonnes numériques pour l'entraînement
features = ['response_time', 'has_suspected_payload', 'error_rate', 'request_count']
X = df[features]
X.fillna(0, inplace=True) # Sécurité pour les NaN

print("Entraînement du modèle d'Anomalie (Isolation Forest)...")
# Contamination de ~15% puisqu'on a environ 170 requêtes d'attaque sur 800 saines
model = IsolationForest(n_estimators=100, contamination=0.15, random_state=42)
model.fit(X)

# Sauvegarde pour l'utiliser en temps réel dans un futur module (Phase 4)
joblib.dump(model, 'isolation_forest_model.joblib')
print("Modèle sauvegardé sous 'isolation_forest_model.joblib'")

print("\n------------------------------")
print("TEST ET RESULTATS DE DETECTION")
print("------------------------------")
# L'Isolation Forest retourne 1 pour NORMAL (Inlier) et -1 pour ANOMALIE (Outlier)
df['anomaly'] = model.predict(X)
anomalies = df[df['anomaly'] == -1]
df.to_csv("logs_features.csv", index=False)

print(f"Total des requêtes scannées : {len(df)}")
print(f"Nombre de requêtes d'attaques suspectes identifiées : {len(anomalies)}")

print("\nTop 5 des Adresses IP classées dangereuses :")
dangerous_ips = anomalies['ip_address'].value_counts()
for ip, count in dangerous_ips.head(15).items():
    print(f" ⚠️  IP Suspecte: {ip} | Nombre de requêtes identifiées en anomalie: {count}")
    
