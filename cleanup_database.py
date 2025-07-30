from pymongo import MongoClient
from datetime import datetime, timedelta
import gridfs
import sys

def cleanup_database():
    # Connessione a MongoDB
    mongo_uri = "mongodb+srv://massimoserafini:QIs0axxmwPcEKS78@monitoring.auhw6a8.mongodb.net/?retryWrites=true&w=majority&appName=monitoring"
    
    try:
        print("🔍 Connessione al database...")
        client = MongoClient(mongo_uri)
        db = client['seismic_monitoring']
        
        # Inizializza GridFS
        fs = gridfs.GridFS(db)
        
        # Conta i documenti prima della pulizia
        total_files = db.fs.files.count_documents({})
        total_metadata = db.seismic_data.count_documents({})
        
        print(f"📊 Stato attuale del database:")
        print(f"- File binari (GridFS): {total_files}")
        print(f"- Metadati: {total_metadata}")
        
        # Chiedi conferma all'utente
        confirm = input("\n⚠️  Sei sicuro di voler cancellare TUTTI i dati? (sì/NO): ")
        if confirm.lower() not in ['s', 'si', 'sì', 'sí', 'yes', 'y']:
            print("❌ Operazione annullata")
            return
        
        # Elimina TUTTI i file GridFS
        print("\n🗑️  Eliminazione file binari...")
        result_files = db.fs.files.delete_many({})
        result_chunks = db.fs.chunks.delete_many({})
        print(f"✅ Eliminati {result_files.deleted_count} file binari")
        
        # Elimina TUTTI i metadati
        print("🗑️  Eliminazione metadati...")
        result_metadata = db.seismic_data.delete_many({})
        print(f"✅ Eliminati {result_metadata.deleted_count} documenti di metadati")
        
        # Crea un indice per migliorare le prestazioni
        print("\n🔄 Creazione indici per ottimizzare le prestazioni...")
        db.seismic_data.create_index("timestamp")
        db.seismic_data.create_index("station")
        db.seismic_data.create_index([("type", 1), ("timestamp", -1)])
        
        print("\n✨ Pulizia completata con successo!")
        print("Il database è ora vuoto e pronto per l'uso.")
        
    except Exception as e:
        print(f"\n❌ Errore durante la pulizia del database: {e}")
        sys.exit(1)
    finally:
        if 'client' in locals():
            client.close()

if __name__ == "__main__":
    print("="*60)
    print("🔄 PULIZIA DATABASE MONITORAGGIO SISMICO")
    print("="*60)
    print("\n⚠️  Attenzione: questo script cancellerà TUTTI i dati dal database.")
    print("   Assicurati di aver fatto un backup se necessario.\n")
    
    cleanup_database()
