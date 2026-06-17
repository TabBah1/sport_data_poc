import os
import logging
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

DB_URL = os.getenv("DATABASE_URL")

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

def compute_advantages(engine):
    logger.info("Calcul des avantages en cours...")

    with engine.connect() as conn:
        # Récupérer tous les salariés
        employees = conn.execute(text("""
            SELECT employee_id, gross_salary, commute_mode
            FROM employees
        """)).fetchall()

        # Salariés avec trajet valide
        valid_commutes = conn.execute(text("""
            SELECT DISTINCT employee_id
            FROM commute_validation
            WHERE is_valid = TRUE
        """)).fetchall()
        valid_commute_ids = {row[0] for row in valid_commutes}

        # Nombre d'activités par salarié sur les 12 derniers mois
        activity_counts = conn.execute(text("""
            SELECT employee_id, COUNT(*) as nb_activities
            FROM activities
            WHERE start_date >= NOW() - INTERVAL '12 months'
            GROUP BY employee_id
        """)).fetchall()
        activity_map = {row[0]: row[1] for row in activity_counts}

    results = []
    prime_count = 0
    wellness_count = 0

    for employee_id, gross_salary, commute_mode in employees:
        salary_bonus = 0
        wellness_days = 0
        nb_activities = activity_map.get(employee_id, 0)

        # Prime 5% : trajet sportif + validé
        if commute_mode in ("walking_running", "cycling_scooter") and employee_id in valid_commute_ids:
            salary_bonus = round(float(gross_salary) * 0.05, 2)
            prime_count += 1

        # 5 jours bien-être : >= 15 activités
        if nb_activities >= 15:
            wellness_days = 5
            wellness_count += 1

        results.append({
            "employee_id":   employee_id,
            "salary_bonus":  salary_bonus,
            "wellness_days": wellness_days,
            "activity_count": nb_activities,
        })

    # Insertion en base
    with engine.connect() as conn:
        for r in results:
            conn.execute(
                text("""
                    INSERT INTO advantages
                    (employee_id, salary_bonus, wellness_days, activity_count)
                    VALUES (:employee_id, :salary_bonus, :wellness_days, :activity_count)
                """),
                r
            )
        conn.commit()

    total_bonus = sum(r["salary_bonus"] for r in results)
    logger.info(f"{prime_count} salariés éligibles à la prime sportive.")
    logger.info(f"{wellness_count} salariés éligibles aux jours bien-être.")
    logger.info(f"Coût total des primes : {total_bonus:,.2f} €")
    return len(results)

def run():
    engine = get_engine()
    try:
        count = compute_advantages(engine)
        log_pipeline(engine, "compute_advantages", "success", f"{count} salariés traités")
    except Exception as e:
        logger.error(f"Erreur calcul avantages : {e}")
        log_pipeline(engine, "compute_advantages", "error", str(e))
        raise

if __name__ == "__main__":
    run()