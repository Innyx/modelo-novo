#!/usr/bin/env python3
import os
import cv2
import numpy as np
import json
import concurrent.futures
import time
import shutil
from pyzbar.pyzbar import decode
import pandas as pd
import sqlalchemy
from global_keys import get_database_credentials

# --- Banco de Dados ---
CREDENTIALS = get_database_credentials()
engine = sqlalchemy.create_engine(
    f"postgresql://{CREDENTIALS['user']}:{CREDENTIALS['password']}@"
    f"{CREDENTIALS['host']}:{CREDENTIALS['port']}/{CREDENTIALS['database']}",
    pool_pre_ping=True
)
SCHEMA = "simulado_5"
SIMULADO = "5"

# --- Diretórios ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.join(BASE_DIR, 'scanners teste')        # pasta com subpastas regionais
OUTPUT_JSON_DIR = os.path.join(BASE_DIR, 'json_oraculo')     # saída de JSONs por subpasta
MANUAL_COMP_DIR = os.path.join(BASE_DIR, 'unknown_qr')        # imagens com QR não reconhecido
os.makedirs(OUTPUT_JSON_DIR, exist_ok=True)
os.makedirs(MANUAL_COMP_DIR, exist_ok=True)

# --- Configurações de processamento ---
LIMIAR_PREENCHIDO = 22.0
MAX_WIDTH = 2280
MAX_HEIGHT = 3220

# Parâmetros de presença e respostas
presence_x = [125, 128, 720, 385]
presence_y = [1040, 1120, 1120, 1040]
PRESENCE_RECT = (50, 50)

# Coordenadas de resposta: 4 colunas × 13 linhas
SHIFT = 0
SHIFT2 = 0
x_coords = [215, 765, 1298+SHIFT, 1840+SHIFT2]
y_coords = [1790 + 85 * i for i in range(13)]
RECT_SIZE = (60, 60)


def query_table(schema: str, sim_prefix: str) -> pd.DataFrame:
    table = f"{schema}.d_avaliacoes"
    df = pd.read_sql(f"SELECT * FROM {table};", engine, dtype={'avaliacao_id': str, 'simulado_id': str})
    sim05 = f"{sim_prefix}05"
    sim09 = f"{sim_prefix}09"
    return df[df['simulado_id'].isin([sim05, sim09])]


def crop_to_limits(img):
    h, w = img.shape[:2]
    if w > MAX_WIDTH or h > MAX_HEIGHT:
        x = (w - MAX_WIDTH) // 2
        y = (h - MAX_HEIGHT) // 2
        return img[y:y+MAX_HEIGHT, x:x+MAX_WIDTH]
    return img


def extrair_qrcode(img):
    roi = img[1:470, 1:470]
    detector = cv2.QRCodeDetector()
    data, _, _ = detector.detectAndDecode(roi)
    if data:
        parts = data.strip().split('-')
        if len(parts) == 3:
            return {'curso_id': parts[0], 'avaliacao_id': parts[1], 'estudante_id': parts[2], 'raw': data}
    return {'raw': 'Unknown'}


def analisar_retangulo(img_gray, x, y, w, h, threshold=LIMIAR_PREENCHIDO):
    roi = img_gray[y:y+h, x:x+w]
    _, binary = cv2.threshold(roi, 128, 255, cv2.THRESH_BINARY_INV)
    total = roi.size
    marked = cv2.countNonZero(binary)
    perc = (marked / total * 100) if total else 0
    return perc


def process_image(image_path: str) -> dict:
    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"Não carregou: {image_path}")
    img = crop_to_limits(img)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # QR Code
    qr = extrair_qrcode(img)
    avaliacao_id = qr.get('avaliacao_id')
    simulado_id = None
    if avaliacao_id:
        df = query_table(SCHEMA, SIMULADO)
        row = df[df['avaliacao_id'] == avaliacao_id]
        if not row.empty:
            simulado_id = row['simulado_id'].iloc[0]
    qr['simulado_id'] = simulado_id

    # Presença
    pres = {}
    w_pres, h_pres = PRESENCE_RECT
    for idx, (xc, yc) in enumerate(zip(presence_x, presence_y)):
        x0, y0 = xc - w_pres//2, yc - h_pres//2
        perc = analisar_retangulo(gray, x0, y0, w_pres, h_pres)
        pres[f'grupo_{idx}'] = 'Marcado' if perc >= LIMIAR_PREENCHIDO else None

    # Respostas
    resp = {}
    for col_idx, xb in enumerate(x_coords):
        for row_idx, yb in enumerate(y_coords):
            qid = f'questao_{col_idx*len(y_coords) + row_idx + 1}'
            marked = []
            for opt in range(4):
                px = xb + opt*100
                perc = analisar_retangulo(gray, px, yb, RECT_SIZE[0], RECT_SIZE[1])
                if perc >= LIMIAR_PREENCHIDO:
                    marked.append(opt)
            resp[qid] = marked or None

    return {'filename': os.path.basename(image_path), 'qrcode': qr, 'presenca': pres, 'respostas': resp}


def main():
    start = time.perf_counter()
    # Itera por cada subpasta em PARENT_DIR
    for sub in os.listdir(PARENT_DIR):
        subdir = os.path.join(PARENT_DIR, sub)
        if not os.path.isdir(subdir):
            continue
        results = []
        # Coleta imagens na subpasta recursivamente
        images = []
        for root, _, files in os.walk(subdir):
            for f in files:
                if f.lower().endswith(('.jpg', '.jpeg', '.png')):
                    images.append(os.path.join(root, f))
        # Processa em paralelo
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            futures = {executor.submit(process_image, img): img for img in images}
            for fut in concurrent.futures.as_completed(futures):
                img_path = futures[fut]
                try:
                    data = fut.result()
                    results.append(data)
                    # Copia imagens com QR desconhecido
                    if data['qrcode'].get('raw') == 'Unknown':
                        shutil.copy(img_path, MANUAL_COMP_DIR)
                except Exception as e:
                    print(f"Erro em {img_path}: {e}")
        # Grava um JSON por subpasta
        out_file = os.path.join(OUTPUT_JSON_DIR, f"{sub}.json")
        with open(out_file, 'w', encoding='utf-8') as jf:
            json.dump(results, jf, ensure_ascii=False, indent=4)
    elapsed = time.perf_counter() - start
    print(f"Processamento concluído em {elapsed:.2f}s")

if __name__ == '__main__':
    main()
