import subprocess
import time
import os
import webbrowser

# === Configurazione ===
STAZIONI = ["sacr", "cign", "triv"]
INTERVALLO_SEC = 120
DASHBOARD_APERTA = False

# === Avvio stream rullo per tutte le stazioni ===
def avvia_rullo():
    for stazione in STAZIONI:
        try:
            nome_script = f"stream_rullo_{stazione}.py"
            print(f"[🎬] Avvio rullo continuo: {nome_script}")
            subprocess.Popen(["python3", nome_script])
        except Exception as e:
            print(f"[⚠️] Errore avvio rullo {stazione.upper()}: {e}")

# === Avvio monitoraggio per stazione ===
def avvia_monitoraggio(nome):
    try:
        nome_script = f"stream_upload_{nome}.py"
        print(f"[📡] Avvio monitoraggio: {nome_script}")
        subprocess.Popen(["python3", nome_script])
    except Exception as e:
        print(f"[⚠️] Errore avvio monitoraggio {nome.upper()}: {e}")

# === Avvio sistema di rilevamento automatico ===
def avvia_sistema_rilevamento():
    try:
        print(f"[🔍] Avvio sistema di rilevamento automatico")
        subprocess.Popen(["python3", "seismic_detection_system.py"])
    except Exception as e:
        print(f"[⚠️] Errore avvio sistema rilevamento: {e}")

# === Avvio sistema di pulizia automatica ===
def avvia_pulizia_automatica():
    try:
        print(f"[🧹] Avvio sistema di pulizia automatica database")
        subprocess.Popen(["python3", "database_cleanup.py"])
    except Exception as e:
        print(f"[⚠️] Errore avvio pulizia automatica: {e}")

# === Avvio rulli statici (se servono) ===
def aggiorna_rulli_statici():
    try:
        print("[🔧] Aggiornamento rulli statici...")
        subprocess.run(["python3", "rullo_sacr.py"])
        subprocess.run(["python3", "rullo_cign.py"])
        subprocess.run(["python3", "rullo_triv.py"])
        print("[✅] Rulli aggiornati")
    except Exception as e:
        print(f"[⚠️] Errore aggiornamento rulli: {e}")

# === Apertura dashboard ===
def apri_dashboard():
    global DASHBOARD_APERTA
    if not DASHBOARD_APERTA:
        try:
            webbrowser.open("index.html")
            DASHBOARD_APERTA = True
            print("[🌐] Dashboard aperta")
        except Exception as e:
            print(f"[⚠️] Errore apertura dashboard: {e}")

# === Loop continuo ===
if __name__ == "__main__":
    ciclo = 0
    
    # Avvia tutti i sistemi
    print("�� AVVIO SISTEMA COMPLETO DI MONITORAGGIO SISMICO")
    print("=" * 60)
    
    avvia_rullo()
    avvia_sistema_rilevamento()
    avvia_pulizia_automatica()  # NUOVO: sistema di pulizia automatica

    while True:
        ciclo += 1
        print(f"\n🔄 [CICLO {ciclo}] — Avvio monitoraggio multiplo")
        inizio = time.time()

        for nome in STAZIONI:
            avvia_monitoraggio(nome)

        aggiorna_rulli_statici()
        apri_dashboard()

        durata = time.time() - inizio
        print(f"[⏱] Ciclo {ciclo} completato in {durata:.2f} sec")
        print(f"🕒 Attendo {INTERVALLO_SEC} secondi prima del prossimo ciclo...\n")

        time.sleep(INTERVALLO_SEC)