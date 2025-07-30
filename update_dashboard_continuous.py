#!/usr/bin/env python3
"""
Script per aggiornamento continuo della dashboard
Esegue in background e aggiorna dashboard_data.json ogni 30 secondi
"""

import time
import json
import logging
from datetime import datetime, timezone
from pymongo import MongoClient
import os

# Configurazione logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('dashboard_updater.log')
    ]
)
logger = logging.getLogger(__name__)

class DashboardUpdater:
    def __init__(self):
        self.mongo_uri = "mongodb+srv://massimoserafini:QIs0axxmwPcEKS78@monitoring.auhw6a8.mongodb.net/?retryWrites=true&w=majority&appName=monitoring"
        self.client = MongoClient(self.mongo_uri)
        self.db = self.client["monitoring"]
        self.collection = self.db["seismic_monitoring"]
        self.dashboard_file = "dashboard_data.json"
        self.last_update_time = None
        
    def get_latest_triangulation(self):
        """Recupera l'ultima triangolazione dal database"""
        try:
            latest = self.collection.find_one(
                {"type": "triangulation_result"}, 
                sort=[("timestamp", -1)]
            )
            return latest
        except Exception as e:
            logger.error(f"❌ Errore recupero dati MongoDB: {e}")
            return None
    
    def update_dashboard_file(self, triangulation_data):
        """Aggiorna il file dashboard_data.json"""
        try:
            if not triangulation_data:
                logger.warning("⚠️ Nessun dato di triangolazione trovato")
                return False
                
            dashboard_data = {
                "timestamp": triangulation_data.get("timestamp"),
                "lat": triangulation_data["epicenter"]["latitude"],
                "lon": triangulation_data["epicenter"]["longitude"],
                "stations": triangulation_data.get("valid_stations", []),
                "time_diffs": triangulation_data.get("time_differences", {})
            }
            
            # Verifica se i dati sono cambiati
            current_data = {}
            if os.path.exists(self.dashboard_file):
                try:
                    with open(self.dashboard_file, "r") as f:
                        current_data = json.load(f)
                except:
                    pass
            
            # Aggiorna solo se i dati sono diversi
            if current_data.get("timestamp") != dashboard_data["timestamp"]:
                with open(self.dashboard_file, "w") as f:
                    json.dump(dashboard_data, f, indent=2)
                
                logger.info(f"📊 Dashboard aggiornata: {dashboard_data['lat']:.4f}, {dashboard_data['lon']:.4f}")
                self.last_update_time = datetime.now(timezone.utc)
                return True
            else:
                logger.debug("ℹ️ Nessun aggiornamento necessario")
                return False
                
        except Exception as e:
            logger.error(f"❌ Errore aggiornamento dashboard: {e}")
            return False
    
    def run_continuous_update(self, interval_seconds=30):
        """Esegue aggiornamento continuo della dashboard"""
        logger.info(f"🚀 Avvio aggiornamento continuo dashboard (intervallo: {interval_seconds}s)")
        
        while True:
            try:
                triangulation = self.get_latest_triangulation()
                updated = self.update_dashboard_file(triangulation)
                if not updated:
                    logger.info("[DEBUG] Nessun aggiornamento necessario in questo ciclo.")

                time.sleep(interval_seconds)
                
            except KeyboardInterrupt:
                logger.info("⏹ Aggiornamento dashboard interrotto manualmente")
                break
            except Exception as e:
                logger.error(f"⚠️ Errore nel ciclo di aggiornamento: {e}")
                time.sleep(interval_seconds)

def main():
    updater = DashboardUpdater()
    updater.run_continuous_update(interval_seconds=30)

if __name__ == "__main__":
    main() 