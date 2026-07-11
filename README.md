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

```bash
# Dans .env, changer par exemple :
BONUS_RATE=0.07

# Puis relancer :
python src/eligibility/compute.py
# → Nouveau coût calculé et mis à jour en base
# → Actualiser Power BI pour voir l'évolution
```

### Orchestration avec Kestra

Kestra est accessible sur `http://localhost:8080`. Le flow `sport_data_pipeline` :
- Clone automatiquement le repo GitHub
- Enchaîne toutes les étapes du pipeline
- S'exécute automatiquement chaque lundi à 8h
- Journalise chaque étape dans `pipeline_logs`

## Résultats obtenus

Sur un échantillon de 161 salariés :

- **68 salariés** éligibles à la prime sportive (vélo, trottinette, marche/running)
- **94 salariés** éligibles aux 5 jours bien-être (≥ 15 activités/an)
- **172 482,50 €** de coût total des primes sportives (taux 5%)
- **470 jours** bien-être accordés
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