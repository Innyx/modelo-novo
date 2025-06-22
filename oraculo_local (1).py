#!/usr/bin/env python3
import os
import cv2
import numpy as np
from pyzbar.pyzbar import decode
import pandas as pd
from global_keys import get_database_credentials
import sqlalchemy

# --- Configuração de acesso ao banco ---
CREDENTIALS = get_database_credentials()
engine = sqlalchemy.create_engine(
    f"postgresql://{CREDENTIALS['user']}:{CREDENTIALS['password']}@"
    f"{CREDENTIALS['host']}:{CREDENTIALS['port']}/{CREDENTIALS['database']}",
    pool_pre_ping=True
)
SCHEMA = "simulado_5"  # ajuste para o nome do seu schema
SIMULADO = "5"

# --- Configurações de imagem ---
LIMIAR_PREENCHIDO = 0.0
MAX_WIDTH = 2280
MAX_HEIGHT = 3220

# Dados para presença: (x_center, y_center)
presence_x = [125, 128, 720, 385]
presence_y = [1040, 1120, 1120, 1040]
PRESENCE_RECT = (50, 50)   # largura, altura = 2*r (r=25)

# Dados para presença de 5º ano
presence_x_5_ano = [125, 128, 720, 385]
presence_y_5_ano = [1040, 1120, 1120, 1040]
PRESENCE_RECT_5 = (60, 60)  # 2*r para r variáveis

# Coordenadas base para respostas: 4 colunas × 11 linhas
SHIFT = 0
SHIFT2 = 0
x_coords = [215, 765, 1298+SHIFT, 1840+SHIFT2]
y_coords = [1790 + 85 * i for i in range(13)]
RECT_SIZE = (60, 60)

# Coordenadas base para respostas de 5º ano
x_coords_5_ano = [220, 770, 1298+SHIFT, 1840+SHIFT2]
y_coords_5_ano = [1800 + 85 * i for i in range(11)]

# Garante que o diretório de saída exista
dirsafe = lambda d: os.makedirs(d, exist_ok=True)


def query_table(schema: str, sim_prefix: str) -> pd.DataFrame:
    """
    Carrega d_cursos do schema e filtra simulado_id ending em '05' ou '09' para o prefixo.
    """
    table = f"{schema}.d_avaliacoes"
    df = pd.read_sql(f"SELECT * FROM {table};", engine, dtype={'avaliacao_id': str, "simulado_id":str})
    sim05 = f"{sim_prefix}05"
    sim09 = f"{sim_prefix}09"
    return df[df["simulado_id"].isin([sim05, sim09])]


def crop_to_limits(img):
    h, w = img.shape[:2]
    if w > MAX_WIDTH or h > MAX_HEIGHT:
        x = (w - MAX_WIDTH) // 2
        y = (h - MAX_HEIGHT) // 2
        return img[y:y+MAX_HEIGHT, x:x+MAX_WIDTH]
    return img


def extrair_qrcode_roi(img):
    roi = img[1:470, 1:470]
    return roi, (1, 1, 470, 470)


def analisar_retangulo(img_gray, x, y, w, h):
    roi = img_gray[y:y+h, x:x+w]
    _, binary = cv2.threshold(roi, 128, 255, cv2.THRESH_BINARY_INV)
    marked = cv2.countNonZero(binary)
    total = roi.size
    return (marked / total * 100) if total else 0


def processar_e_visualizar(image_path: str, output_path: str):
    # Carrega e prepara imagem
    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"Não consegui carregar {image_path}")
    img = crop_to_limits(img)
    vis = img.copy()
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # 1) QR code: extrai e decodifica
    qr_roi, (qx, qy, qw, qh) = extrair_qrcode_roi(img)
    cv2.rectangle(vis, (qx, qy), (qx+qw, qy+qh), color=(255, 0, 0), thickness=2)
    decoded = decode(qr_roi)
    simulado_id = None

    if decoded:
        qr_text = decoded[0].data.decode("utf-8")
        parts = qr_text.split("-")
        avaliacao_id = parts[1]
        # prefix é tudo antes dos dois últimos dígitos do primeiro campo
     
        # consulta dimensão de cursos para esse prefixo
        df_cursos = query_table(SCHEMA, SIMULADO)
        row = df_cursos[df_cursos["avaliacao_id"] == avaliacao_id]
        if not row.empty:
            simulado_id = row["simulado_id"].iloc[0]

    # Escolhe as coordenadas certas conforme o simulado
    print(simulado_id)
    if simulado_id and simulado_id.endswith("05"):
        pres_x = presence_x_5_ano
        pres_y = presence_y_5_ano
        pres_size = PRESENCE_RECT_5
        resp_x = x_coords_5_ano
        resp_y = y_coords_5_ano
    else:
        pres_x = presence_x
        pres_y = presence_y
        pres_size = PRESENCE_RECT
        resp_x = x_coords
        resp_y = y_coords

    # 2) Presença (mesma lógica de 'respostas')
    w_pres, h_pres = pres_size
    for xc, yc in zip(pres_x, pres_y):
        x0 = xc - w_pres // 2
        y0 = yc - h_pres // 2
        perc = analisar_retangulo(gray, x0, y0, w_pres, h_pres)
        if perc >= LIMIAR_PREENCHIDO:
            cv2.rectangle(vis, (x0, y0), (x0 + w_pres, y0 + h_pres),
                          color=(0, 255, 0), thickness=3)

    # 3) Respostas
    for xb in resp_x:
        for yb in resp_y:
            for opt in range(4):
                px = xb + opt * 100
                py = yb
                perc = analisar_retangulo(gray, px, py, *RECT_SIZE)
                if perc >= LIMIAR_PREENCHIDO:
                    cv2.rectangle(vis, (px, py),
                                  (px + RECT_SIZE[0], py + RECT_SIZE[1]),
                                  color=(0, 0, 255), thickness=2)

    # Salva saída
    cv2.imwrite(output_path, vis)
    print(f"Imagem anotada salva em: {output_path}")


if __name__ == "__main__":
    IMAGE_PATH = "scanners teste/scanners teste/01/13062025_Prefeitura de Manaus_001.jpg"
    OUTPUT_PATH = "minha_imagem_out.jpg"
    processar_e_visualizar(IMAGE_PATH, OUTPUT_PATH)
