from keep_alive import keep_alive
import os
from ap_main import setup_bot, start_bot

def main():
    keep_alive()
    updater = setup_bot()
    start_bot(updater)

if __name__ == "__main__":
    os.environ["TELEGRAM_TOKEN"] = "BURAYA_TELEGRAM_BOT_TOKENIN"  # Bot tokenini gir
    main()
📂 keep_alive.py
python
Kopyala
Düzenle
import threading
from http.server import SimpleHTTPRequestHandler, HTTPServer

PORT = 8080

def run_server():
    server_address = ("0.0.0.0", PORT)
    httpd = HTTPServer(server_address, SimpleHTTPRequestHandler)
    httpd.serve_forever()

def keep_alive():
    thread = threading.Thread(target=run_server)
    thread.daemon = True
    thread.start()
    print(f"✅ Keep-Alive aktif: Port {PORT}")