import pandas as pd
import json
from pathlib import Path
import os
import re

# --------------------------------
# CONFIG
# --------------------------------
INPUT_CSV = "bronbestand touren familie(Klimtochten 00-25) (1).csv"
OUTPUT_BASE = Path("vacations")

# --------------------------------
# Load CSV with correct separator and encoding fallback
# --------------------------------
try:
    df = pd.read_csv(INPUT_CSV, sep=";", encoding="utf-8")
except UnicodeDecodeError:
    print("⚠ UTF-8 failed, loading with cp1252...")
    df = pd.read_csv(INPUT_CSV, sep=";", encoding="cp1252")

# Clean column names
df.columns = [re.sub(r"\s+", "_", c.strip()) for c in df.columns]

# Ensure Vakantie exists
if "Vakantie" not in df.columns:
    raise ValueError("❌ ERROR: CSV must contain a 'Vakantie' column (capital V).")


# --------------------------------
# Parse coords from 'locatie' column
# Expected format: "47.1234, 11.5678"
# --------------------------------
def parse_coords(value):
    if not isinstance(value, str):
        return None
    if "," not in value:
        return None

    parts = value.split(",")
    try:
        lat = float(parts[0].strip())
        lon = float(parts[1].strip())
        return [lat, lon]
    except:
        return None


# --------------------------------
# Convert CSV row → route dictionary
# --------------------------------
def row_to_dict(row):
    coords = parse_coords(row.get("Locatie"))
    return {
        "gebied": row.get("gebied"),
        "routenaam": row.get("routenaam"),
        "datum": row.get("datum"),
        "moeilijkheid": row.get("moeilijkheid"),
        "lengte": row.get("lengte"),
        "zeker": row.get("zeker"),
        "kenmerk": row.get("kenmerk"),
        "rots": row.get("rots"),
        "klimmers": {
            "max": row.get("Max"),
            "stijl_max": row.get("stijl_Max"),
            "sem": row.get("Sem"),
            "stijl_sem": row.get("stijl_Sem"),
            "paul": row.get("Paul"),
            "stijl_paul": row.get("stijl_Paul"),
            "trudy": row.get("Trudy"),
            "stijl_trudy": row.get("stijl_Trudy"),
        },
        "moeilijkheid_langere_route": row.get("moeilijkheid_langere_route"),
        "coords": coords
    }


# --------------------------------
# Group rows by Vakantie
# --------------------------------
vacations = {}

for _, row in df.iterrows():
    vac = str(row["Vakantie"]).strip()
    vacations.setdefault(vac, []).append(row_to_dict(row))


# --------------------------------
# For each vacation, group by gebied and lift coords to gebied-level
# --------------------------------
for vac, entries in vacations.items():

    result = {}

    for route in entries:
        gebied = route.get("gebied", "UNKNOWN")

        if gebied not in result:
            result[gebied] = {
                "coords": None,
                "routes": []
            }

        # Promote coords to gebied-level (first non-null wins)
        if route["coords"] and result[gebied]["coords"] is None:
            result[gebied]["coords"] = route["coords"]

        # Remove coords from route-level
        route_copy = route.copy()
        route_copy.pop("coords", None)

        result[gebied]["routes"].append(route_copy)

    # Create vacation folder
    safe_vac = re.sub(r"[^A-Za-z0-9_\-]+", "_", vac)
    folder = OUTPUT_BASE / safe_vac
    folder.mkdir(parents=True, exist_ok=True)

    # Save JSON
    output_file = folder / "climbing.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"✔ Created: {output_file}")

print("\nDone! All climbing.json files generated with gebied-level coords.")
