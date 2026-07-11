import os
import json
import logging
from kafka import KafkaConsumer
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "localhost:9092")
TOPIC = "sport-activities"
SLACK_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_CHANNEL = os.getenv("SLACK_CHANNEL")

def format_message(activity: dict) -> str:
    first_name = activity.get("first_name", "")
    last_name  = activity.get("last_name", "")
    sport      = activity.get("sport_name", "")
    distance_m = activity.get("distance_m")
    comment    = activity.get("comment")
    start_str  = activity.get("start_date")
    end_str    = activity.get("end_date")

    # Calcul de la durée en minutes
    duration_min = None
    if start_str and end_str:
        try:
            start = datetime.fromisoformat(start_str)
            end = datetime.fromisoformat(end_str)
            duration_min = round((end - start).total_seconds() / 60)
        except (ValueError, TypeError):
            duration_min = None

    # Verbe selon le sport
    verbe = {
        "Running": "courir",
        "Course à pied": "courir",
        "Randonnée": "marcher",
        "Natation": "nager",
    }.get(sport, f"faire du {sport}")

    if distance_m and duration_min:
        distance_km = round(distance_m / 1000, 1)
        msg = f"Bravo {first_name} {last_name} ! Tu viens de {verbe} {distance_km} km en {duration_min} min !"
    elif duration_min:
        msg = f"Bravo {first_name} {last_name} ! Tu viens de faire {duration_min} min de {sport} !"
    else:
        msg = f"Bravo {first_name} {last_name} ! Séance de {sport} terminée !"

    if comment:
        msg += f' ("{comment}")'

    return msg

def run():
    client = WebClient(token=SLACK_TOKEN)

    consumer = KafkaConsumer(
        TOPIC,
        bootstrap_servers=KAFKA_BROKER,
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        auto_offset_reset="latest",
        group_id="slack-notifier"
    )

    logger.info(f"Consumer démarré — écoute du topic '{TOPIC}'...")
    count = 0

    for message in consumer:
        activity = message.value
        text = format_message(activity)

        try:
            client.chat_postMessage(channel=SLACK_CHANNEL, text=text)
            logger.info(f"Slack ✓ : {activity['first_name']} {activity['last_name']}")
            count += 1
        except SlackApiError as e:
            logger.error(f"Erreur Slack : {e.response['error']}")

    consumer.close()
    logger.info(f"{count} messages envoyés sur Slack.")

if __name__ == "__main__":
    run()