import os
import time
import psycopg2
import pandas as pd
from sklearn.ensemble import IsolationForest
import joblib

def train_and_save():
    print("Connexion à la base de données...")
    max_retries = 30
    conn = None
    for i in range(max_retries):
        try:
            conn = psycopg2.connect(
                dbname=os.getenv("DB_NAME", "sentinel"),
                user=os.getenv("DB_USER", "postgres"),
                password=os.getenv("DB_PASS", "postgres"),
                host=os.getenv("DB_HOST", "db"),
                port=os.getenv("DB_PORT", "5433")
            )
            print("Connecté à la base de données pour l'entraînement !")
            break
        except Exception as e:
            print(f"Erreur de connexion (essai {i+1}/{max_retries}): {e}")
            time.sleep(2)

    if not conn:
        print("Erreur: Impossible de se connecter à la base de données pour l'entraînement.")
        return False

    # Check for data
    data_ready = False
    print("Vérification de la présence de données dans api_logs...")
    for i in range(30):
        try:
            query = "SELECT ip_address, timestamp, endpoint, method, status_code, response_time, suspected_payload FROM api_logs"
            df = pd.read_sql_query(query, conn)
            if len(df) > 50:
                data_ready = True
                break
        except Exception as e:
            pass
        if not data_ready:
            print(f"En attente de données pour l'entraînement... (essai {i+1}/30)")
            time.sleep(2)

    conn.close()

    if not data_ready:
        print("Erreur: Aucune donnée trouvée ou table inexistante.")
        return False

    print(f"{len(df)} requêtes trouvées. Nettoyage et Feature Engineering (Créer dataset)...")
    
    # Feature Engineering (Identique à l'inférence)
    df['has_suspected_payload'] = df['suspected_payload'].notnull().astype(int)
    df['is_error'] = (df['status_code'] >= 400).astype(int)
    error_rates = df.groupby('ip_address')['is_error'].mean().reset_index().rename(columns={'is_error': 'error_rate'})
    df = df.merge(error_rates, on='ip_address', how='left')
    request_counts = df.groupby('ip_address').size().reset_index(name='request_count')
    df = df.merge(request_counts, on='ip_address', how='left')
    
    features = ['response_time', 'has_suspected_payload', 'error_rate', 'request_count']
    X = df[features]
    X.fillna(0, inplace=True)

    print("Entraînement du modèle d'Anomalie (Isolation Forest)...")
    model = IsolationForest(n_estimators=100, contamination=0.15, random_state=42)
    model.fit(X)

    joblib.dump(model, 'isolation_forest_model.joblib')
    print("Modèle sauvegardé sous 'isolation_forest_model.joblib'")

    print("\n------------------------------")
    print("TEST ET RESULTATS DE DETECTION")
    print("------------------------------")
    df['anomaly'] = model.predict(X)
    anomalies = df[df['anomaly'] == -1]
    df.to_csv("logs_features.csv", index=False)
    
    print(f"Total des requêtes scannées : {len(df)}")
    print(f"Nombre de requêtes d'attaques suspectes identifiées : {len(anomalies)}")
    
    print("\nTop 5 des Adresses IP classées dangereuses :")
    dangerous_ips = anomalies['ip_address'].value_counts()
    for ip, count in dangerous_ips.head(5).items():
        print(f" ⚠️  IP Suspecte: {ip} | Nombre de requêtes identifiées en anomalie: {count}")

    return True

if __name__ == "__main__":
    train_and_save()
