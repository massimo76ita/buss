import os, base64
from pymongo import MongoClient
from gridfs import GridFS
from datetime import datetime, timezone, timedelta

# === Connessione al cluster RULLO ===
uri = "mongodb+srv://massimoserafini1976:RxqRhjJrVl4wDGOv@rullo.evun5ie.mongodb.net/?retryWrites=true&w=majority&appName=rullo"
client = MongoClient(uri)
db = client["rullo_triv"]
fs = GridFS(db)

# === Configurazione stazione ===
STAZIONE = "TRIV"
NOME_COMPLETO = "Trivento (CB)"
COLORE = "#ff4444"
CANALIZZAZIONE = "HHZ"
HTML_FILENAME = "rullo_TRIV.html"
MAX_RULLI = 10

# === Tempo e filtro ===
TIMEZONE_CEST = timezone(timedelta(hours=2))
now = datetime.now(TIMEZONE_CEST)
oggi = now.strftime("%Y-%m-%d")

docs = list(
    db.tracciati.find({"day_key": oggi, "station": STAZIONE, "type": "rullo"})
    .sort("timestamp_cest", -1)
    .limit(MAX_RULLI)
)[::-1]

totali = len(docs)
ultima = docs[-1]["timestamp_cest"] if totali else None

def format_orario_ce(value):
    if isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value)
        except ValueError:
            return "—"
    elif isinstance(value, datetime):
        dt = value
    else:
        return "—"
    return dt.strftime("%H:%M:%S CEST")

orario = format_orario_ce(ultima) if totali else "—"

# === Scrittura HTML ===
with open(HTML_FILENAME, "w") as f:
    f.write(f"""<!DOCTYPE html><html><head>
<meta charset="UTF-8">
<title>Rullo Continuo — {STAZIONE}</title>
<meta http-equiv="refresh" content="120">
<style>
body {{ background:#121212; color:#eee; font-family:sans-serif; padding:10px }}
h1, .summary {{ text-align:center }}
.gallery {{
  display:grid;
  grid-template-columns:repeat(auto-fit,minmax(600px,1fr));
  gap:20px; max-width:1400px; margin:auto
}}
.entry {{
  background:#1e1e1e; border:1px solid #444; padding:6px;
  border-radius:6px
}}
.entry img {{
  width:100%; background:#fff; border-radius:4px
}}
.timestamp {{
  font-size:13px; text-align:center; margin-top:6px;
  color:#ccc; font-family:monospace
}}
footer {{
  margin-top:40px; font-size:12px;
  text-align:center; color:#888
}}
</style></head><body>
<h1 style='color:{COLORE}'>📍 {STAZIONE} — {NOME_COMPLETO} — Rullo continuo {CANALIZZAZIONE}</h1>
<div class="summary">🕒 Ultimo aggiornamento: {orario}<br>📊 Rulli visualizzati: {totali}</div>
<div class="gallery">""")

    for d in docs:
        try:
            img = fs.get(d["file_id"]).read()
            b64 = base64.b64encode(img).decode()
            label = format_orario_ce(d.get("timestamp_cest"))
            durata = d.get("duration", "—")
            f.write(f"""<div class="entry">
<img src="data:image/png;base64,{b64}">
<div class="timestamp">🕒 {label} — ⏱️ Durata: {durata:.1f} sec</div>
</div>""")
        except Exception as e:
            print(f"⚠️ Errore su {d.get('filename', '??')}: {e}")

    f.write(f"</div><footer>Powered by Massimo & Nathan — Rullo TRIV</footer></body></html>")
print(f"[✓] Pagina rullo aggiornata: {HTML_FILENAME}")

