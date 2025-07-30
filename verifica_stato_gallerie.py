from pymongo import MongoClient

uri = "mongodb+srv://massimo76:a5rFSpkB5vIHUoQa@..."
client = MongoClient(uri)
db = client["sismologia"]

for stazione in ["SACR", "CIGN", "TRIV"]:
    count_all = db.tracciati.count_documents({"station": stazione})
    count_img = db.tracciati.count_documents({"station": stazione, "file_id": {"$exists": True}})
    print(f"{stazione}: {count_all} eventi totali — {count_img} con PNG")
