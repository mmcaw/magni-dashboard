import streamlit as st
from google.oauth2 import service_account
from google.cloud import bigquery
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# Create API client.
credentials = service_account.Credentials.from_service_account_info(
    st.secrets["gcp_service_account"]
)
client = bigquery.Client(credentials=credentials)

# Perform query.
# Uses st.cache_data to only rerun when the query changes or after 10 min.
@st.cache_data(ttl=600)
def run_query(query):
    query_job = client.query(query)
    rows_raw = query_job.result()
    # Convert to list of dicts. Required for st.cache_data to hash the return value.
    rows = [dict(row) for row in rows_raw]
    return rows


### Status Board ###

query = \
"""
SELECT System,
       CASE 
           WHEN EXISTS (
               SELECT 1
               FROM `qc-database-365211.System_References.abc` as sub
               WHERE sub.System = main.System AND sub.Date = CURRENT_DATE()
           ) THEN '🟢' 
           ELSE '🔴'
       END as Record_Exists_Today
FROM `qc-database-365211.System_References.abc` as main
GROUP BY System
"""

df_captured_today = pd.read_gbq(query, credentials=credentials)
st.dataframe(df_captured_today)



### Dropdowns ###

col1, col2, _ = st.columns(3)

query_dropdown = "SELECT DISTINCT(System) FROM `qc-database-365211.System_References.abc`"
system_options = pd.read_gbq(query_dropdown, credentials=credentials)
system_options = system_options["System"].tolist()
with col1: 
    system = st.selectbox(
        'Select a System',
        system_options)

with col2:
    channel = st.selectbox(
        'Select a Channel',
        [1, 2])

# query_dropdown = "SELECT DISTINCT(Date) FROM `qc-database-365211.System_References.abc`"
# spectra_options = pd.read_gbq(query_dropdown, credentials=credentials)
# spectra_options = spectra_options["Date"].tolist()
# date = st.selectbox(
#     'Select a Date',
#     spectra_options)

col1, col2, _ = st.columns(3)

one_week_ago = datetime.now() - timedelta(weeks=1)

with col1:
    date_start = st.date_input(
            "Date From", one_week_ago)

with col2:
    date_end = st.date_input(
            "Date To")


query = f"SELECT *, DENSE_RANK() OVER (ORDER BY Spectra_UUID) as Measurement, CONCAT(FORMAT_DATE('%Y-%m-%d', Date), '-', CAST(DENSE_RANK() OVER (ORDER BY Spectra_UUID) AS STRING)) as Date_Measurement FROM `qc-database-365211.System_References.abc` WHERE Date between '{date_start}' and '{date_end}' AND Channel={channel} AND System='{system}'"


df = pd.read_gbq(query, credentials=credentials)

df["Wavelengths"] = df["Spectra"].apply(lambda x: x[0]["Wavelengths"])
df["Counts"] = df["Spectra"].apply(lambda x: x[0]["Counts"])

df = df.explode(["Wavelengths", "Counts"])




## DOWNLOADING
@st.cache_data()
def convert_df(df):
    # IMPORTANT: Cache the conversion to prevent computation on every rerun
    df_export = df.copy()
    df_export = df_export.pivot_table(["Counts"],["Wavelengths"], ["System","Date","Channel"])
    return df_export.to_csv().encode('utf-8')

st.download_button(
    label="Download data as CSV",
    data=convert_df(df),
    file_name='reference_spectra.csv',
    mime='text/csv',
)


fig = px.line(df, x="Wavelengths", y="Counts", color="Date_Measurement")
st.plotly_chart(fig, theme="streamlit")

## Maximum value with time
df_max_counts = df.groupby(["Date","Spectra_UUID","Measurement"])["Counts"].max().reset_index()
fig = px.line(df_max_counts, x="Date", y="Counts")
st.plotly_chart(fig, theme="streamlit")

# st.line_chart(df, x="Wavelengths", y="Counts")


