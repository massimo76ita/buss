from pymongo import MongoClient

uri = "mongodb+srv://massimoserafini1976:RxqRhJrVl4wDGOv@rullo.evun5ie.mongodb.net/?retryWrites=true&w=majority&appName=rullo"
client = MongoClient(uri)

print("📦 Database e collezioni disponibili:\n")
for db_name in client.list_database_names():
    print(f"🗂️ {db_name}")
    db = client[db_name]
    try:
        collections = db.list_collection_names()
        for col in collections:
            print(f"   └── 📁 {col}")
    except Exception as e:
        print(f"   ⚠️ Errore: {e}")
