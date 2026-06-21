import os
import logging
import random
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from pathlib import Path
from faker import Faker

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

DB_URL = os.getenv("DATABASE_URL")
fake = Faker("fr_FR")

# Paramètres par sport : (distance_min_m, distance_max_m, duree_min_min, duree_max_min, avec_distance)
SPORT_PARAMS = {
    "Running":        (3000,  20000, 20,  90,  True),
    "Randonnée":      (5000,  25000, 60,  240, True),
    "Tennis":         (0,     0,     45,  120, False),
    "Natation":       (500,   5000,  20,  90,  True),
    "Football":       (0,     0,     60,  120, False),
    "Rugby":          (0,     0,     60,  120, False),
    "Badminton":      (0,     0,     45,  90,  False),
    "Voile":          (0,     0,     120, 300, False),
    "Boxe":           (0,     0,     45,  90,  False),
    "Judo":           (0,     0,     45,  90,  False),
    "Escalade":       (0,     0,     60,  180, False),
    "Triathlon":      (10000, 50000, 90,  300, True),
    "Tennis de table":(0,     0,     30,  90,  False),
    "Équitation":     (0,     0,     60,  180, False),
    "Basketball":     (0,     0,     60,  120, False),
}

COMMENTAIRES = {
    "Running":        ["Belle sortie !", "Reprise du sport :)", "Objectif 10km bientôt !", None],
    "Randonnée":      ["Superbe paysage !", "Je vous la conseille c'est top", "Randonnée du dimanche", None],
    "Tennis":         ["Belle partie !", "Victoire aujourd'hui !", None],
    "Natation":       ["Séance intensive !", "Crawl + dos crawlé", None],
    "Football":       ["Match de folie !", "Entraînement du club", None],
    "Rugby":          ["Entraînement !", "Match du week-end", None],
    "Badminton":      ["Bonne séance !", None],
    "Voile":          ["Vent parfait aujourd'hui !", "Sortie en mer", None],
    "Boxe":           ["Séance de sparring !", None],
    "Judo":           ["Passage de grade bientôt !", None],
    "Escalade":       ["Nouveau mur aujourd'hui !", "Bloc 6b passé !", None],
    "Triathlon":      ["Enchaînement parfait !", "Préparation compétition", None],
    "Tennis de table":["Match serré !", None],
    "Équitation":     ["Belle balade !", None],
    "Basketball":     ["Entraînement du club", None],
}

def get_engine():
    if not DB_URL:
        raise ValueError("DATABASE_URL manquant dans .env")
    return create_engine(DB_URL)

def log_pipeline(engine, step: str, status: str, message: str):
    with engine.connect() as conn:
        conn.execute(
            text("INSERT INTO pipeline_logs (step, status, message) VALUES (:step, :status, :message)"),
            {"step": step, "status": status, "message": message}
        )
        conn.commit()

def generate_activities(engine) -> int:
    logger.info("Récupération des salariés avec sport déclaré...")

    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT e.employee_id, s.sport_name
            FROM employees e
            JOIN sports s ON e.employee_id = s.employee_id
            WHERE s.sport_name IS NOT NULL
        """))
        salaries = result.fetchall()

    logger.info(f"{len(salaries)} salariés avec sport déclaré.")

    date_fin = datetime.now()
    date_debut = date_fin - timedelta(days=365)

    activities = []

    for employee_id, sport_name in salaries:
        if sport_name not in SPORT_PARAMS:
            continue

        dist_min, dist_max, dur_min, dur_max, avec_distance = SPORT_PARAMS[sport_name]

        # Entre 15 et 40 activités par salarié sur 12 mois
        nb_activites = random.randint(15, 40)

        for _ in range(nb_activites):
            # Date aléatoire dans les 12 derniers mois
            jours_aleatoires = random.randint(0, 365)
            start = date_debut + timedelta(days=jours_aleatoires)
            # Heure réaliste : matin (6h-9h) ou soir (17h-20h)
            heure = random.choice([
                random.randint(6, 9),
                random.randint(17, 20)
            ])
            start = start.replace(hour=heure, minute=random.randint(0, 59), second=0)

            duree_min = random.randint(dur_min, dur_max)
            end = start + timedelta(minutes=duree_min)

            distance = None
            if avec_distance:
                distance = random.randint(dist_min, dist_max)

            commentaire = random.choice(COMMENTAIRES.get(sport_name, [None]))

            activities.append({
                "employee_id": employee_id,
                "sport_name":  sport_name,
                "start_date":  start,
                "end_date":    end,
                "distance_m":  distance,
                "comment":     commentaire,
            })

    df = pd.DataFrame(activities)
    df.to_sql("activities", engine, if_exists="append", index=False)

    logger.info(f"{len(df)} activités générées et insérées.")
    return len(df)

def truncate_activities(engine):
    with engine.connect() as conn:
        conn.execute(text("TRUNCATE TABLE activities RESTART IDENTITY"))
        conn.commit()
    logger.info("Table activities vidée (idempotence).")

def run():
    engine = get_engine()
    truncate_activities(engine)
    try:
        count = generate_activities(engine)
        log_pipeline(engine, "strava_gen", "success", f"{count} activités simulées")
    except Exception as e:
        logger.error(f"Erreur simulation : {e}")
        log_pipeline(engine, "strava_gen", "error", str(e))
        raise

if __name__ == "__main__":
    run()