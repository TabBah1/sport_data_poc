-- ===========================================
-- SPORT DATA POC - Schéma de base de données
-- ===========================================

CREATE TABLE IF NOT EXISTS employees (
    employee_id     INTEGER PRIMARY KEY,
    last_name       VARCHAR(100),
    first_name      VARCHAR(100),
    birth_date      DATE,
    business_unit   VARCHAR(100),
    hire_date       DATE,
    gross_salary    NUMERIC(12, 2),
    contract_type   VARCHAR(20),
    leave_days      INTEGER,
    address         TEXT,
    commute_mode    VARCHAR(50)
);

COMMENT ON TABLE employees IS 'Table des salariés';
COMMENT ON COLUMN employees.employee_id IS 'Identifiant unique du salarié';
COMMENT ON COLUMN employees.last_name IS 'Nom de famille';
COMMENT ON COLUMN employees.first_name IS 'Prénom';
COMMENT ON COLUMN employees.birth_date IS 'Date de naissance';
COMMENT ON COLUMN employees.business_unit IS 'Département / BU';
COMMENT ON COLUMN employees.hire_date IS 'Date d embauche';
COMMENT ON COLUMN employees.gross_salary IS 'Salaire brut annuel en euros';
COMMENT ON COLUMN employees.contract_type IS 'Type de contrat (CDI, CDD...)';
COMMENT ON COLUMN employees.leave_days IS 'Nombre de jours de congés payés';
COMMENT ON COLUMN employees.address IS 'Adresse du domicile';
COMMENT ON COLUMN employees.commute_mode IS 'Moyen de déplacement : walking_running, cycling_scooter, transit, car';

CREATE TABLE IF NOT EXISTS sports (
    sport_id        SERIAL PRIMARY KEY,
    employee_id     INTEGER REFERENCES employees(employee_id),
    sport_name      VARCHAR(100)
);

COMMENT ON TABLE sports IS 'Sport déclaré par chaque salarié';
COMMENT ON COLUMN sports.sport_id IS 'Identifiant unique';
COMMENT ON COLUMN sports.employee_id IS 'Référence au salarié';
COMMENT ON COLUMN sports.sport_name IS 'Nom du sport pratiqué (NULL si aucun sport déclaré)';

CREATE TABLE IF NOT EXISTS activities (
    activity_id     SERIAL PRIMARY KEY,
    employee_id     INTEGER REFERENCES employees(employee_id),
    sport_name      VARCHAR(100),
    start_date      TIMESTAMP,
    end_date        TIMESTAMP,
    distance_m      INTEGER,
    comment         TEXT,
    created_at      TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE activities IS 'Historique des activités sportives simulées (type Strava)';
COMMENT ON COLUMN activities.activity_id IS 'Identifiant unique de l activité';
COMMENT ON COLUMN activities.employee_id IS 'Référence au salarié';
COMMENT ON COLUMN activities.sport_name IS 'Type d activité';
COMMENT ON COLUMN activities.start_date IS 'Date et heure de début';
COMMENT ON COLUMN activities.end_date IS 'Date et heure de fin';
COMMENT ON COLUMN activities.distance_m IS 'Distance en mètres (NULL si non pertinent ex: escalade)';
COMMENT ON COLUMN activities.comment IS 'Commentaire libre du salarié';
COMMENT ON COLUMN activities.created_at IS 'Date d insertion en base';

CREATE TABLE IF NOT EXISTS commute_validation (
    validation_id       SERIAL PRIMARY KEY,
    employee_id         INTEGER REFERENCES employees(employee_id),
    distance_km         NUMERIC(6, 2),
    commute_mode        VARCHAR(50),
    is_valid            BOOLEAN,
    rejection_reason    TEXT,
    checked_at          TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE commute_validation IS 'Résultats de validation des trajets domicile-travail via Google Maps';
COMMENT ON COLUMN commute_validation.validation_id IS 'Identifiant unique';
COMMENT ON COLUMN commute_validation.employee_id IS 'Référence au salarié';
COMMENT ON COLUMN commute_validation.distance_km IS 'Distance calculée par Google Maps en km';
COMMENT ON COLUMN commute_validation.commute_mode IS 'Mode de déplacement déclaré';
COMMENT ON COLUMN commute_validation.is_valid IS 'True si la déclaration est cohérente avec la distance';
COMMENT ON COLUMN commute_validation.rejection_reason IS 'Motif de rejet si is_valid = False';
COMMENT ON COLUMN commute_validation.checked_at IS 'Date de vérification';

CREATE TABLE IF NOT EXISTS advantages (
    advantage_id        SERIAL PRIMARY KEY,
    employee_id         INTEGER REFERENCES employees(employee_id),
    salary_bonus        NUMERIC(12, 2) DEFAULT 0,
    wellness_days       INTEGER DEFAULT 0,
    activity_count      INTEGER DEFAULT 0,
    computed_at         TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE advantages IS 'Avantages calculés pour chaque salarié';
COMMENT ON COLUMN advantages.advantage_id IS 'Identifiant unique';
COMMENT ON COLUMN advantages.employee_id IS 'Référence au salarié';
COMMENT ON COLUMN advantages.salary_bonus IS 'Prime sportive (5% du salaire brut si éligible)';
COMMENT ON COLUMN advantages.wellness_days IS 'Jours bien-être accordés (5 si >= 15 activités)';
COMMENT ON COLUMN advantages.activity_count IS 'Nombre d activités comptabilisées sur l année';
COMMENT ON COLUMN advantages.computed_at IS 'Date de calcul';

CREATE TABLE IF NOT EXISTS pipeline_logs (
    log_id      SERIAL PRIMARY KEY,
    step        VARCHAR(100),
    status      VARCHAR(20),
    message     TEXT,
    logged_at   TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE pipeline_logs IS 'Journal d exécution du pipeline';
COMMENT ON COLUMN pipeline_logs.log_id IS 'Identifiant unique';
COMMENT ON COLUMN pipeline_logs.step IS 'Nom de l étape du pipeline';
COMMENT ON COLUMN pipeline_logs.status IS 'Statut : success, error, warning';
COMMENT ON COLUMN pipeline_logs.message IS 'Message détaillé';
COMMENT ON COLUMN pipeline_logs.logged_at IS 'Date et heure du log';