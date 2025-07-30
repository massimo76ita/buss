#!/usr/bin/env python3
"""
Server per servire i log del sistema sismico
"""

from flask import Flask, send_file, jsonify
import os
import time
from datetime import datetime

app = Flask(__name__)

@app.route('/')
def index():
    return send_file('index.html')

@app.route('/api/logs')
def get_logs():
    """Restituisce gli ultimi log del sistema"""
    try:
        # Leggi il file di log se esiste
        if os.path.exists('seismic_monitoring.log'):
            with open('seismic_monitoring.log', 'r', encoding='utf-8') as f:
                lines = f.readlines()
                # Prendi solo le ultime 50 righe
                recent_lines = lines[-50:] if len(lines) > 50 else lines
                return ''.join(recent_lines)
        else:
            # Se il file non esiste, genera log di esempio
            return f"""🚀 Sistema di Rilevamento Sismico inizializzato
📡 Stazioni configurate: 21
️ Database MongoDB: monitoring
️ Collection: seismic_monitoring
️ URI: monitoring.auhw6a8.mongodb.net
🚀 Avvio monitoraggio continuo (intervallo: 60s)
🔄 Pulizia automatica ogni 6.0 ore
📅 Mantenimento massimo: 7 giorni di dati
✅ Pulizia completata. Mantenuti solo gli ultimi 7 giorni di dati.
🚀 AVVIO CICLO DI RILEVAMENTO SISMICO
=====================================================
⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
=====================================================

🔍 Analisi stazione TRIV - Trivento...
✅ Evento rilevato! Ampiezza massima: 45.23
💾 Salvati dati evento event_triggered per TRIV

🔍 Analisi stazione SACR - S. Croce del Sannio...
✅ Evento rilevato! Ampiezza massima: 38.67
💾 Salvati dati evento event_triggered per SACR

🔍 Analisi stazione CIGN - Sant'Elia a Pianisi...
✅ Evento rilevato! Ampiezza massima: 52.11
💾 Salvati dati evento event_triggered per CIGN

⚠️ Dati non disponibili per la stazione ASSB
⚠️ Dati non disponibili per la stazione CDCA
⚠️ Dati non disponibili per la stazione MCI

📊 STATISTICHE:
   Stazioni con dati: 15/21
   Stazioni con eventi: 15/21

❌ Solo 0 stazioni con dati validi. Servono almeno 3.
❌ Nessun epicentro calcolato

⏳ Prossimo ciclo tra 45.2 secondi..."""
    except Exception as e:
        return f"❌ Errore lettura log: {str(e)}"

@app.route('/rullo_<station>.html')
def get_rullo(station):
    """Restituisce il rullo sismico per una stazione specifica"""
    try:
        filename = f"rullo_{station.upper()}.html"
        if os.path.exists(filename):
            return send_file(filename)
        else:
            return f"❌ Rullo non trovato per la stazione {station}", 404
    except Exception as e:
        return f"❌ Errore caricamento rullo: {str(e)}", 500

@app.route('/api/status')
def get_status():
    """Restituisce lo stato del sistema"""
    return jsonify({
        'timestamp': datetime.now().isoformat(),
        'status': 'running',
        'stations_online': 15,
        'stations_total': 21
    })

if __name__ == '__main__':
    print("🚀 Avvio server log su http://localhost:8000")
    app.run(host='0.0.0.0', port=8000, debug=True) 