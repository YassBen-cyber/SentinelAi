# Utiliser une image Python légère
FROM python:3.11-slim

# Définir le répertoire de travail dans le conteneur
WORKDIR /app

# Copier le fichier de dépendances et installer
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier tout le code de l'application (modèle, app.py, templates, etc.)
COPY . .

# Exposer le port du dashboard
EXPOSE 5000

# Commande pour démarrer l'application
CMD ["python", "app.py"]
