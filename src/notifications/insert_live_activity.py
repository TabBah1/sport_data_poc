import os
import sys
import json
import logging
from datetime import datetime
from kafka import KafkaProducer
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

DB_URL = os.getenv("DATABASE_URL")
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "localhost:9092")
TOPIC = "sport-activities"

def get_engine():
    return create_engine(DB_URL)

def insert_activity(employee_id: int, sport_name: str, distance_m: int, duration_min: int, comment: str = None):
    """
    Insère une nouvelle activité sportive pour un salarié et la publie en direct
    sur Redpanda pour déclencher la notification Slack.
    Utilisé pour la démonstration live (insertion d'une nouvelle course en soutenance).
    """
    engine = get_engine()

    start_date = datetime.now()
    end_date_calc = start_date.timestamp() + (duration_min * 60)
    end_date = datetime.fromtimestamp(end_date_calc)

    with engine.connect() as conn:
        # Vérifier que le salarié existe
        employee = conn.execute(
            text("SELECT first_name, last_name FROM employees WHERE employee_id = :id"),
            {"id": employee_id}
        ).fetchone()

        if not employee:
            logger.error(f"Salarié {employee_id} introuvable.")
            return

        first_name, last_name = employee

        result = conn.execute(
            text("""
                INSERT INTO activities
                (employee_id, sport_name, start_date, end_date, distance_m, comment)
                VALUES (:employee_id, :sport_name, :start_date, :end_date, :distance_m, :comment)
                RETURNING activity_id
            """),
            {
                "employee_id": employee_id,
                "sport_name": sport_name,
                "start_date": start_date,
                "end_date": end_date,
                "distance_m": distance_m,
                "comment": comment,
            }
        )
        activity_id = result.fetchone()[0]
        conn.commit()

    logger.info(f"Activité {activity_id} insérée en base pour {first_name} {last_name}.")

    # Publication immédiate sur Redpanda
    producer = KafkaProducer(
        bootstrap_servers=KAFKA_BROKER,
        value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8")
    )

    message = {
        "activity_id": activity_id,
        "employee_id": employee_id,
        "first_name": first_name,
        "last_name": last_name,
        "sport_name": sport_name,
        "distance_m": distance_m,
        "start_date": str(start_date),
        "end_date": str(end_date),
        "comment": comment,
    }

    producer.send(TOPIC, value=message)
    producer.flush()
    producer.close()

    logger.info(f"Activité publiée sur le topic '{TOPIC}'. Lancez le consumer pour voir la notification Slack.")
    return activity_id

if __name__ == "__main__":
    # Exemple d'utilisation en ligne de commande :
    # python src/notifications/insert_live_activity.py <employee_id> <sport_name> <distance_m> <duration_min> "<commentaire>"
    if len(sys.argv) < 5:
        print("Usage : python insert_live_activity.py <employee_id> <sport_name> <distance_m> <duration_min> [commentaire]")
        print('Exemple : python src/notifications/insert_live_activity.py 43015 "Course à pied" 10800 46 "Super sortie matinale"')
        sys.exit(1)

    employee_id = int(sys.argv[1])
    sport_name = sys.argv[2]
    distance_m = int(sys.argv[3]) if sys.argv[3] != "0" else None
    duration_min = int(sys.argv[4])
    comment = sys.argv[5] if len(sys.argv) > 5 else None

    insert_activity(employee_id, sport_name, distance_m, duration_min, comment)