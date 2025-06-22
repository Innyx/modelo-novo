#!/usr/bin/env python3
import os
import csv
from google.cloud import storage
from concurrent.futures import ThreadPoolExecutor, as_completed
from pyzbar.pyzbar import decode
from google.api_core.exceptions import TooManyRequests
import time


os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "saeb_cartoes_manual.json"
# 1. Configure o path para sua chave de serviço, ou rode em Cloud Shell.
GOOGLE_APPLICATION_CREDENTIALS="credentials.json"

# 2. Parâmetros
BUCKET_NAME = "saeb_cartoes_manual"
PASTAS = [
    "contagem"
    # etc...
]
SAIDA_CSV = "image_links_v2.csv"

# 3. Inicializa client e bucket
client = storage.Client()
bucket = client.bucket(BUCKET_NAME)

# 4. Coleta pares (nome, url) em lista
def upload_image(local_path, fn):
    blob = bucket.blob(fn)
    max_attempts = 5
    for attempt in range(1, max_attempts + 1):
        try:
            blob.upload_from_filename(local_path)
            blob.make_public()
            return (fn, blob.public_url)
        except TooManyRequests:
            if attempt == max_attempts:
                raise
            sleep_secs = 2 ** attempt
            print(f"[429] retry em {sleep_secs}s (tentativa {attempt}/{max_attempts}) para {fn}")
            time.sleep(sleep_secs)

print(f'Iniciando upload de imagens...{time.strftime("%H:%M:%S")}')
linhas = []
futures = []
with ThreadPoolExecutor() as executor:
    for pasta in PASTAS:
        for root, _, files in os.walk(pasta):
            for fn in files:
                if fn.lower().endswith((".jpg", ".jpeg", ".png", ".gif", ".bmp")):
                    local_path = os.path.join(root, fn)
                    futures.append(executor.submit(upload_image, local_path, fn))
    for future in as_completed(futures):
        linhas.append(future.result())

#5. Grava CSV
with open(SAIDA_CSV, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["image_name", "public_url"])
    writer.writerows(linhas)

print(f'Fim upload de imagens...{time.strftime("%H:%M:%S")}')
print(f"Upload concluído! CSV gerado em {SAIDA_CSV}")
