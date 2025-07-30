import io
import matplotlib.pyplot as plt
from pymongo import MongoClient
from bson import Binary
from datetime import datetime

MONGO_URI = "mongodb+srv://massimo76:a5rFSpkB5vIHUoQa@clusterbusso.dbrl7bb.mongodb.net/?retryWrites=true&w=majority&appName=ClusterBusso"
DB_NAME = "busso"
COLL_NAME = "eventi_sismici"

def salva_evento(stazione, peak, rms, fig=None):
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    coll = db[COLL_NAME]

    timestamp = datetime.utcnow()
    png_data = None

    if fig:
        buf = io.BytesIO()
        fig.savefig(buf, format='png')
        png_data = Binary(buf.getvalue())
        plt.close(fig)

    evento = {
        "station": stazione,
        "timestamp": timestamp,
        "peak": float(peak),
        "rms": float(rms),
        "image": png_data
    }

    coll.insert_one(evento)
    print(f"[✓] Evento salvato su DB: {stazione} {timestamp}")
