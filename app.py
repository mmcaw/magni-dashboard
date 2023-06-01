import streamlit as st
from google.oauth2 import service_account
from google.cloud import bigquery
import pandas as pd

# Create API client.
credentials = service_account.Credentials.from_service_account_info(
    st.secrets["gcp_service_account"]
)
client = bigquery.Client(credentials=credentials)

# Perform query.
# Uses st.cache_data to only rerun when the query changes or after 10 min.
# @st.cache_data(ttl=600)
def run_query(query):
    query_job = client.query(query)
    rows_raw = query_job.result()
    # Convert to list of dicts. Required for st.cache_data to hash the return value.
    rows = [dict(row) for row in rows_raw]
    return rows


query_dropdown = "SELECT DISTINCT(UUID) FROM `qc-database-365211.Chip_QA.QA_Spectra_Table` LIMIT 10"

spectra_options = pd.read_gbq(query_dropdown, credentials=credentials)
spectra_options = spectra_options["UUID"].tolist()

option = st.selectbox(
    'Select a UUID',
    spectra_options)


query = f"SELECT * FROM `qc-database-365211.Chip_QA.QA_Spectra_Table` WHERE UUID='{option}'"

df = pd.read_gbq(query, credentials=credentials)

st.line_chart(df, x="Wavelength", y="Counts")


