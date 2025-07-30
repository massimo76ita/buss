#!/usr/bin/env python3
"""
Script per avviare solo i processi di streaming dei rulli
Questi processi acquisiscono dati sismici in tempo reale e li salvano nei database
"""

import subprocess
import sys
import time
import signal
import os
from datetime import datetime

class StreamRulliLauncher:
    def __init__(self):
        self.processes = []
        self.running = True
        
    def start_stream_rulli(self):
        """Avvia i processi di streaming dei rulli per tutte le stazioni"""
        print("📡 Avvio stream rulli...")
        success = True
        
        for station in ["triv", "sacr", "cign"]:
            try:
                script_name = f"stream_rullo_{station}.py"
                print(f"🚀 Avvio {script_name}...")
                process = subprocess.Popen([
                    sys.executable, script_name
                ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                self.processes.append((f"Stream Rullo {station.upper()}", process))
                print(f"✅ Stream rullo {station.upper()} avviato")
                time.sleep(2)  # Piccola pausa tra l'avvio dei processi
            except Exception as e:
                print(f"❌ Errore avvio stream rullo {station}: {e}")
                success = False
        
        return success
    
    def monitor_processes(self):
        """Monitora i processi in esecuzione"""
        print("\n📋 Stato degli stream rulli:")
        print("=" * 50)
        
        while self.running:
            try:
                for name, process in self.processes:
                    if process.poll() is not None:
                        print(f"⚠️ {name} si è fermato (exit code: {process.returncode})")
                        # Rimuovi il processo terminato
                        self.processes = [(n, p) for n, p in self.processes if p.poll() is None]
                
                if not self.processes:
                    print("❌ Tutti gli stream rulli si sono fermati")
                    break
                
                time.sleep(10)
                
            except KeyboardInterrupt:
                print("\n⏹ Interruzione richiesta dall'utente...")
                self.stop_all_processes()
                break
    
    def stop_all_processes(self):
        """Ferma tutti i processi"""
        print("🛑 Arresto di tutti gli stream rulli...")
        for name, process in self.processes:
            try:
                process.terminate()
                process.wait(timeout=5)
                print(f"✅ {name} arrestato")
            except subprocess.TimeoutExpired:
                process.kill()
                print(f"⚠️ {name} forzato all'arresto")
            except Exception as e:
                print(f"❌ Errore arresto {name}: {e}")
    
    def run(self):
        """Avvia tutti gli stream rulli"""
        print("🎬 Sistema di Streaming Rulli - Avvio")
        print("=" * 50)
        print(f"⏰ Avvio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Registra handler per SIGINT (Ctrl+C)
        signal.signal(signal.SIGINT, lambda sig, frame: self.stop_all_processes())
        
        # Avvia gli stream rulli
        success = self.start_stream_rulli()
        
        if success:
            print("\n🎉 Tutti gli stream rulli avviati con successo!")
            print("📊 I database dei rulli verranno aggiornati in tempo reale")
            print("⏹ Premi Ctrl+C per fermare tutti gli stream")
            print()
            
            # Monitora i processi
            self.monitor_processes()
        else:
            print("\n❌ Errore nell'avvio di alcuni stream rulli")
            self.stop_all_processes()

def main():
    launcher = StreamRulliLauncher()
    launcher.run()

if __name__ == "__main__":
    main() 