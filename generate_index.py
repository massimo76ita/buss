from datetime import datetime, timezone

stazioni = [
    {"id": "SACR", "nome": "Santa Croce del Sannio", "localita": "(BN)", "color": "#00c6ff"},
    {"id": "CIGN", "nome": "Sant'Elia a Pianisi", "localita": "(CB)", "color": "#ff6b00"},
    {"id": "TRIV", "nome": "Trivento", "localita": "(CB)", "color": "#ff0066"}
]

now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

with open("index.html", "w") as f:
    f.write("<!DOCTYPE html><html lang='it'><head><meta charset='UTF-8'><title>Rete Sismica Molise</title>")
    f.write("<style>")
    f.write("""
        body { background:#111; color:#eee; font-family:'Segoe UI', sans-serif; margin:0; }
        h1 { text-align:center; padding:24px; font-size:28px; background:#222; margin-bottom:0; }
        .grid { display:flex; flex-wrap:wrap; justify-content:center; gap:24px; padding:40px; }
        .card { width:280px; background:#1a1a1a; border-radius:8px; box-shadow:0 0 10px #000;
                padding:20px; text-align:center; transition:0.3s; }
        .card:hover { transform:scale(1.05); box-shadow:0 0 16px #00f6ff88; }
        .btn { display:inline-block; margin-top:12px; padding:10px 16px; border:none; border-radius:6px;
               color:#fff; text-decoration:none; font-weight:bold; font-size:15px; }
        footer { background:#222; color:#888; font-size:12px; text-align:center; padding:14px; margin-top:40px; }
    """)
    f.write("</style></head><body>")
    f.write("<h1>📡 Rete Sismica — Stazioni Monitorate</h1><div class='grid'>")

    for s in stazioni:
        f.write("<div class='card'>")
        f.write(f"<h2>{s['id']} — {s['nome']} {s['localita']}</h2>")
        f.write(f"<a class='btn' style='background:{s['color']}' href='inline_{s['id']}.html'>Vai alla galleria eventi</a><br>")
        f.write(f"<a class='btn' style='background:#00ff88' href='rullo_{s['id']}.html'>Vai al rullo continuo</a>")
        f.write("</div>")

    f.write(f"</div><footer>Rigenerato il {now} — Powered by Massimo & Nathan</footer></body></html>")

