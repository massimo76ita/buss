import asyncio
from pymongo import MongoClient
from gridfs import GridFS
from telegram import Bot, InputFile
from datetime import datetime
import pytz

# === Telegram ===
BOT_TOKEN = "8032045656:AAFZ2FYaGiqh2xxdHVkre4EDpYSFcV-e6-o"
CHAT_ID = "180056339"

# === Soglie di invio automatico ===
SOGLIA_PEAK = 800
SOGLIA_DURATA = 3.0  # in secondi

# === Connessione MongoDB ===
uri = "mongodb+srv://massimo76:a5rFSpkB5vIHUoQa@clusterbusso.dbrl7bb.mongodb.net/?retryWrites=true&w=majority"
client = MongoClient(uri)
db = client["sismologia"]
fs = GridFS(db)

# === Funzione chiamabile da altri moduli ===
async def invia_se_sismico(doc):
    peak = doc.get("peak", 0)
    durata = doc.get("duration", 0.0)

    if peak < SOGLIA_PEAK or durata < SOGLIA_DURATA:
        print(f"🔕 Evento {doc['station']} non inviato — peak {peak}, durata {durata}s")
        return

    try:
        bot = Bot(token=BOT_TOKEN)
        timestamp = doc["timestamp_cest"].astimezone(pytz.timezone("Europe/Rome")).strftime("%Y-%m-%d %H:%M:%S")
        lat = doc.get("lat", "?")
        lon = doc.get("lon", "?")
        rms = doc.get("rms", "?")
        file_id = doc["file_id"]
        filename = doc["filename"]
        file_data = InputFile(fs.get(file_id).read(), filename=filename)

        caption = (
            f"📍 *{doc['station']} — Evento sismico rilevato*\n"
            f"🕒 {timestamp}\n"
            f"📊 Peak: `{peak}` — RMS: `{rms}`\n"
            f"⏱️ Durata: `{durata:.2f}` sec\n"
            f"🌍 Lat: `{lat}` — Lon: `{lon}`"
        )

        await bot.send_photo(
            chat_id=CHAT_ID,
            photo=file_data,
            caption=caption,
            parse_mode="Markdown"
        )

        print(f"✅ PNG inviato da {doc['station']}: {filename}")
    except Exception as e:
        print(f"❌ Errore Telegram ({doc['station']}): {e}")

# === Esecuzione autonoma per test o cronjob
async def main():
    oggi = datetime.now(pytz.timezone("Europe/Rome")).strftime("%Y-%m-%d")
    for stazione in ["TRIV", "SACR", "CIGN"]:
        doc = db.tracciati.find_one(
            {"station": stazione, "day_key": oggi},
            sort=[("timestamp_cest", -1)]
        )
        if doc:
            await invia_se_sismico(doc)

if __name__ == "__main__":
    asyncio.run(main())
