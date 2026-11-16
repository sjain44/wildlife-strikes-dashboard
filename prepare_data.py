"""Download and clean the FAA National Wildlife Strike Database.

Run `python prepare_data.py` to rebuild data/strikes_clean.parquet from scratch.
Each `# %% step` block below is also a cell in the narrative notebook.
"""
# %% step: setup
from pathlib import Path
import urllib.request
import zipfile

import numpy as np
import pandas as pd

DATA = Path(__file__).resolve().parent / "data" if "__file__" in globals() else Path("data")
RAW = DATA / "raw"
URL = "https://wildlife.faa.gov/assets/database_excel.zip"

# %% step: download
# Download the zip once. The FAA site's "Download Excel" button points at this file.
RAW.mkdir(parents=True, exist_ok=True)
zip_path = RAW / "database_excel.zip"
if not zip_path.exists():
    urllib.request.urlretrieve(URL, zip_path)
with zipfile.ZipFile(zip_path) as z:
    z.extractall(RAW)

# %% step: read
# calamine reads the 159 MB workbook in about 35 seconds (openpyxl takes minutes).
raw = pd.read_excel(RAW / "Public.xlsx", engine="calamine")
# Some text columns mix numbers and strings (AIRPORT_ID holds both 123 and "KDTW").
# Cast every object column to a clean, stripped string so parquet can store it.
text_cols = raw.select_dtypes(include=["object", "string"]).columns
raw[text_cols] = raw[text_cols].astype("string").apply(lambda s: s.str.strip())
raw.shape

# %% step: duplicates
# 8 strike IDs appear twice. The only column that differs is SPECIES ("Squirrels" vs
# "Tree squirrels"), so it is a lookup artifact. Keep the more specific name.
dups = raw[raw["INDEX_NR"].duplicated(keep=False)]
raw = raw[~(raw["INDEX_NR"].duplicated(keep=False) & raw["SPECIES"].eq("Squirrels"))]
assert raw["INDEX_NR"].is_unique

# %% step: select
# Keep the 20 columns the dashboard uses and give them readable names.
cols = {
    "INDEX_NR": "id", "INCIDENT_DATE": "date", "INCIDENT_YEAR": "year",
    "INCIDENT_MONTH": "month", "TIME_OF_DAY": "time_of_day", "AIRPORT_ID": "airport_id",
    "AIRPORT": "airport", "STATE": "state", "LATITUDE": "lat", "LONGITUDE": "lon",
    "OPERATOR": "operator", "AC_CLASS": "ac_class", "PHASE_OF_FLIGHT": "phase",
    "HEIGHT": "height_ft", "SPEED": "speed_kt", "DAMAGE_LEVEL": "damage_code",
    "SPECIES": "species", "SIZE": "size", "NUM_STRUCK": "num_struck",
    "INGESTED_OTHER": "ingested",
}
df = raw[list(cols)].rename(columns=cols)

# %% step: types
# Dates and coordinates arrive as text. Convert them, and flag 2026 as a partial year
# because the FAA had only validated reports through about August when I downloaded it.
df["date"] = pd.to_datetime(df["date"], errors="coerce")
df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
df["lon"] = pd.to_numeric(df["lon"], errors="coerce")
df["partial_year"] = df["year"].eq(df["year"].max())

# %% step: damage
# FAA damage codes: N none, M minor, M? uncertain minor, S substantial, D destroyed.
# A strike counts as damaging if any damage was reported. Blank means not reported.
damage_labels = {"N": "None", "M": "Minor", "M?": "Minor", "S": "Substantial", "D": "Destroyed"}
df["damage"] = df["damage_code"].map(damage_labels).fillna("Not reported")
df["damaging"] = df["damage"].isin(["Minor", "Substantial", "Destroyed"])

# %% step: phase
# Twelve phase-of-flight values collapse into four groups for the Sankey diagram.
phase_groups = {
    "Parked": "On the ground", "Taxi": "On the ground",
    "Take-off Run": "Take-off and climb", "Climb": "Take-off and climb",
    "Departure": "Take-off and climb",
    "En Route": "En route", "Local": "En route",
    "Descent": "Approach and landing", "Approach": "Approach and landing",
    "Arrival": "Approach and landing", "Landing Roll": "Approach and landing",
}
df["phase_group"] = df["phase"].map(phase_groups).fillna("Not reported")

# %% step: species
# 40% of reports name only "Unknown bird - small" and similar. They stay in the totals
# but are excluded from species comparisons, since they are not a real species.
df["unknown_species"] = df["species"].str.contains("unknown", case=False, na=True)
df["size"] = df["size"].fillna("Not reported")
df["time_of_day"] = df["time_of_day"].fillna("Not reported")

# %% step: height
# HEIGHT is feet above ground. 0 means the animal was hit on the runway, so airborne
# analysis uses height > 0 only. Half the reports leave height blank.
df["airborne"] = df["height_ft"].gt(0)

# %% step: save
for c in ["time_of_day", "state", "ac_class", "phase", "phase_group", "damage",
          "damage_code", "size", "num_struck", "species", "airport", "airport_id", "operator"]:
    df[c] = df[c].astype("category")
DATA.mkdir(exist_ok=True)
df.to_parquet(DATA / "strikes_clean.parquet", index=False)
df.shape
