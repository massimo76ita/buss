#!/usr/bin/env python3
"""
Script semplice per avviare la dashboard con apertura automatica del browser
"""

import subprocess
import sys
import webbrowser
import time
import threading

def open_browser_delayed(port=8000, delay=3):
    """Apre il browser dopo un delay"""
    def open_browser():
        time.sleep(delay)
        url = f"http://localhost:{port}"
        print(f"🌐 Apertura browser su: {url}")
        try:
            webbrowser.open(url)
        except Exception as e:
            print(f"⚠️ Errore apertura browser: {e}")
            print(f"📱 Apri manualmente: {url}")
    
    browser_thread = threading.Thread(target=open_browser)
    browser_thread.daemon = True
    browser_thread.start()

def main():
    print("🚀 Avvio Dashboard Monitoraggio Sismico")
    print("=" * 50)
    
    # Avvia il server
    print("🌐 Avvio server web...")
    try:
        # Avvia thread per aprire il browser
        open_browser_delayed(port=8000, delay=3)
        
        # Avvia il server
        subprocess.run([sys.executable, "server.py"])
        
    except KeyboardInterrupt:
        print("\n⏹ Server fermato dall'utente")
    except Exception as e:
        print(f"❌ Errore: {e}")

if __name__ == "__main__":
    main() 