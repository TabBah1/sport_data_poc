import os
import json
import logging
import time
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
    if not DB_URL:
        raise ValueError("DATABASE_URL manquant dans .env")
    return create_engine(DB_URL)

def run():
    engine = get_engine()
    producer = KafkaProducer(
        bootstrap_servers=KAFKA_BROKER,
        value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8")
    )

    logger.info("Récupération des activités récentes...")
    with engine.connect() as conn:
        activities = conn.execute(text("""
            SELECT a.activity_id, a.employee_id, e.first_name, e.last_name,
                   a.sport_name, a.distance_m, a.start_date, a.end_date, a.comment
            FROM activities a
            JOIN employees e ON a.employee_id = e.employee_id
            ORDER BY RANDOM()
            LIMIT 20
        """)).fetchall()

    logger.info(f"{len(activities)} activités à publier sur le topic '{TOPIC}'...")

    for row in activities:
        message = {
            "activity_id": row[0],
            "employee_id": row[1],
            "first_name":  row[2],
            "last_name":   row[3],
            "sport_name":  row[4],
            "distance_m":  row[5],
            "start_date":  str(row[6]),
            "end_date":    str(row[7]),
            "comment":     row[8],
        }
        producer.send(TOPIC, value=message)
        logger.info(f"Publié : {message['first_name']} {message['last_name']} — {message['sport_name']}")
        time.sleep(0.1)

    producer.flush()
    producer.close()
    logger.info("Tous les messages publiés.")

if __name__ == "__main__":
    run()