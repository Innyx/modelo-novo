#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import csv
import json
import time
import cv2
import numpy as np
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from pyzbar.pyzbar import decode
from google.cloud import storage
from google.api_core.exceptions import TooManyRequests

# —————— CONFIGURAÇÃO GCP ——————
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "innyx-tecnologia.json"
BUCKET_NAME = "saeb_cartoes_manual"

# —————— PARÂMETROS ——————
# —————— PARÂMETROS ——————
PASTAS    = [
     'ddzs',  

    # "E:/ddzs/DDZ CENTRO SUL",
    # "E:/ddzs/DDZ LESTE I",
    # "E:/ddzs/DDZ RURAL",
    # "E:/ddzs/DDZ SUL",
    # adicione outras pastas conforme desejar
]
SAIDA_CSV = "image_links.csv"

# —————— LÊ CSV DE CARTOES QUE JA ESTAO NO BUCKET ——————
df_processados  = pd.read_csv('image_links_luis.csv', dtype=str, encoding='utf-8')


# —————— INICIALIZA CLIENTE GCS ——————
client = storage.Client()
bucket = client.bucket(BUCKET_NAME)

# —————— CROPPING CONSTANTS ——————
MAX_WIDTH  = 2280
MAX_HEIGHT = 3220

def crop_to_limits(img):
    """Corta o centro da imagem se ultrapassar as dimensões máximas."""
    h, w = img.shape[:2]
    if w > MAX_WIDTH or h > MAX_HEIGHT:
        x = (w - MAX_WIDTH) // 2
        y = (h - MAX_HEIGHT) // 2
        return img[y:y+MAX_HEIGHT, x:x+MAX_WIDTH]
    return img

# —————— HELPERS PARA QR ——————
def _extract_qr_data(image_path: str) -> dict:
    """
    Carrega imagem, aplica crop_to_limits, lê ROI fixa do QR code,
    decodifica e retorna dict com curso_id, avaliacao_id, estudante_id, raw.
    """
    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"Não consegui carregar '{image_path}'")
    # aplica recorte antes de extrair o QR
    img = crop_to_limits(img)

    # ROI fixa para QR (1:470, 1:470)
    roi = img[1:470, 1:470]
    decoded = decode(roi)
    if not decoded:
        return {'curso_id': None, 'avaliacao_id': None, 'estudante_id': None, 'raw': 'Unknown'}

    txt = decoded[0].data.decode("utf-8").strip()
    parts = txt.split("-")
    if len(parts) == 3:
        return {
            'curso_id':     parts[0],
            'avaliacao_id': parts[1],
            'estudante_id': parts[2],
            'raw':          txt
        }
    return {'curso_id': None, 'avaliacao_id': None, 'estudante_id': None, 'raw': txt}

def _upload_and_record(image_path: str):
    """
    • Extrai QR com crop aplicado
    • Monta blob_name incluindo JSON+filename para evitar colisões
    • Faz upload COM retry e backoff em 429
    • Retorna (estudante_id, avaliacao_id, curso_id, public_url)
    """
    qr = _extract_qr_data(image_path)
    filename = os.path.basename(image_path)

    # monta blob_name: JSON compacto + '|' + filename
    blob_key = {'curso_id': qr['curso_id'],
                'avaliacao_id': qr['avaliacao_id'],
                'estudante_id': qr['estudante_id']}
    blob_name = json.dumps(blob_key, ensure_ascii=False, separators=(',',':')) + '|' + filename

    blob = bucket.blob(blob_name)

    # retry/backoff exponencial
    max_attempts = 5
    for attempt in range(1, max_attempts+1):
        try:
            blob.upload_from_filename(image_path)
            blob.make_public()
            break
        except TooManyRequests:
            if attempt == max_attempts:
                raise
            sleep_secs = 2 ** attempt
            print(f"[429] retry em {sleep_secs}s (tentativa {attempt}/{max_attempts})")
            time.sleep(sleep_secs)

    return (
        qr['estudante_id'],
        qr['avaliacao_id'],
        qr['curso_id'],
        blob.public_url
    )

# —————— MAIN ——————
def main():
    # coleta todos os caminhos de imagem
    image_paths = []
    old = []
    for pasta in PASTAS:
        for root, _, files in os.walk(pasta):
            for fn in files:
                if fn.lower().endswith((".jpg",".jpeg",".png",".gif",".bmp")):
                    qr = _extract_qr_data(os.path.join(root, fn))
                    # print(qr['estudante_id'])
                    if qr['estudante_id'] and isinstance(qr['estudante_id'], str):
                        if df_processados['estudante_id'].str.contains(qr['estudante_id']).any():
                            print(f"Imagem {fn} já processada, ignorando.")
                            continue
                    else:
                        print(f"QR inválido em {fn}, ignorando.")
                        continue
                    image_paths.append(os.path.join(root, fn))

    # upload em paralelo
    print(f"Encontradas {image_paths} , {len(image_paths)} imagens para upload.")
    print(f"Encontradas {old} , {len(old)} imagens que já estão no bucket.")
    rows = []
    # with ThreadPoolExecutor(max_workers=8) as pool:
    #     futures = {pool.submit(_upload_and_record, path): path
    #                for path in image_paths}
    #     for fut in as_completed(futures):
    #         path = futures[fut]
    #         try:
    #             estudante_id, avaliacao_id, curso_id, url = fut.result()
    #             rows.append([estudante_id, avaliacao_id, curso_id, url])
    #         except Exception as e:
    #             print(f"[ERRO] {path}: {e}")

    # grava CSV final
    with open(SAIDA_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["estudante_id", "avaliacao_id", "curso_id", "public_url"])
        writer.writerows(rows)

    print(f"Upload concluído! CSV gerado em '{SAIDA_CSV}'")

if __name__ == "__main__":
    main()
