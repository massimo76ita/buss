#!/usr/bin/env python3
"""
Script di lancio per il sistema di monitoraggio sismico completo
Avvia sia il sistema di rilevamento che la dashboard web
"""

import subprocess
import sys
import time
import signal
import os
import webbrowser
import threading
from datetime import datetime

class MonitoringSystemLauncher:
    def __init__(self):
        self.processes = []
        self.running = True
        self.server_port = 8000
        
    def start_seismic_detection(self):
        """Avvia il sistema di rilevamento sismico"""
        print("🚀 Avvio sistema di rilevamento sismico...")
        try:
            process = subprocess.Popen([
                sys.executable, "seismic_detection_system.py"
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            self.processes.append(("Seismic Detection", process))
            print("✅ Sistema di rilevamento sismico avviato")
            
            # Thread per mostrare i log in tempo reale
            def show_logs():
                while process.poll() is None:
                    output = process.stdout.readline()
                    if output:
                        print(output.strip())
                    error = process.stderr.readline()
                    if error:
                        print(f"❌ {error.strip()}")
            
            log_thread = threading.Thread(target=show_logs)
            log_thread.daemon = True
            log_thread.start()
            
            return True
        except Exception as e:
            print(f"❌ Errore avvio sistema di rilevamento: {e}")
            return False
    
    def start_web_server(self):
        """Avvia il server web per la dashboard"""
        print("🌐 Avvio server web...")
        try:
            process = subprocess.Popen([
                sys.executable, "log_server.py"
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.processes.append(("Web Server", process))
            print("✅ Server web avviato")
            return True
        except Exception as e:
            print(f"❌ Errore avvio server web: {e}")
            return False
    
    def open_browser_delayed(self, delay=5):
        """Apre il browser dopo un delay per dare tempo al server di avviarsi"""
        def open_browser():
            time.sleep(delay)
            url = f"http://localhost:{self.server_port}"
            print(f"🌐 Apertura browser su: {url}")
            try:
                webbrowser.open(url)
            except Exception as e:
                print(f"⚠️ Errore apertura browser: {e}")
                print(f"📱 Apri manualmente: {url}")
        
        browser_thread = threading.Thread(target=open_browser)
        browser_thread.daemon = True
        browser_thread.start()
    
    def monitor_processes(self):
        """Monitora i processi in esecuzione"""
        print("\n📋 Stato dei servizi:")
        print("=" * 50)
        
        while self.running:
            try:
                for name, process in self.processes:
                    if process.poll() is not None:
                        print(f"⚠️ {name} si è fermato (exit code: {process.returncode})")
                        # Rimuovi il processo terminato
                        self.processes = [(n, p) for n, p in self.processes if p.poll() is None]
                
                if not self.processes:
                    print("❌ Tutti i servizi si sono fermati")
                    break
                
                time.sleep(5)
                
            except KeyboardInterrupt:
                print("\n⏹ Interruzione richiesta dall'utente...")
                self.stop_all_processes()
                break
    
    def stop_all_processes(self):
        """Ferma tutti i processi"""
        print("🛑 Arresto di tutti i servizi...")
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
        """Avvia tutti i servizi"""
        print("🎯 Sistema di Monitoraggio Sismico - Avvio completo")
        print("=" * 60)
        print(f"⏰ Avvio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Registra handler per SIGINT (Ctrl+C)
        signal.signal(signal.SIGINT, lambda sig, frame: self.stop_all_processes())
        
        # Avvia i servizi
        success = True
        success &= self.start_seismic_detection()
        success &= self.start_web_server()
        
        if success:
            print("\n🎉 Tutti i servizi avviati con successo!")
            print(f"📱 Dashboard disponibile su: http://localhost:{self.server_port}")
            print("⏹ Premi Ctrl+C per fermare tutti i servizi")
            print()
            
            # Apri il browser automaticamente
            self.open_browser_delayed(delay=5)
            
            # Monitora i processi
            self.monitor_processes()
        else:
            print("\n❌ Errore nell'avvio di alcuni servizi")
            self.stop_all_processes()

def main():
    launcher = MonitoringSystemLauncher()
    launcher.run()

if __name__ == "__main__":
    main() 