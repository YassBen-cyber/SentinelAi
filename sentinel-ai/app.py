import os
from flask import Flask, jsonify, render_template, send_file
from flask_cors import CORS
import psycopg2
import pandas as pd
import joblib
import datetime
import io
import threading
import time
from train_model import train_and_save

app = Flask(__name__)
CORS(app)

model = None
try:
    if os.path.exists('isolation_forest_model.joblib'):
        model = joblib.load('isolation_forest_model.joblib')
except Exception as e:
    print(f"Erreur au chargement du modèle initial : {e}")

# Tâche de fond pour l'entraînement automatique du modèle
def auto_train_task():
    global model
    while True:
        try:
            print("Lancement de l'entraînement automatique du modèle en tâche de fond...")
            success = train_and_save()
            if success:
                print("Mise à jour du modèle IA en mémoire terminée avec succès.")
                model = joblib.load('isolation_forest_model.joblib')
        except Exception as e:
            print(f"Erreur durant l'entraînement automatique : {e}")
        
        # Le modèle s'entraîne automatiquement toutes les heures
        time.sleep(3600)

threading.Thread(target=auto_train_task, daemon=True).start()

def get_db_connection():
    return psycopg2.connect(
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASS"),
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT")
    )

alerted_ips = set()

@app.route('/')
def dashboard():
    return render_template('index.html')

@app.route('/api/stats', methods=['GET'])
def get_stats():
    try:
        conn = get_db_connection()
        # Prendre les dernières 1000 requêtes pour analyse en temps quasi-réel
        query = "SELECT ip_address, timestamp, endpoint, method, status_code, response_time, suspected_payload FROM api_logs ORDER BY timestamp DESC LIMIT 1000"
        df = pd.read_sql_query(query, conn)
        conn.close()

        if df.empty:
            return jsonify({"error": "No data found"})

        global model
        if model is None:
            return jsonify({"error": "Le modèle est en cours d'entraînement. Veuillez patienter et réessayer dans quelques instants."}), 503

        # Feature Engineering (Identique à l'entraînement)
        df['has_suspected_payload'] = df['suspected_payload'].notnull().astype(int)
        df['is_error'] = (df['status_code'] >= 400).astype(int)
        
        error_rates = df.groupby('ip_address')['is_error'].mean().reset_index().rename(columns={'is_error': 'error_rate'})
        df = df.merge(error_rates, on='ip_address', how='left')
        
        request_counts = df.groupby('ip_address').size().reset_index(name='request_count')
        df = df.merge(request_counts, on='ip_address', how='left')

        features = ['response_time', 'has_suspected_payload', 'error_rate', 'request_count']
        X = df[features].copy()
        X.fillna(0, inplace=True)

        # Prévision avec Isolation Forest
        df['anomaly'] = model.predict(X)
        anomalies = df[df['anomaly'] == -1]

        # Préparation des données pour le dashboard
        total_requests = int(len(df))
        total_anomalies = int(len(anomalies))
        anomalies_percentage = round((total_anomalies / total_requests) * 100, 1)

        top_ips = anomalies['ip_address'].value_counts().head(5).to_dict()
        top_ips_list = [{"ip": ip, "count": count} for ip, count in top_ips.items()]

        anomalies_list = anomalies.head(20)[['timestamp', 'ip_address', 'endpoint', 'method', 'response_time', 'status_code']].to_dict(orient='records')
        for r in anomalies_list:
            r['timestamp'] = str(r['timestamp'])

        return jsonify({
            "total_requests": total_requests,
            "total_anomalies": total_anomalies,
            "anomalies_percentage": anomalies_percentage,
            "top_ips": top_ips_list,
            "recent_anomalies": anomalies_list,
            "new_alerts": new_alerts
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/report/download', methods=['GET'])
def download_report():
    try:
        conn = get_db_connection()
        query = "SELECT ip_address, timestamp, endpoint, method, status_code, response_time, suspected_payload FROM api_logs ORDER BY timestamp DESC LIMIT 2000"
        df = pd.read_sql_query(query, conn)
        conn.close()

        if df.empty:
            return jsonify({"error": "No data for report"}), 404

        global model
        if model is None:
            return jsonify({"error": "Le modèle est en cours d'entraînement. Veuillez patienter et réessayer dans quelques instants."}), 503

        df['has_suspected_payload'] = df['suspected_payload'].notnull().astype(int)
        df['is_error'] = (df['status_code'] >= 400).astype(int)
        error_rates = df.groupby('ip_address')['is_error'].mean().reset_index().rename(columns={'is_error': 'error_rate'})
        df = df.merge(error_rates, on='ip_address', how='left')
        request_counts = df.groupby('ip_address').size().reset_index(name='request_count')
        df = df.merge(request_counts, on='ip_address', how='left')

        features = ['response_time', 'has_suspected_payload', 'error_rate', 'request_count']
        X = df[features].copy()
        X.fillna(0, inplace=True)
        df['anomaly'] = model.predict(X)
        anomalies = df[df['anomaly'] == -1]

        report_lines = []
        report_lines.append(f"=== RAPPORT DE SECURITE SENTINEL AI ===")
        report_lines.append(f"Généré le: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append(f"Total requêtes analysées: {len(df)}")
        report_lines.append(f"Total menaces détectées: {len(anomalies)}\n")
        
        top_ips = anomalies['ip_address'].value_counts().head(5)
        report_lines.append("--- TOP IP ATTAQUANTES ---")
        for ip, count in top_ips.items():
            report_lines.append(f"- IP: {ip} | {count} requêtes malveillantes")
        
        report_lines.append("\n--- DERNIERES ATTAQUES ---")
        for _, row in anomalies.head(50).iterrows():
            report_lines.append(f"[{row['timestamp']}] {row['ip_address']} -> {row['method']} {row['endpoint']} (Status: {row['status_code']})")

        buffer = io.BytesIO()
        buffer.write("\n".join(report_lines).encode('utf-8'))
        buffer.seek(0)
        
        return send_file(buffer, as_attachment=True, download_name=f"sentinel_report_{datetime.datetime.now().strftime('%Y%m%d')}.txt", mimetype='text/plain')
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
