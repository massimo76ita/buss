from datetime import datetime, time
import pytz

# 🌍 Fuso orario Europa/Rome
CEST = pytz.timezone("Europe/Rome")

def is_ultra_low_active():
    """True se siamo tra le 22:00 e le 06:00 CEST"""
    now = datetime.now(CEST).time()
    return (now >= time(22, 0)) or (now <= time(6, 0))

def get_soglie_ultra_low():
    return {
        "MIN_PEAK": 30,
        "MIN_DURATION": 1.0,
        "MAX_RMS_RATIO": 0.98
    }

def get_soglie_standard():
    return {
        "MIN_PEAK": 100,
        "MIN_DURATION": 2.5,
        "MAX_RMS_RATIO": 0.9
    }

def stato_attuale():
    """Ritorna una stringa descrittiva dello stato UL"""
    now = datetime.now(CEST)
    ora_str = now.strftime("%H:%M:%S")
    stato = "🌓 Modalità Ultra Low attiva" if is_ultra_low_active() else "🌞 Modalità standard attiva"
    return f"{stato} | Ora CEST: {ora_str}"
