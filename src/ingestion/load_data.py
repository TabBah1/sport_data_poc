import os
import logging
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

DB_URL = os.getenv("DATABASE_URL")

BASE_DIR = Path(__file__).resolve().parent.parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"
HR_FILE = RAW_DIR / "Donnees RH.xlsx"
SPORT_FILE = RAW_DIR / "Donnees Sportive.xlsx"

COMMUTE_MAP = {
    "marche/running":                "walking_running",
    "vélo/trottinette/autres":       "cycling_scooter",
    "transports en commun":          "transit",
    "véhicule thermique/électrique": "car",
}

SPORT_NORM = {
    "Runing": "Running",
}

def get_engine():
    if not DB_URL:
        raise ValueError("DATABASE_URL manquant dans .env")
    return create_engine(DB_URL)

def log_pipeline(engine, step: str, status: str, message: str):
    with engine.connect() as conn:
        conn.execute(
            text("""
                INSERT INTO pipeline_logs (step, status, message)
                VALUES (:step, :status, :message)
            """),
            {"step": step, "status": status, "message": message}
        )
        conn.commit()

def load_hr_data(engine) -> int:
    logger.info("Chargement Données RH...")
    df = pd.read_excel(HR_FILE)

    df = df.rename(columns={
        "ID salarié":            "employee_id",
        "Nom":                   "last_name",
        "Prénom":                "first_name",
        "Date de naissance":     "birth_date",
        "BU":                    "business_unit",
        "Date d'embauche":       "hire_date",
        "Salaire brut":          "gross_salary",
        "Type de contrat":       "contract_type",
        "Nombre de jours de CP": "leave_days",
        "Adresse du domicile":   "address",
        "Moyen de déplacement":  "commute_mode",
    })

    df["employee_id"] = df["employee_id"].astype(int)
    df["commute_mode"] = (
        df["commute_mode"]
        .str.strip()
        .str.lower()
        .map(COMMUTE_MAP)
        .fillna("unknown")
    )
    df["birth_date"] = pd.to_datetime(df["birth_date"], errors="coerce")
    df["hire_date"] = pd.to_datetime(df["hire_date"], errors="coerce")
    df = df.dropna(subset=["employee_id"])

    df.to_sql("employees", engine, if_exists="append", index=False)
    logger.info(f"{len(df)} salariés chargés.")
    return len(df)

def load_sport_data(engine) -> int:
    logger.info("Chargement Données Sportives...")
    df = pd.read_excel(SPORT_FILE)

    df = df.rename(columns={
        "ID salarié":          "employee_id",
        "Pratique d'un sport": "sport_name",
    })

    df["employee_id"] = df["employee_id"].astype(int)
    df["sport_name"] = df["sport_name"].replace(SPORT_NORM)

    df[["employee_id", "sport_name"]].to_sql(
        "sports", engine, if_exists="append", index=False
    )
    logger.info(f"{len(df)} lignes sport chargées ({df['sport_name'].isna().sum()} sans sport déclaré).")
    return len(df)

def run():
    engine = get_engine()
    for step, fn in [("load_hr", load_hr_data), ("load_sports", load_sport_data)]:
        try:
            count = fn(engine)
            log_pipeline(engine, step, "success", f"{count} lignes insérées")
        except Exception as e:
            logger.error(f"Erreur étape {step} : {e}")
            log_pipeline(engine, step, "error", str(e))
            raise

if __name__ == "__main__":
    run()