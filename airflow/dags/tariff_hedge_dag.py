"""
Airflow DAG: tariff-hedge-sim daily pipeline.

Schedule: daily + manual trigger.
Tasks:
  generate -> ingest_bronze -> dbt_run_silver -> simulate_risk
  -> dbt_run_gold -> dbt_test -> load_grafana -> generate_alerts
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator

PROJECT_DIR = "/opt/airflow/project"
DBT_DIR = f"{PROJECT_DIR}/dbt_project"

default_args = {
    "owner": "tariff-hedge-sim",
    "depends_on_past": False,
    "email_on_failure": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=2),
}

with DAG(
    dag_id="tariff_hedge_pipeline",
    default_args=default_args,
    description="FX + tariff risk simulation pipeline (medallion architecture)",
    schedule_interval="@daily",
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["tariff", "hedge", "fx", "risk"],
) as dag:

    generate = BashOperator(
        task_id="generate_invoices",
        bash_command=f"cd {PROJECT_DIR} && python -m src.generator",
    )

    ingest_bronze = BashOperator(
        task_id="ingest_bronze",
        bash_command=f"cd {PROJECT_DIR} && python -m src.ingest_bronze",
    )

    dbt_run_silver = BashOperator(
        task_id="dbt_run_silver",
        bash_command=(
            f"cd {DBT_DIR} && dbt run --select staging silver --profiles-dir ."
        ),
    )

    simulate_risk = BashOperator(
        task_id="simulate_risk",
        bash_command=f"cd {PROJECT_DIR} && python -m src.simulate_risk",
    )

    dbt_run_gold = BashOperator(
        task_id="dbt_run_gold",
        bash_command=(
            f"cd {DBT_DIR} && dbt run --select gold --profiles-dir ."
        ),
    )

    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command=(
            f"cd {DBT_DIR} && dbt test --profiles-dir ."
        ),
    )

    load_grafana = BashOperator(
        task_id="load_grafana",
        bash_command=f"cd {PROJECT_DIR} && python -m src.load_grafana",
    )

    alerts = BashOperator(
        task_id="generate_alerts",
        bash_command=f"cd {PROJECT_DIR} && python -m src.generate_alerts",
    )

    # Task dependencies
    generate >> ingest_bronze >> dbt_run_silver >> simulate_risk >> dbt_run_gold >> dbt_test >> load_grafana >> alerts
