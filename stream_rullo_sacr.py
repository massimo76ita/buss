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
STAZIONE = "SACR"
RETE = "IV"
CANALE = "HHZ"
SAMPLING_RATE = 100
FINESTRA_BUFFER = 300        # durata del tracciato salvato (5 minuti)
INTERVALLO_ACQUISIZIONE = 240  # quanto spesso salvare (ogni 4 min)
LATENZA_INGV_SEC = 800
TIMEZONE_CEST = pytz.timezone("Europe/Rome")

# === MongoDB
uri = "mongodb+srv://massimoserafini1976:RxqRhjJrVl4wDGOv@rullo.evun5ie.mongodb.net/?retryWrites=true&w=majority&appName=rullo"
client = MongoClient(uri)
db = client["rullo_sacr"]
fs = GridFS(db)

def acquisisci_buffer():
    try:
        end = UTCDateTime() - LATENZA_INGV_SEC
        start = end - FINESTRA_BUFFER
        tr = Client("INGV").get_waveforms(RETE, STAZIONE, "", CANALE, start, end)[0]
        tr.detrend("demean")
        tr.filter("bandpass", freqmin=0.5, freqmax=10.0)
        data = tr.data.astype(np.float64)
        data -= np.mean(data)

        start_utc = tr.stats.starttime.datetime.replace(tzinfo=timezone.utc)
        start_cest = start_utc.astimezone(TIMEZONE_CEST)
        end_utc = tr.stats.endtime.datetime.replace(tzinfo=timezone.utc)
        end_cest = end_utc.astimezone(TIMEZONE_CEST)
        ritardo = (datetime.now(TIMEZONE_CEST) - end_cest).total_seconds()

        print(f"[📈] Rullo {start_cest.strftime('%H:%M')}–{end_cest.strftime('%H:%M')} CEST (ritardo: {ritardo:.0f} sec)")

        return data, start_cest
    except Exception as e:
        print(f"❌ Errore acquisizione SACR: {e}")
        return None, None

def salva_rullo(buffer, start_time):
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
    print(f"✅ Rullo SACR salvato: {nome} — {len(buffer)} campioni")

# === Loop rolling ottimizzato
print(f"🎬 Rullo rolling SACR — ogni {INTERVALLO_ACQUISIZIONE}s — finestra: {FINESTRA_BUFFER}s\n")
while True:
    data, start = acquisisci_buffer()
    if data is not None:
        salva_rullo(data, start)
    time.sleep(INTERVALLO_ACQUISIZIONE)

