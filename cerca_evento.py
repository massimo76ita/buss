from pymongo import MongoClient
from gridfs import GridFS
from datetime import datetime, timezone, timedelta
import os

# === Connessione al tuo MongoDB ===
uri = "mongodb+srv://massimoserafini1976:RxqRhjJrVl4wDGOv@rullo.evun5ie.mongodb.net/?retryWrites=true&w=majority&appName=rullo"
client = MongoClient(uri)
db = client["sismologia"]
fs = GridFS(db)

# === Configurazione ===
STAZIONE = "SACR"
DATA = "2025-07-23"
TIMEZONE_CEST = timezone(timedelta(hours=2))
start = datetime.fromisoformat(f"{DATA}T15:20:00").replace(tzinfo=TIMEZONE_CEST)
end = datetime.fromisoformat(f"{DATA}T15:40:00").replace(tzinfo=TIMEZONE_CEST)

# === Query: cerca solo file rullo PNG ===
query = {
    "station": STAZIONE,
    "timestamp_cest": {
        "$gte": start.isoformat(),
        "$lte": end.isoformat()
    },
    "filename": {"$regex": "^rullo_.*\\.png$"}
}

docs = list(db.tracciati.find(query).sort("timestamp_cest", 1))

# === Anteprima a video ===
if not docs:
    print("❌ Nessun rullo SACR trovato tra le 15:26 e le 15:32")
else:
    print(f"✅ Trovati {len(docs)} rulli SACR tra le 15:26 e le 15:32:\n")
    for i, doc in enumerate(docs, start=1):
        ts = datetime.fromisoformat(doc["timestamp_cest"]).strftime("%H:%M:%S")
        filename = doc.get("filename", "—")
        file_id = doc["file_id"]
        try:
            size = fs.get(file_id).length
            print(f"{i}. 🕒 {ts} — 📄 {filename} — 📦 {size} bytes")
        except Exception as e:
            print(f"{i}. 🕒 {ts} — 📄 {filename} — ⚠️ Errore: {e}")

    # === Salvataggio PNG ===
    os.makedirs("rulli_SACR_creta", exist_ok=True)
    for i, doc in enumerate(docs, start=1):
        try:
            file_id = doc["file_id"]
            img_data = fs.get(file_id).read()
            ts = datetime.fromisoformat(doc["timestamp_cest"]).strftime("%H-%M-%S")
            filename = f"rulli_SACR_creta/rullo_SACR_{ts}.png"
            with open(filename, "wb") as f:
                f.write(img_data)
            print(f"✅ Salvato: {filename}")
        except Exception as e:
            print(f"❌ Errore su rullo {i}: {e}")
