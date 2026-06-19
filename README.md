# POC Avantages Sportifs — Sport Data Solution

Ce projet est un POC (Proof of Concept) développé dans le cadre de ma formation Data Engineer chez OpenClassrooms. L'idée de départ est simple : automatiser le calcul des avantages sportifs accordés aux salariés d'une entreprise fictive, Sport Data Solution.

## C'est quoi concrètement ?

L'entreprise veut récompenser ses salariés qui ont une activité physique, que ce soit pour venir au bureau ou en dehors du travail. Deux avantages sont prévus :

- **Une prime de 5%** du salaire brut annuel pour les salariés qui viennent au bureau à pied, en vélo ou en trottinette (validé automatiquement via Google Maps)
- **5 jours de bien-être** pour les salariés qui font au moins 15 activités sportives dans l'année

Le pipeline que j'ai construit automatise tout ça : de la récupération des données RH jusqu'à l'envoi de notifications Slack et la visualisation dans Power BI.

## Stack technique

| Composant | Outil |
|---|---|
| Langage | Python + Pandas |
| Base de données | PostgreSQL |
| Streaming | Redpanda (compatible Kafka, via Docker) |
| Orchestration | Kestra (via Docker) |
| Qualité des données | Great Expectations v1 |
| Notifications | Slack |
| Reporting | Power BI |
| Versioning | GitHub |

## Architecture du projet

sport_data_poc/

├── data/

│   ├── raw/               ← fichiers Excel sources (non commités)

│   └── processed/

├── src/

│   ├── ingestion/         ← load_data.py : chargement Excel → PostgreSQL

│   ├── simulation/        ← strava_gen.py : génération activités sportives

│   ├── validation/        ← gmaps_check.py : validation trajets Google Maps

│   ├── eligibility/       ← compute.py : calcul des avantages

│   ├── quality/           ← expectations.py : tests Great Expectations

│   └── notifications/     ← producer.py + consumer.py : Redpanda → Slack

├── sql/

│   └── create_tables.sql  ← schéma de la base de données

├── orchestration/

│   └── pipeline.yml       ← flow Kestra

├── docker-compose.yml     ← Redpanda + Kestra

├── requirements.txt

└── README.md

## Comment faire tourner le projet

### Prérequis

- Python 3.11 + Anaconda
- PostgreSQL (local)
- Docker Desktop
- Power BI Desktop
- Clé API Google Maps
- Token Slack Bot

### Installation

```bash
# 1. Cloner le repo
git clone https://github.com/TabBah1/sport_data_poc.git
cd sport_data_poc

# 2. Créer et activer l'environnement
conda create -n sport_data_poc python=3.11 -y
conda activate sport_data_poc
conda install numpy -y
pip install -r requirements.txt

# 3. Créer le fichier .env
cp .env.example .env
# Remplir les variables dans .env
```

### Configuration `.env`

DATABASE_URL=postgresql://postgres:VOTRE_MOT_DE_PASSE@localhost:5432/sport_poc

GOOGLE_MAPS_API_KEY=votre_clé_google_maps

SLACK_BOT_TOKEN=xoxb-votre-token-slack

SLACK_CHANNEL=sport-data-poc

### Lancer l'infrastructure Docker

```bash
docker-compose up -d
```

### Créer la base de données

Dans pgAdmin, créer la base `sport_poc` puis exécuter :

```bash
psql -U postgres -d sport_poc -f sql/create_tables.sql
```

### Exécuter le pipeline manuellement

```bash
# Ingestion des données RH et sportives
python src/ingestion/load_data.py

# Simulation des activités (type Strava)
python src/simulation/strava_gen.py

# Validation des trajets via Google Maps
python src/validation/gmaps_check.py

# Calcul des avantages
python src/eligibility/compute.py

# Tests de qualité des données
python src/quality/expectations.py

# Streaming Redpanda → Slack
python src/notifications/producer.py
python src/notifications/consumer.py
```

### Orchestration avec Kestra

Kestra est accessible sur `http://localhost:8080`. Le flow `sport_data_pipeline` est configuré pour s'exécuter automatiquement chaque lundi à 8h.

## Résultats obtenus

Sur un échantillon de 161 salariés :

- **68 salariés** éligibles à la prime sportive (vélo, trottinette, marche/running)
- **94 salariés** éligibles aux 5 jours bien-être (≥ 15 activités/an)
- **172 482,50 €** de coût total des primes sportives
- **470 jours** bien-être accordés
- **2 500 activités** simulées sur 12 mois
- **Tous les tests Great Expectations** passés (3 tables validées)

## Données

Les fichiers Excel sources (`Données RH.xlsx` et `Données Sportive.xlsx`) ne sont pas commités dans ce repo car ils contiennent des données RH sensibles (même fictives). Ils doivent être placés dans `data/raw/` avant de lancer le pipeline.

## Auteur

Abdoulaye BAH — Formation Data Engineer, OpenClassrooms