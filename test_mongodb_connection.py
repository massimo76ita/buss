from pymongo import MongoClient
from datetime import datetime

# URI del tuo cluster MongoDB
mongo_uri = "mongodb+srv://massimoserafini:QIs0axxmwPcEKS78@monitoring.auhw6a8.mongodb.net/?retryWrites=true&w=majority&appName=monitoring"

try:
    # Connessione
    client = MongoClient(mongo_uri)
    client.admin.command('ping')
    print("✅ Connessione a MongoDB riuscita")

    # Seleziona database e collection
    db = client["monitoring"]
    collection = db["seismic_monitoring"]

    # Documento di test
    test_doc = {
        "type": "test_entry",
        "station": "TEST",
        "timestamp": datetime.utcnow().isoformat(),
        "note": "Verifica scrittura e lettura"
    }

    # Scrittura
    result = collection.insert_one(test_doc)
    print(f"📥 Documento inserito con ID: {result.inserted_id}")

    # Lettura
    found = collection.find_one({"_id": result.inserted_id})
    if found:
        print("🔍 Documento trovato:")
        for k, v in found.items():
            print(f"   {k}: {v}")
    else:
        print("❌ Documento non trovato")

    # Pulizia (opzionale)
    delete = input("Vuoi eliminare il documento di test? (s/n): ").strip().lower()
    if delete == 's':
        collection.delete_one({"_id": result.inserted_id})
        print("🧹 Documento eliminato")

except Exception as e:
    print(f"❌ Errore: {e}")
