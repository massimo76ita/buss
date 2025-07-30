import os
from pymongo import MongoClient
from datetime import datetime, timezone, timedelta

def genera_html(station):
    giorno = datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=2))).strftime("%Y-%m-%d")

    uri = "mongodb+srv://massimo76:a5rFSpkB5vIHUoQa@clusterbusso.dbrl7bb.mongodb.net/?retryWrites=true&w=majority&appName=ClusterBusso"
    client = MongoClient(uri)
    db = client["sismologia"]

    doc_list = db.tracciati.find({
        "station": station,
        "day_key": giorno
    }).sort("timestamp_utc", -1)

    rows = ""
    for doc in doc_list:
        ora = doc.get("timestamp_cest", "")[11:19] if "timestamp_cest" in doc else "—"
        filename = doc.get("filename", "—")
        peak = f"{doc.get('peak'):.0f}" if isinstance(doc.get('peak'), (int, float)) else "—"
        rms = f"{doc.get('rms'):.2f}" if isinstance(doc.get('rms'), (int, float)) else "—"
        evento = "✅" if doc.get("evento") else ""
        coincidenza = "🔴" if doc.get("coincidenza") else ""

        rows += f"""
        <tr>
            <td>{ora}</td>
            <td><img src="{filename}" width="300"></td>
            <td>{peak}</td>
            <td>{rms}</td>
            <td>{evento}</td>
            <td>{coincidenza}</td>
        </tr>
        """

    html = f"""<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <title>Tracciati {station} – {giorno}</title>
    <meta http-equiv="refresh" content="120">
    <style>
        body {{ font-family: Arial; background: #f9f9f9; }}
        h1 {{ color: #333; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ border: 1px solid #ccc; padding: 8px; text-align: center; }}
        th {{ background: #eee; }}
    </style>
</head>
<body>
    <h1>📍 Stazione {station} – {giorno}</h1>
    <table>
        <tr>
            <th>Ora (CEST)</th>
            <th>PNG</th>
            <th>Peak</th>
            <th>RMS</th>
            <th>Evento</th>
            <th>Coincidenza</th>
        </tr>
        {rows}
    </table>
</body>
</html>"""

    filename = f"{station}_{giorno}.html"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"[✓] HTML con auto-refresh generato: {filename}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 2:
        genera_html(sys.argv[1])
    else:
        print("❌ Specificare una stazione (es. SACR o CIGN)")
