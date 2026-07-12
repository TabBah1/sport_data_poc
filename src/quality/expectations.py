import os
import logging
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import great_expectations as gx

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

def log_pipeline(engine, step: str, status: str, message: str):
    with engine.connect() as conn:
        conn.execute(
            text("INSERT INTO pipeline_logs (step, status, message) VALUES (:step, :status, :message)"),
            {"step": step, "status": status, "message": message}
        )
        conn.commit()

def run_expectations():
    engine = get_engine()
    context = gx.get_context()
    results_summary = []

    # ─── 1. TABLE EMPLOYEES ───────────────────────────────────────
    logger.info("Tests sur la table employees...")
    df_employees = pd.read_sql("SELECT * FROM employees", engine)
    ds = context.data_sources.add_pandas("employees_source")
    da = ds.add_dataframe_asset("employees_asset")
    batch = da.add_batch_definition_whole_dataframe("employees_batch").get_batch(
        batch_parameters={"dataframe": df_employees}
    )

    suite = context.suites.add(gx.ExpectationSuite(name="employees_suite"))
    suite.add_expectation(gx.expectations.ExpectColumnValuesToNotBeNull(column="employee_id"))
    suite.add_expectation(gx.expectations.ExpectColumnValuesToBeUnique(column="employee_id"))
    suite.add_expectation(gx.expectations.ExpectColumnValuesToNotBeNull(column="gross_salary"))
    suite.add_expectation(gx.expectations.ExpectColumnValuesToBeBetween(column="gross_salary", min_value=0))
    suite.add_expectation(gx.expectations.ExpectColumnValuesToBeInSet(
        column="commute_mode",
        value_set=["walking_running", "cycling_scooter", "transit", "car"]
    ))
    suite.add_expectation(gx.expectations.ExpectTableRowCountToBeBetween(min_value=1, max_value=10000))

    result = batch.validate(suite)
    results_summary.append(("employees", result.success))
    status_employees = "success" if result.success else "error"
    log_pipeline(engine, "expectations_employees", status_employees,
                 f"employees : {'PASSED' if result.success else 'FAILED'}")
    logger.info(f"employees : {'✓ OK' if result.success else '✗ ÉCHEC'}")

    # ─── 2. TABLE ACTIVITIES ──────────────────────────────────────
    logger.info("Tests sur la table activities...")
    df_activities = pd.read_sql("SELECT * FROM activities", engine)
    ds2 = context.data_sources.add_pandas("activities_source")
    da2 = ds2.add_dataframe_asset("activities_asset")
    batch2 = da2.add_batch_definition_whole_dataframe("activities_batch").get_batch(
        batch_parameters={"dataframe": df_activities}
    )

    suite2 = context.suites.add(gx.ExpectationSuite(name="activities_suite"))
    suite2.add_expectation(gx.expectations.ExpectColumnValuesToNotBeNull(column="employee_id"))
    suite2.add_expectation(gx.expectations.ExpectColumnValuesToNotBeNull(column="start_date"))
    suite2.add_expectation(gx.expectations.ExpectColumnValuesToNotBeNull(column="sport_name"))
    suite2.add_expectation(gx.expectations.ExpectColumnValuesToBeBetween(
        column="distance_m", min_value=0, mostly=0.8
    ))
    suite2.add_expectation(gx.expectations.ExpectTableRowCountToBeBetween(min_value=100))

    result2 = batch2.validate(suite2)
    results_summary.append(("activities", result2.success))
    status_activities = "success" if result2.success else "error"
    log_pipeline(engine, "expectations_activities", status_activities,
                 f"activities : {'PASSED' if result2.success else 'FAILED'}")
    logger.info(f"activities : {'✓ OK' if result2.success else '✗ ÉCHEC'}")

    # ─── 3. TABLE COMMUTE_VALIDATION ──────────────────────────────
    logger.info("Tests sur la table commute_validation...")
    df_commute = pd.read_sql("SELECT * FROM commute_validation", engine)
    ds3 = context.data_sources.add_pandas("commute_source")
    da3 = ds3.add_dataframe_asset("commute_asset")
    batch3 = da3.add_batch_definition_whole_dataframe("commute_batch").get_batch(
        batch_parameters={"dataframe": df_commute}
    )

    suite3 = context.suites.add(gx.ExpectationSuite(name="commute_suite"))
    suite3.add_expectation(gx.expectations.ExpectColumnValuesToNotBeNull(column="employee_id"))
    suite3.add_expectation(gx.expectations.ExpectColumnValuesToBeBetween(
        column="distance_km", min_value=0
    ))
    suite3.add_expectation(gx.expectations.ExpectColumnValuesToBeInSet(
        column="commute_mode",
        value_set=["walking_running", "cycling_scooter"]
    ))

    result3 = batch3.validate(suite3)
    results_summary.append(("commute_validation", result3.success))
    status_commute = "success" if result3.success else "error"
    log_pipeline(engine, "expectations_commute", status_commute,
                 f"commute_validation : {'PASSED' if result3.success else 'FAILED'}")
    logger.info(f"commute_validation : {'✓ OK' if result3.success else '✗ ÉCHEC'}")

    # ─── RÉSUMÉ ───────────────────────────────────────────────────
    logger.info("─" * 40)
    all_passed = all(r[1] for r in results_summary)
    for table, success in results_summary:
        logger.info(f"  {table:25s} : {'✓ PASSED' if success else '✗ FAILED'}")
    logger.info("─" * 40)
    logger.info(f"Résultat global : {'✓ TOUS LES TESTS PASSÉS' if all_passed else '✗ DES TESTS ONT ÉCHOUÉ'}")

    # Log global dans pipeline_logs
    global_status = "success" if all_passed else "error"
    tables_passed = sum(1 for _, s in results_summary if s)
    log_pipeline(engine, "expectations_global", global_status,
                 f"{tables_passed}/{len(results_summary)} suites validées")

    return all_passed

if __name__ == "__main__":
    run_expectations()