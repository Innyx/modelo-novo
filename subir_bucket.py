#!/usr/bin/env python3
import os
import csv
from google.cloud import storage


os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "innyx-tecnologia.json"
# 1. Configure o path para sua chave de serviço, ou rode em Cloud Shell.
GOOGLE_APPLICATION_CREDENTIALS="credentials.json"

# 2. Parâmetros
BUCKET_NAME = "saeb_cartoes_manual"
PASTAS = [
    "s4_oficial_35.847_arq"
    # etc...
]
SAIDA_CSV = "image_links.csv"

# 3. Inicializa client e bucket
client = storage.Client()
bucket = client.bucket(BUCKET_NAME)

# 4. Coleta pares (nome, url) em lista
linhas = []
for pasta in PASTAS:
    for root, _, files in os.walk(pasta):  # Usa os.walk para percorrer subpastas
        for fn in files:
            if fn.lower().endswith((".jpg", ".jpeg", ".png", ".gif", ".bmp")):
                local_path = os.path.join(root, fn)
                blob = bucket.blob(fn)
                blob.upload_from_filename(local_path)
                blob.make_public()
                linhas.append((fn, blob.public_url))

#5. Grava CSV
with open(SAIDA_CSV, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["image_name", "public_url"])
    writer.writerows(linhas)

print(f"Upload concluído! CSV gerado em {SAIDA_CSV}")
