# POC Avantages Sportifs — Sport Data Solution (Option B)

Ce projet est un POC (Proof of Concept) développé dans le cadre de ma formation Data Engineer chez OpenClassrooms. L'objectif : automatiser le calcul des avantages sportifs accordés aux salariés d'une entreprise fictive, Sport Data Solution.

## C'est quoi concrètement ?

L'entreprise veut récompenser ses salariés qui ont une activité physique, que ce soit pour venir au bureau ou en dehors du travail. Deux avantages sont prévus :

- **Une prime de 5%** du salaire brut annuel pour les salariés qui viennent au bureau à pied, en vélo ou en trottinette (validé automatiquement via Google Maps)
- **5 jours de bien-être** pour les salariés qui font au moins 15 activités sportives dans l'année

Le pipeline automatise tout : de la récupération des données RH jusqu'à l'envoi de notifications Slack en temps réel et la visualisation dans Power BI.

## Stack technique

| Composant | Outil |
|---|---|
| Langage | Python + Pandas |
| Base de données | PostgreSQL |
| Streaming | Redpanda (compatible Kafka, via Docker) |
| Orchestration | Kestra (via Docker) |
| Qualité des données | Great Expectations v1 |
| Notifications | Slack (automatique à chaque activité) |
| Reporting | Power BI (2 pages : KPIs + Monitoring) |
| Versioning | GitHub |

## Architecture du projet

```
sport_data_poc/
├── data/
│   ├── raw/                        ← fichiers Excel sources (non commités)
│   └── processed/
├── src/
│   ├── ingestion/                  ← load_data.py : chargement Excel → PostgreSQL
│   ├── simulation/                 ← strava_gen.py : génération activités sportives
│   ├── validation/                 ← gmaps_check.py : validation trajets Google Maps
│   ├── eligibility/                ← compute.py : calcul des avantages
│   ├── quality/                    ← expectations.py : tests Great Expectations
│   └── notifications/
│       ├── producer.py             ← publie les activités sur Redpanda
│       ├── consumer.py             ← écoute Redpanda et envoie sur Slack (permanent)
│       └── insert_live_activity.py ← insertion d'une activité en temps réel
├── sql/
│   └── create_tables.sql           ← schéma PostgreSQL avec commentaires français
├── orchestration/
│   └── pipeline.yml                ← flow Kestra (WorkingDirectory + git.Clone)
├── docker-compose.example.yml      ← template Docker sans secrets
├── generate_secrets.py             ← génère les secrets base64 pour Kestra
├── .env.example                    ← template des variables d'environnement
├── requirements.txt
└── README.md
```

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

# 3. Créer le fichier .env depuis le template
cp .env.example .env
# Remplir les variables dans .env avec vos vraies valeurs
```

### Configuration `.env`

```
DATABASE_URL=postgresql://postgres:VOTRE_MOT_DE_PASSE@localhost:5432/sport_poc
GOOGLE_MAPS_API_KEY=votre_clé_google_maps
SLACK_BOT_TOKEN=xoxb-votre-token-slack
SLACK_CHANNEL=sport-data-poc
BONUS_RATE=0.05
WELLNESS_MIN_ACTIVITIES=15
WELLNESS_DAYS=5
```

### Lancer l'infrastructure Docker

```bash
# Copier et compléter le fichier docker-compose
cp docker-compose.example.yml docker-compose.yml
# Générer les secrets Kestra (base64) depuis votre .env
python generate_secrets.py
# Remplir docker-compose.yml avec les valeurs générées, puis :
docker-compose up -d
```

### Créer la base de données

Dans pgAdmin, créer la base `sport_poc` et la base `kestra`, puis exécuter :

```bash
psql -U postgres -d sport_poc -f sql/create_tables.sql
```

### Exécuter le pipeline manuellement

```bash
# Ingestion des données RH et sportives (idempotent)
python src/ingestion/load_data.py

# Simulation des activités type Strava (idempotent)
python src/simulation/strava_gen.py

# Validation des trajets via Google Maps API (idempotent)
python src/validation/gmaps_check.py

# Calcul des avantages (idempotent + paramétrable via .env)
python src/eligibility/compute.py

# Tests de qualité des données
python src/quality/expectations.py

# Démarrer le consumer Slack en écoute permanente
python src/notifications/consumer.py

# Publier les activités existantes sur Redpanda
python src/notifications/producer.py
```

### Insérer une activité en temps réel (démo live)

```bash
# Terminal 1 : consumer en écoute permanente
python src/notifications/consumer.py

# Terminal 2 : insérer une nouvelle activité
python src/notifications/insert_live_activity.py <employee_id> "<sport>" <distance_m> <duree_min> "<commentaire>"

# Exemple :
python src/notifications/insert_live_activity.py 59019 "Course à pied" 10800 46 "Super sortie matinale"
# → Activité insérée en base + message Slack automatique
# → Actualiser Power BI pour voir la mise à jour
```

### Modifier les paramètres à la volée

Cinq paramètres sont configurables dans `.env` sans toucher au code :

| Variable | Effet | Script à relancer |
|---|---|---|
| `BONUS_RATE` | Taux de la prime sportive (défaut 5%) | `compute.py` |
| `WELLNESS_MIN_ACTIVITIES` | Seuil d'activités pour les jours bien-être (défaut 15) | `compute.py` |
| `WELLNESS_DAYS` | Nombre de jours bien-être accordés (défaut 5) | `compute.py` |
| `WALKING_MAX_KM` | Distance max marche/running validée (défaut 15 km) | `gmaps_check.py` puis `compute.py` |
| `CYCLING_MAX_KM` | Distance max vélo/trottinette validée (défaut 25 km) | `gmaps_check.py` puis `compute.py` |

```bash
# Exemple : changer le taux de prime
# Dans .env :
BONUS_RATE=0.07

# Puis relancer :
python src/eligibility/compute.py
# → Nouveau coût calculé et mis à jour en base
# → Actualiser Power BI pour voir l'évolution
```

```bash
# Exemple : changer les seuils de distance de trajet
# Dans .env :
WALKING_MAX_KM=20

# Ces paramètres affectent la validation Google Maps, donc relancer dans cet ordre :
python src/validation/gmaps_check.py   # ~30-60s, appelle l'API Google Maps
python src/eligibility/compute.py
```

> **Reproductibilité :** `strava_gen.py` utilise une graine aléatoire fixe (`random.seed(42)`), donc les chiffres ci-dessus restent identiques à chaque exécution du pipeline, tant que le nombre de salariés/sports ne change pas.

### Orchestration avec Kestra

Kestra est accessible sur `http://localhost:8080`. Le flow `sport_data_pipeline` :
- Clone automatiquement le repo GitHub
- Enchaîne toutes les étapes du pipeline
- S'exécute automatiquement chaque lundi à 8h
- Journalise chaque étape dans `pipeline_logs`

## Résultats obtenus

Sur un échantillon de 161 salariés :

- **68 salariés** éligibles à la prime sportive (vélo, trottinette, marche/running)
- **95 salariés** éligibles aux 5 jours bien-être (≥ 15 activités/an)
- **172 483 €** de coût total des primes sportives (taux 5%)
- **475 jours** bien-être accordés
- **~2 500 activités** simulées sur 12 mois
- **Tous les tests Great Expectations passés** (3 tables validées)

## Monitoring

La table `pipeline_logs` trace chaque exécution du pipeline (étape, statut, message, horodatage). Le dashboard Power BI inclut une page dédiée au monitoring avec :
- Journal d'exécution complet
- Statuts par étape (vert = succès, rouge = erreur)
- Date de la dernière exécution

## Sécurité

- Le fichier `.env` (clés API, tokens) n'est jamais commité
- Le fichier `docker-compose.yml` (secrets Kestra encodés) n'est jamais commité
- Les templates `.env.example` et `docker-compose.example.yml` sont fournis
- `generate_secrets.py` permet de régénérer les secrets à partir du `.env` local

## Données

Les fichiers Excel sources ne sont pas commités (données RH sensibles). Ils doivent être placés dans `data/raw/` avant de lancer le pipeline.

## Auteur

Abdoulaye BAH — Formation Data Engineer, OpenClassrooms — Option B