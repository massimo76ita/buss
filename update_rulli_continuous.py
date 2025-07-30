#!/usr/bin/env python3
"""
Script per aggiornamento continuo dei file rullo
Aggiorna automaticamente i file HTML dei rulli per tutte le stazioni
"""

import os
import base64
import time
import logging
from datetime import datetime, timezone, timedelta
from pymongo import MongoClient
from gridfs import GridFS
import subprocess
import sys

# Configurazione logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('rulli_updater.log')
    ]
)
logger = logging.getLogger(__name__)

class RulliUpdater:
    def __init__(self):
        # Configurazione stazioni
        self.stations = {
            "TRIV": {
                "uri": "mongodb+srv://massimoserafini1976:RxqRhjJrVl4wDGOv@rullo.evun5ie.mongodb.net/?retryWrites=true&w=majority&appName=rullo",
                "db_name": "rullo_triv",
                "name": "Trivento (CB)",
                "color": "#ff4444"
            },
            "SACR": {
                "uri": "mongodb+srv://massimoserafini1976:RxqRhjJrVl4wDGOv@rullo.evun5ie.mongodb.net/?retryWrites=true&w=majority&appName=rullo",
                "db_name": "rullo_sacr", 
                "name": "S. Croce del Sannio (BN)",
                "color": "#44ff44"
            },
            "CIGN": {
                "uri": "mongodb+srv://massimoserafini1976:RxqRhjJrVl4wDGOv@rullo.evun5ie.mongodb.net/?retryWrites=true&w=majority&appName=rullo",
                "db_name": "rullo_cign",
                "name": "Sant'Elia a Pianisi (CB)",
                "color": "#4444ff"
            }
        }
        
        self.timezone_cest = timezone(timedelta(hours=2))
        self.max_rulli = 10
        self.last_update = {}
        
    def get_station_data(self, station_code):
        """Recupera i dati per una stazione specifica"""
        try:
            station_config = self.stations[station_code]
            client = MongoClient(station_config["uri"])
            db = client[station_config["db_name"]]
            fs = GridFS(db)
            
            now = datetime.now(self.timezone_cest)
            oggi = now.strftime("%Y-%m-%d")
            
            docs = list(
                db.tracciati.find({"day_key": oggi, "station": station_code, "type": "rullo"})
                .sort("timestamp_cest", -1)
                .limit(self.max_rulli)
            )[::-1]
            
            return docs, fs, station_config
            
        except Exception as e:
            logger.error(f"❌ Errore recupero dati {station_code}: {e}")
            return [], None, None
    
    def format_orario_ce(self, value):
        """Formatta l'orario in formato CEST"""
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
    
    def generate_rullo_html(self, station_code, docs, fs, station_config):
        """Genera il file HTML del rullo per una stazione"""
        try:
            totali = len(docs)
            ultima = docs[-1]["timestamp_cest"] if totali else None
            orario = self.format_orario_ce(ultima) if totali else "—"
            
            html_filename = f"rullo_{station_code}.html"
            
            with open(html_filename, "w") as f:
                f.write(f"""<!DOCTYPE html><html><head>
<meta charset="UTF-8">
<title>Rullo Continuo — {station_code}</title>
<meta http-equiv="refresh" content="30">
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
<h1 style='color:{station_config["color"]}'>📍 {station_code} — {station_config["name"]} — Rullo continuo HHZ</h1>
<div class="summary">🕒 Ultimo aggiornamento: {orario}<br>📊 Rulli visualizzati: {totali}</div>
<div class="gallery">""")

                for d in docs:
                    try:
                        img = fs.get(d["file_id"]).read()
                        b64 = base64.b64encode(img).decode()
                        label = self.format_orario_ce(d.get("timestamp_cest"))
                        durata = d.get("duration", "—")
                        f.write(f"""<div class="entry">
<img src="data:image/png;base64,{b64}">
<div class="timestamp">🕒 {label} — ⏱️ Durata: {durata:.1f} sec</div>
</div>""")
                    except Exception as e:
                        logger.warning(f"⚠️ Errore immagine {station_code}: {e}")

                f.write(f"</div><footer>Powered by Massimo & Nathan — Rullo {station_code} - Aggiornamento automatico</footer></body></html>")
            
            logger.info(f"📊 Rullo {station_code} aggiornato: {totali} tracciati, ultimo: {orario}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Errore generazione HTML {station_code}: {e}")
            return False
    
    def update_all_rulli(self):
        """Aggiorna tutti i file rullo"""
        logger.info("🔄 Aggiornamento rulli in corso...")
        
        for station_code in self.stations.keys():
            try:
                docs, fs, station_config = self.get_station_data(station_code)
                if docs and fs and station_config:
                    success = self.generate_rullo_html(station_code, docs, fs, station_config)
                    if success:
                        self.last_update[station_code] = datetime.now()
                
            except Exception as e:
                logger.error(f"❌ Errore aggiornamento {station_code}: {e}")
    
    def run_continuous_update(self, interval_seconds=60):
        """Esegue aggiornamento continuo dei rulli"""
        logger.info(f"🚀 Avvio aggiornamento continuo rulli (intervallo: {interval_seconds}s)")
        
        while True:
            try:
                self.update_all_rulli()
                time.sleep(interval_seconds)
                
            except KeyboardInterrupt:
                logger.info("⏹ Aggiornamento rulli interrotto manualmente")
                break
            except Exception as e:
                logger.error(f"⚠️ Errore nel ciclo di aggiornamento: {e}")
                time.sleep(interval_seconds)

def main():
    updater = RulliUpdater()
    updater.run_continuous_update(interval_seconds=60)  # Aggiorna ogni minuto

if __name__ == "__main__":
    main() 