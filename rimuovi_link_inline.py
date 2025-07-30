import os

# === File generatori da eliminare ===
generatori = [
    "generate_html_inline_CIGN.py",
    "generate_html_inline_SACR.py",
    "generate_html_inline_TRIV.py"
]

# === File HTML da eliminare ===
html_inline = [
    "inline_CIGN.html",
    "inline_SACR.html",
    "inline_TRIV.html"
]

# === Elimina generatori
for file in generatori:
    if os.path.exists(file):
        os.remove(file)
        print(f"🗑️ Eliminato script: {file}")

# === Elimina HTML inline
for file in html_inline:
    if os.path.exists(file):
        os.remove(file)
        print(f"🗑️ Eliminato file HTML: {file}")

# === Pulisci index.html
index_path = "index.html"
if os.path.exists(index_path):
    with open(index_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    cleaned = []
    for line in lines:
        if any(tag in line for tag in html_inline):
            print(f"🧹 Rimosso da index.html: {line.strip()}")
            continue
        if "<iframe" in line or "<object" in line:
            print(f"🧹 Rimosso embed: {line.strip()}")
            continue
        cleaned.append(line)

    with open(index_path, "w", encoding="utf-8") as f:
        f.writelines(cleaned)

    print("✅ index.html ripulito")

else:
    print("⚠️ index.html non trovato")

print("✅ Pulizia completata.")
