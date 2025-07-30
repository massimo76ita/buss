from pymongo import MongoClient
from gridfs import GridFS
from datetime import datetime, timezone, timedelta
import os

# === Connessione al nuovo MongoDB ===
uri = "mongodb+srv://massimoserafini1976:RxqRhjJrVl4wDGOv@rullo.evun5ie.mongodb.net/?retryWrites=true&w=majority&appName=rullo"
client = MongoClient(uri)
db = client["sismologia"]
fs = GridFS(db)

# === Configurazione ===
STAZIONE = "SACR"
DATA = "2025-07-23"
TIMEZONE_CEST = timezone(timedelta(hours=2))
start = datetime.fromisoformat(f"{DATA}T15:26:00").replace(tzinfo=TIMEZONE_CEST)
end = datetime.fromisoformat(f"{DATA}T15:32:00").replace(tzinfo=TIMEZONE_CEST)

# === Query ===
query = {
    "station": STAZIONE,
    "timestamp_cest": {
        "$gte": start.isoformat(),
        "$lte": end.isoformat()
    },
    "filename": {"$regex": "rullo_"}
}

docs = list(db.tracciati.find(query).sort("timestamp_cest", 1))

# === Cartella di output ===
os.makedirs("rulli_creta_SACR", exist_ok=True)

# === Estrazione PNG ===
for i, doc in enumerate(docs, start=1):
    try:
        file_id = doc["file_id"]
        img_data = fs.get(file_id).read()
        ts = datetime.fromisoformat(doc["timestamp_cest"]).strftime("%H-%M-%S")
        filename = f"rulli_creta_SACR/rullo_SACR_{ts}.png"
        with open(filename, "wb") as f:
            f.write(img_data)
        print(f"✅ PNG salvato: {filename}")
    except Exception as e:
        print(f"❌ Errore su rullo {i}: {e}")
