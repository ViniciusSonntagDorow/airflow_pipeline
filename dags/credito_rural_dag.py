from airflow.decorators import dag, task
from pendulum import datetime
import requests
import gzip
import shutil
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
import pandas as pd

load_dotenv()

DB_HOST = os.getenv('DB_HOST_PROD')
DB_PORT = os.getenv('DB_PORT_PROD')
DB_NAME = os.getenv('DB_NAME_PROD')
DB_USER = os.getenv('DB_USER_PROD')
DB_PASS = os.getenv('DB_PASS_PROD')
DB_SCHEMA = os.getenv('DB_SCHEMA_PROD')

DATABASE_URL = f'postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}'

engine = create_engine(DATABASE_URL)

@dag(
    start_date=datetime(2024, 1, 1),
    schedule="@daily",
    catchup=False,
    default_args={"owner": "Astro", "retries": 3},
    tags=["goiano analytics"],
)
def credito_rural_dag():
    # Define tasks
    @task()
    def download_data(*anos):
        for ano in anos:
            url = f"https://www.bcb.gov.br/htms/sicor/DadosBrutos/SICOR_CONTRATOS_MUNICIPIO_{ano}.gz"
            r = requests.get(url)
            path = f"C:/Users/vinic/OneDrive/Documentos/python/airflow_dbt_pipeline/include/{ano}.gz"
            with open(path, "wb") as f:
                f.write(r.content)
        return path[0:71]

    @task()
    def unzip(path):
        for file in os.listdir(path):
            if file.endswith(".gz"):
                zip_url = os.path.join(path, file)
                output_file = zip_url[:-3] + ".csv"
                with gzip.open(zip_url, 'rb') as f_in:
                    with open(output_file, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
    
    @task()
    def to_postgres(path):
        df_final = pd.DataFrame()
        for file in os.listdir(path):
            csv_url = os.path.join(path, file)
            if file.endswith(".csv"):
                df = pd.read_csv(csv_url, sep="|", encoding="iso-8859-2")
                df_final = pd.concat([df_final, df])
        df.to_sql('creditorural', engine, if_exists='replace', index=True)
    
    path = download_data(2024)

    unzip(path)

    to_postgres(path)


# Instantiate the DAG
credito_rural_dag()