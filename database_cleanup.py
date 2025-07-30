#!/usr/bin/env python3
"""
Script di pulizia automatica database - eseguito ogni giorno alle 00:30
"""

from pymongo import MongoClient
from datetime import datetime, timedelta
import schedule
import time
import logging

# Configurazione logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('database_cleanup.log'),
        logging.StreamHandler()
    ]
)

# Connessioni MongoDB
uri_rullo = "mongodb+srv://massimoserafini1976:RxqRhjJrVl4wDGOv@rullo.evun5ie.mongodb.net/?retryWrites=true&w=majority&appName=rullo"
client_rullo = MongoClient(uri_rullo)

uri_monitoring = "mongodb+srv://massimoserafini:QIs0axxmwPcEKS78@monitoring.auhw6a8.mongodb.net/?retryWrites=true&w=majority&appName=monitoring"
client_monitoring = MongoClient(uri_monitoring)

def pulisci_database_rullo():
    """Pulisce il database rullo esistente"""
    logging.info("🧹 Inizio pulizia database rullo...")
    
    # Mantieni solo gli ultimi 7 giorni
    cutoff_date = datetime.now() - timedelta(days=7)
    
    for db_name in ["rullo_triv", "rullo_sacr", "rullo_cign"]:
        try:
            db = client_rullo[db_name]
            fs = db.fs
            
            # Trova file vecchi
            old_files = list(db.tracciati.find({
                "timestamp_cest": {"$lt": cutoff_date.isoformat()}
            }))
            
            logging.info(f"  {db_name}: {len(old_files)} file vecchi trovati")
            
            # Elimina file vecchi
            deleted_count = 0
            for file_doc in old_files:
                try:
                    # Elimina da GridFS
                    fs.delete(file_doc["file_id"])
                    # Elimina documento
                    db.tracciati.delete_one({"_id": file_doc["_id"]})
                    deleted_count += 1
                except Exception as e:
                    logging.error(f"    Errore eliminazione file: {e}")
            
            logging.info(f"  ✅ {db_name}: {deleted_count} file eliminati")
            
        except Exception as e:
            logging.error(f"  ❌ Errore pulizia {db_name}: {e}")

def pulisci_database_monitoring():
    """Pulisce il database monitoring"""
    logging.info("🧹 Inizio pulizia database monitoring...")
    
    try:
        # Database monitoring con collection seismic_monitoring
        db_monitoring = client_monitoring["monitoring"]
        collection_seismic = db_monitoring["seismic_monitoring"]
        
        # Mantieni solo gli ultimi 3 giorni per i dati grezzi
        cutoff_data = datetime.now() - timedelta(days=3)
        
        # Pulisci seismic_data nella collection seismic_monitoring
        old_data = list(collection_seismic.find({
            "timestamp": {"$lt": cutoff_data.isoformat()}
        }))
        
        logging.info(f"  seismic_monitoring: {len(old_data)} record vecchi")
        
        deleted_count = 0
        for data_doc in old_data:
            try:
                # Elimina da GridFS se presente
                if "file_id" in data_doc:
                    db_monitoring.fs.delete(data_doc["file_id"])
                # Elimina documento
                collection_seismic.delete_one({"_id": data_doc["_id"]})
                deleted_count += 1
            except Exception as e:
                logging.error(f"    Errore eliminazione: {e}")
        
        logging.info(f"  ✅ seismic_monitoring: {deleted_count} record eliminati")
        
        # Mantieni solo gli ultimi 7 giorni per i risultati
        cutoff_results = datetime.now() - timedelta(days=7)
        
        # Pulisci detection_results
        result = collection_seismic.delete_many({
            "type": "detection_result",
            "timestamp": {"$lt": cutoff_results.isoformat()}
        })
        logging.info(f"  ✅ detection_results: {result.deleted_count} record eliminati")
        
        # Pulisci triangulation_results
        result = collection_seismic.delete_many({
            "type": "triangulation_result",
            "timestamp": {"$lt": cutoff_results.isoformat()}
        })
        logging.info(f"  ✅ triangulation_results: {result.deleted_count} record eliminati")
        
    except Exception as e:
        logging.error(f"  ❌ Errore pulizia monitoring: {e}")

def pulisci_database_seismic_monitoring():
    """Pulisce il database seismic_monitoring separato"""
    logging.info("🧹 Inizio pulizia database seismic_monitoring...")
    
    try:
        # Database seismic_monitoring separato
        db_seismic = client_monitoring["seismic_monitoring"]
        
        # Mantieni solo gli ultimi 7 giorni
        cutoff_date = datetime.now() - timedelta(days=7)
        
        # Pulisci test_collection
        if "test_collection" in db_seismic.list_collection_names():
            result = db_seismic.test_collection.delete_many({
                "timestamp": {"$lt": cutoff_date.isoformat()}
            })
            logging.info(f"  ✅ test_collection: {result.deleted_count} record eliminati")
        
        # Pulisci altre collections se presenti
        for collection_name in db_seismic.list_collection_names():
            if collection_name != "test_collection":
                result = db_seismic[collection_name].delete_many({
                    "timestamp": {"$lt": cutoff_date.isoformat()}
                })
                logging.info(f"  ✅ {collection_name}: {result.deleted_count} record eliminati")
        
    except Exception as e:
        logging.error(f"  ❌ Errore pulizia seismic_monitoring: {e}")

def mostra_statistiche():
    """Mostra statistiche dei database"""
    logging.info("📊 STATISTICHE DATABASE:")
    
    # Database rullo
    for db_name in ["rullo_triv", "rullo_sacr", "rullo_cign"]:
        try:
            db = client_rullo[db_name]
            count = db.tracciati.count_documents({})
            logging.info(f"  {db_name}: {count} documenti")
        except Exception as e:
            logging.error(f"  {db_name}: errore - {e}")
    
    # Database monitoring
    try:
        db_monitoring = client_monitoring["monitoring"]
        collection_seismic = db_monitoring["seismic_monitoring"]
        seismic_count = collection_seismic.count_documents({})
        logging.info(f"  monitoring.seismic_monitoring: {seismic_count} documenti")
    except Exception as e:
        logging.error(f"  monitoring.seismic_monitoring: errore - {e}")
    
    # Database seismic_monitoring
    try:
        db_seismic = client_monitoring["seismic_monitoring"]
        for collection_name in db_seismic.list_collection_names():
            count = db_seismic[collection_name].count_documents({})
            logging.info(f"  seismic_monitoring.{collection_name}: {count} documenti")
    except Exception as e:
        logging.error(f"  seismic_monitoring: errore - {e}")

def pulizia_completa():
    """Esegue la pulizia completa dei database"""
    logging.info("🚀 AVVIO PULIZIA AUTOMATICA DATABASE")
    logging.info("=" * 50)
    
    # Mostra statistiche prima della pulizia
    mostra_statistiche()
    
    # Pulisci tutti i database
    pulisci_database_rullo()
    pulisci_database_monitoring()
    pulisci_database_seismic_monitoring()
    
    # Mostra statistiche dopo la pulizia
    logging.info("📊 STATISTICHE DOPO PULIZIA:")
    mostra_statistiche()
    
    logging.info("✅ Pulizia automatica completata!")

def main():
    """Funzione principale con scheduling"""
    logging.info("🔄 Sistema di pulizia automatica avviato")
    logging.info("⏰ Pulizia programmata ogni giorno alle 00:30")
    
    # Programma la pulizia alle 00:30 ogni giorno
    schedule.every().day.at("00:30").do(pulizia_completa)
    
    # Esegui una pulizia immediata se è la prima volta
    logging.info("🚀 Esecuzione pulizia iniziale...")
    pulizia_completa()
    
    # Loop infinito per mantenere il processo attivo
    while True:
        schedule.run_pending()
        time.sleep(60)  # Controlla ogni minuto

if __name__ == "__main__":
    main()