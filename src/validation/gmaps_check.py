import os
import time
import logging
import requests
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

DB_URL = os.getenv("DATABASE_URL")
GMAPS_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
COMPANY_ADDRESS = "1362 Av. des Platanes, 34970 Lattes, France"

# Règles de validation (en km)
LIMITS = {
    "walking_running": 15,
    "cycling_scooter": 25,
}

GMAPS_MODE = {
    "walking_running": "walking",
    "cycling_scooter": "bicycling",
}

def get_engine():
    if not DB_URL:
        raise ValueError("DATABASE_URL manquant dans .env")
    return create_engine(DB_URL)

def log_pipeline(engine, step, status, message):
    with engine.connect() as conn:
        conn.execute(
            text("INSERT INTO pipeline_logs (step, status, message) VALUES (:step, :status, :message)"),
            {"step": step, "status": status, "message": message}
        )
        conn.commit()

def get_distance_km(origin: str, mode: str) -> float | None:
    url = "https://maps.googleapis.com/maps/api/distancematrix/json"
    params = {
        "origins": origin,
        "destinations": COMPANY_ADDRESS,
        "mode": mode,
        "key": GMAPS_KEY,
    }
    try:
        r = requests.get(url, params=params, timeout=10)
        data = r.json()
        if data["status"] == "OK":
            element = data["rows"][0]["elements"][0]
            if element["status"] == "OK":
                return element["distance"]["value"] / 1000
    except Exception as e:
        logger.warning(f"Erreur API Google Maps : {e}")
    return None

def validate_commutes(engine):
    logger.info("Récupération des salariés à valider...")

    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT employee_id, address, commute_mode
            FROM employees
            WHERE commute_mode IN ('walking_running', 'cycling_scooter')
        """))
        salaries = result.fetchall()

    logger.info(f"{len(salaries)} salariés à valider.")
    validations = []

    for i, (employee_id, address, commute_mode) in enumerate(salaries):
        gmaps_mode = GMAPS_MODE[commute_mode]
        limit_km = LIMITS[commute_mode]

        logger.info(f"[{i+1}/{len(salaries)}] Salarié {employee_id} — {commute_mode} — {address}")

        distance_km = get_distance_km(address, gmaps_mode)

        if distance_km is None:
            is_valid = False
            reason = "Impossible de calculer la distance via Google Maps"
        elif distance_km <= limit_km:
            is_valid = True
            reason = None
        else:
            is_valid = False
            reason = f"Distance {distance_km:.1f} km > limite {limit_km} km pour {commute_mode}"

        validations.append({
            "employee_id":     employee_id,
            "distance_km":     distance_km,
            "commute_mode":    commute_mode,
            "is_valid":        is_valid,
            "rejection_reason": reason,
        })

        # Pause pour respecter les limites de l'API Google
        time.sleep(0.2)

    # Insertion en base
    with engine.connect() as conn:
        for v in validations:
            conn.execute(
                text("""
                    INSERT INTO commute_validation
                    (employee_id, distance_km, commute_mode, is_valid, rejection_reason)
                    VALUES (:employee_id, :distance_km, :commute_mode, :is_valid, :rejection_reason)
                """),
                v
            )
        conn.commit()

    valides = sum(1 for v in validations if v["is_valid"])
    invalides = len(validations) - valides
    logger.info(f"Validation terminée : {valides} valides, {invalides} invalides.")
    return len(validations)

def run():
    engine = get_engine()
    try:
        count = validate_commutes(engine)
        log_pipeline(engine, "gmaps_validation", "success", f"{count} trajets validés")
    except Exception as e:
        logger.error(f"Erreur validation : {e}")
        log_pipeline(engine, "gmaps_validation", "error", str(e))
        raise

if __name__ == "__main__":
    run()