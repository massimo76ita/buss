#!/usr/bin/env python3
"""
Estrae l'ultimo epicentro calcolato da MongoDB e aggiorna dashboard_data.json
mantenendo i valori precedenti se non c'è un nuovo evento.
"""

from pymongo import MongoClient
import json
import os

# === CONFIGURAZIONE ===
uri = "mongodb+srv://massimoserafini:QIs0axxmwPcEKS78@monitoring.auhw6a8.mongodb.net/?retryWrites=true&w=majority&appName=monitoring"
client = MongoClient(uri)
db = client["monitoring"]
collection = db["seismic_monitoring"]

DASHBOARD_FILE = "dashboard_data.json"

# Carica i dati precedenti se esistono
previous_data = {}
if os.path.exists(DASHBOARD_FILE):
    with open(DASHBOARD_FILE, "r") as f:
        try:
            previous_data = json.load(f)
        except json.JSONDecodeError:
            previous_data = {}

# Trova l'ultimo documento di tipo triangulation_result
last_triangulation = collection.find_one({"type": "triangulation_result"}, sort=[("timestamp", -1)])
print("DEBUG: Ultimo triangulation_result trovato:", last_triangulation)

if last_triangulation:
    new_timestamp = last_triangulation.get("timestamp")
    print("DEBUG: Nuovo timestamp trovato:", new_timestamp)

    # Verifica se è un nuovo evento
    if previous_data.get("timestamp") != new_timestamp:
        # Nuovo evento → aggiorna tutto
        data = {
            "timestamp": new_timestamp,
            "lat": last_triangulation["epicenter"]["latitude"],
            "lon": last_triangulation["epicenter"]["longitude"],
            "stations": last_triangulation.get("valid_stations", []),
            "time_diffs": last_triangulation.get("time_differences", {})
        }
        print("DEBUG: Scrivo nuovo dashboard_data.json:", data)
    else:
        # Nessun nuovo evento → mantieni i dati precedenti
        data = previous_data
        print("DEBUG: Nessun nuovo evento, mantengo i dati precedenti.")
else:
    data = previous_data if previous_data else {"error": "Nessun epicentro trovato"}
    print("DEBUG: Nessun triangulation_result trovato, scrivo errore.")

# Scrivi il file aggiornato
with open(DASHBOARD_FILE, "w") as f:
    json.dump(data, f, indent=2)

print("✅ dashboard_data.json aggiornato.")
