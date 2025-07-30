from obspy.clients.fdsn import Client
from obspy import UTCDateTime
from pymongo import MongoClient
from gridfs import GridFS
from datetime import datetime, timezone, timedelta
from telegram import Bot, InputFile
from io import BytesIO
import matplotlib.pyplot as plt
import numpy as np
import pytz
import asyncio

# === Configurazione ===
STAZIONE = "TRIV"
RETE = "IV"
CANALE = "HHZ"
OFFSET = 80
DURATA = 30
SOGLIA_PEAK = 800
SOGLIA_DURATA = 3.0
SOGLIA_RMS_PEAK_RATIO = 0.95

# === Telegram ===
BOT_TOKEN = "8032045656:AAFZ2FYaGiqh2xxdHVkre4EDpYSFcV-e6-o"
CHAT_ID = "180056339"

# === MongoDB ===
uri = "mongodb+srv://massimo76:a5rFSpkB5vIHUoQa@clusterbusso.dbrl7bb.mongodb.net/?retryWrites=true&w=majority"
client = MongoClient(uri)
db = client["sismologia"]
fs = GridFS(db)

async def main():
    try:
        # Acquisizione tracciato
        end = UTCDateTime()
        start = end - OFFSET
        tr = Client("INGV").get_waveforms(RETE, STAZIONE, "", CANALE, start, start + DURATA)[0]

        # === Filtro bandpass ===
        tr.detrend("demean")
        tr.filter("bandpass", freqmin=0.5, freqmax=10.0)

        data = tr.data.astype(np.float64)
        sr = tr.stats.sampling_rate
        duration = len(data) / sr

        data -= np.mean(data)

        # === Analisi ===
        peak = float(np.max(np.abs(data)))
        rms = float(np.sqrt(np.mean(data**2)))

        cest = datetime.now(pytz.timezone("Europe/Rome"))
        giorno = cest.strftime("%Y-%m-%d")
        nome = f"{STAZIONE}_trace_{giorno}_{cest.strftime('%H-%M-%S.%f')}Z.png"

        std = np.std(data)
        ylim = std * 5

        # === Asse X in orario reale
        times = [cest.replace(microsecond=0) + timedelta(seconds=i / sr) for i in range(len(data))]

        buf = BytesIO()
        plt.figure(figsize=(10, 3))
        plt.plot(times, data, color="black", linewidth=0.8)
        plt.ylim(-ylim, ylim)
        plt.title(f"{STAZIONE} {CANALE} — {giorno} {cest.strftime('%H:%M:%S')} CEST — Peak={peak:.0f} RMS={rms:.0f}")
        plt.xlabel("Orario (HH:MM:SS)")
        plt.gcf().autofmt_xdate()
        plt.tight_layout()
        plt.savefig(buf, format="png", dpi=120)
        plt.close()
        buf.seek(0)

        # === Salvataggio MongoDB ===
        file_id = fs.put(buf, filename=nome)
        doc = {
            "station": STAZIONE,
            "channel": CANALE,
            "peak": peak,
            "rms": rms,
            "duration": duration,
            "timestamp_utc": datetime.now(timezone.utc),
            "timestamp_cest": cest.isoformat(),
            "day_key": giorno,
            "filename": nome,
            "file_id": file_id
        }
        db.tracciati.insert_one(doc)
        print(f"[✓] Evento salvato: {STAZIONE} — Peak={peak:.2f} — RMS={rms:.2f} — Durata={duration:.2f}s")

        # === Log dettagliato del filtraggio ===
        print(f"\n🔍 [FILTRI] Analisi evento {STAZIONE}:")
        print(f"   - Peak: {peak:.2f} (soglia: {SOGLIA_PEAK}) → {'✅' if peak >= SOGLIA_PEAK else '❌'}")
        print(f"   - Durata: {duration:.2f}s (soglia: {SOGLIA_DURATA}s) → {'✅' if duration >= SOGLIA_DURATA else '❌'}")
        rms_ratio = rms / peak if peak > 0 else float('inf')
        print(f"   - RMS/Peak: {rms_ratio:.3f} (soglia: <{SOGLIA_RMS_PEAK_RATIO}) → {'✅' if rms_ratio < SOGLIA_RMS_PEAK_RATIO else '❌'}")
        
        # === Invio Telegram ===
        if peak >= SOGLIA_PEAK and duration >= SOGLIA_DURATA and rms_ratio < SOGLIA_RMS_PEAK_RATIO:
            try:
                bot = Bot(token=BOT_TOKEN)
                file_data = InputFile(fs.get(file_id).read(), filename=nome)
                caption = (
                    f"📍 *{STAZIONE} — Evento sismico rilevato*\n"
                    f"🕒 {giorno} {cest.strftime('%H:%M:%S')} CEST\n"
                    f"📊 Peak: `{peak:.0f}` — RMS: `{rms:.0f}`\n"
                    f"⏱️ Durata: `{duration:.2f}` sec"
                )
                await bot.send_photo(chat_id=CHAT_ID, photo=file_data, caption=caption, parse_mode="Markdown")
                print("✅ PNG inviato su Telegram")
            except Exception as e:
                print(f"❌ Errore nell'invio a Telegram: {e}")
        else:
            print("🔕 Evento scartato — non supera i filtri")

    except Exception as e:
        print(f"❌ Errore TRIV: {e}")

# === Avvio asincrono ===
if __name__ == "__main__":
    asyncio.run(main())
