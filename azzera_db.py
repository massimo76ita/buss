from pymongo import MongoClient

# === Connessione ===
uri = "mongodb+srv://massimo76:a5rFSpkB5vIHUoQa@clusterbusso.dbrl7bb.mongodb.net/?retryWrites=true&w=majority&appName=ClusterBusso"
client = MongoClient(uri)
db = client["sismologia"]

# === Collezioni da rimuovere ===
COLLEZIONI = ["tracciati", "fs.files", "fs.chunks"]

for coll_name in COLLEZIONI:
    result = db[coll_name].delete_many({})
    print(f"[✓] Rimossi {result.deleted_count} documenti da '{coll_name}'")

print("\n🔥 Database 'sismologia' completamente ripulito.")
