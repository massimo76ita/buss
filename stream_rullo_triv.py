from obspy.clients.fdsn import Client
from obspy import UTCDateTime
from pymongo import MongoClient
from gridfs import GridFS
from datetime import datetime, timezone, timedelta
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pytz
import io
import time

# === Configurazione ===
STAZIONE = "TRIV"
RETE = "IV"
CANALE = "HHZ"
SAMPLING_RATE = 100
INTERVALLO_ACQUISIZIONE = 10
FINESTRA_BUFFER = 300
LATENZA_INGV_SEC = 800
TIMEZONE_CEST = pytz.timezone("Europe/Rome")

# === Connessione MongoDB
uri = "mongodb+srv://massimoserafini1976:RxqRhjJrVl4wDGOv@rullo.evun5ie.mongodb.net/?retryWrites=true&w=majority&appName=rullo"
client = MongoClient(uri)
db = client["rullo_triv"]
fs = GridFS(db)

# === Buffer dati
buffer_data = []
buffer_start = None

def acquisisci_tracciato():
    try:
        end = UTCDateTime() - LATENZA_INGV_SEC
        start = end - INTERVALLO_ACQUISIZIONE
        tr = Client("INGV").get_waveforms(RETE, STAZIONE, "", CANALE, start, end)[0]
        tr.detrend("demean")
        tr.filter("bandpass", freqmin=0.5, freqmax=10.0)
        data = tr.data.astype(np.float64)
        data -= np.mean(data)

        start_time_utc = tr.stats.starttime.datetime.replace(tzinfo=timezone.utc)
        start_time_cest = start_time_utc.astimezone(TIMEZONE_CEST)
        ora_attuale = datetime.now(TIMEZONE_CEST)
        ritardo = (ora_attuale - start_time_cest).total_seconds()
        if ritardo > 300:
            print(f"[⚠️] Rullo TRIV in ritardo di {ritardo:.0f} sec")

        return data, start_time_cest
    except Exception as e:
        print(f"❌ Errore acquisizione TRIV: {e}")
        return None, None

def salva_buffer(buffer, start_time):
    times = [start_time + timedelta(seconds=i / SAMPLING_RATE) for i in range(len(buffer))]
    std = np.std(buffer)
    ylim = std * 5

    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(times, buffer, color="black", linewidth=0.8)
    ax.set_ylim(-ylim, ylim)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S', tz=TIMEZONE_CEST))
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax.set_xlabel("Orario locale (CEST)")
    ax.set_ylabel("Ampiezza")
    ax.set_title(f"{STAZIONE} — Tracciato continuo — {start_time.strftime('%Y-%m-%d %H:%M:%S')} CEST")
    ax.grid(True)
    fig.autofmt_xdate()
    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120)
    buf.seek(0)
    plt.close(fig)

    nome = f"{STAZIONE}_rullo_{start_time.strftime('%Y-%m-%d_%H-%M-%S')}.png"
    file_id = fs.put(buf.read(), filename=nome)
    doc = {
        "station": STAZIONE,
        "channel": CANALE,
        "type": "rullo",
        "duration": len(buffer) / SAMPLING_RATE,
        "timestamp_cest": start_time.isoformat(),
        "day_key": start_time.strftime("%Y-%m-%d"),
        "filename": nome,
        "file_id": file_id
    }
    db.tracciati.insert_one(doc)
    print(f"✅ Rullo TRIV salvato: {nome} — {len(buffer)} campioni")

print(f"🎬 Avvio rullo continuo per {STAZIONE} — finestra: {FINESTRA_BUFFER}s\n")
while True:
    data, start = acquisisci_tracciato()
    if data is not None:
        if buffer_start is None:
            buffer_start = start
        buffer_data.extend(data)

        if len(buffer_data) >= FINESTRA_BUFFER * SAMPLING_RATE:
            salva_buffer(np.array(buffer_data), buffer_start)
            buffer_data = []
            buffer_start = None

    time.sleep(INTERVALLO_ACQUISIZIONE)

