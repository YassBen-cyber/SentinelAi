# Sentinel AI 🛡️

Sentinel AI est un système intelligent de détection de menaces pour les API. Il surveille le trafic entrant, détecte les anomalies en temps réel à l'aide de modèles de Machine Learning (Isolation Forest) et fournit un tableau de bord analytique.

## 🏗️ Architecture du Projet

Le projet est divisé en plusieurs microservices conteneurisés avec Docker :

- **Sentinel API (Backend)** : Application Java Spring Boot responsable de la gestion des logs d'API et de l'authentification.
- **Sentinel AI (Dashboard & ML)** : Application Python Flask qui analyse les logs pour détecter les comportements malveillants et sert l'interface utilisateur.
- **Base de données** : PostgreSQL pour stocker l'historique des requêtes et les alertes.
- **Générateur de Trafic** : Un script Python automatisé simulant du trafic normal et des attaques (Brute Force, SQL Injection) lors du premier lancement.

## 🚀 Démarrage Rapide

Assurez-vous d'avoir **Docker** et **Docker Compose** installés sur votre machine.

1. Clonez ce dépôt.
2. À la racine du projet, lancez la commande suivante :

```bash
docker-compose up --build -d
```

Cette commande va construire les images, démarrer les conteneurs et générer automatiquement un jeu de données initial (trafic normal et attaques).

## 🌐 Accès aux Services

Une fois les conteneurs démarrés, vous pouvez accéder aux différents services via votre navigateur :

- **Dashboard IA (Interface Web)** : [http://localhost:5000](http://localhost:5000)
- **API Backend (Java)** : [http://localhost:8080](http://localhost:8080)
- **Base de données (PostgreSQL)** : `localhost:5432` (Utilisateur: `postgres`, Mot de passe: `postgres`)

## 🛠️ Technologies Utilisées

- **Backend** : Java, Spring Boot
- **IA & Dashboard** : Python, Flask, Scikit-Learn (Isolation Forest), Pandas
- **Base de données** : PostgreSQL
- **Déploiement** : Docker, Docker Compose
