FROM apache/airflow:2.8.1-python3.11

USER root

# System deps for DuckDB
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ && \
    rm -rf /var/lib/apt/lists/*

USER airflow

# Python deps
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Copy project into container
COPY --chown=airflow:root . /opt/airflow/project/

# Copy DAGs into Airflow DAGs folder
COPY --chown=airflow:root airflow/dags/ /opt/airflow/dags/

# dbt profiles available in project dir
ENV DBT_PROFILES_DIR=/opt/airflow/project/dbt_project
ENV DBT_DUCKDB_PATH=/opt/airflow/project/data/warehouse.duckdb

WORKDIR /opt/airflow/project
