from http.server import HTTPServer, SimpleHTTPRequestHandler
import json
from datetime import datetime
import random
import webbrowser
import threading
import time

class CORSRequestHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        # Abilita CORS per tutte le richieste
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'X-Requested-With, Content-Type')
        return super().end_headers()

    def do_OPTIONS(self):
        # Gestisci le richieste di preflight
        self.send_response(200, "ok")
        self.end_headers()

    def do_GET(self):
        if self.path == '/api/latest-data':
            # Simula dati aggiornati
            data = {
                "timestamp": datetime.now().isoformat(),
                "status": "ok",
                "data": {
                    "ultimo_aggiornamento": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "stazioni_attive": 12,
                    "stato": "normale"
                }
            }
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(data).encode())
        else:
            # Per tutte le altre richieste, usa il comportamento predefinito
            return SimpleHTTPRequestHandler.do_GET(self)

def open_browser(port, delay=2):
    """Apre il browser dopo un breve delay"""
    time.sleep(delay)
    url = f"http://localhost:{port}"
    print(f"🌐 Apertura browser su: {url}")
    webbrowser.open(url)

def run(server_class=HTTPServer, handler_class=CORSRequestHandler, port=8000):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f"🚀 Server in esecuzione su http://localhost:{port}")
    print("⏳ Apertura browser automatica tra 2 secondi...")
    
    # Avvia thread per aprire il browser
    browser_thread = threading.Thread(target=open_browser, args=(port,))
    browser_thread.daemon = True
    browser_thread.start()
    
    httpd.serve_forever()

if __name__ == '__main__':
    run()
