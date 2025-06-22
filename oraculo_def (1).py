#!/usr/bin/env python3
import os
import cv2
import numpy as np
from pyzbar.pyzbar import decode
import pandas as pd
from global_keys import get_database_credentials
import sqlalchemy


# ------------------------------------------------------------------
# AJUSTE estes três caminhos de acordo com o seu projeto
# ------------------------------------------------------------------
BASE_DIR               = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR             = os.path.join(BASE_DIR, "reprocessamento")      # raiz das regiões
OUTPUT_JSON_DIR        = os.path.join(BASE_DIR, "json_reprocessamento")        # onde salvar .json
MANUAL_COMP_DIR_SUFFIX = "manual_comp"                                 # sufixo da pasta p/ erros
os.makedirs(OUTPUT_JSON_DIR, exist_ok=True)





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
LIMIAR_PREENCHIDO = 22.0
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
    table = f"{schema}.d_estudantes"
    df = pd.read_sql(f"SELECT * FROM {table};", engine, dtype={ "simulado_id":str})
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

def extrair_qrcode_info(img):
    """Lê ROI do QR, decodifica e devolve dict {curso_id, avaliacao_id, estudante_id} ou 'raw'."""
    roi = img[1:470, 1:470]
    decoded = decode(roi)
    if not decoded:
        return {'raw': 'Unknown'}
    qr_text = decoded[0].data.decode("utf-8")          # Ex.: "CURSO-AVAL-ESTUDANTE"
    partes = qr_text.split("-")
    if len(partes) == 3:
        return {
            'curso_id':     partes[0],
            'avaliacao_id': partes[1],
            'estudante_id': partes[2],
            'raw':          qr_text
        }
    return {'raw': qr_text}


def analisar_retangulo(img_gray, x, y, w, h):
    roi = img_gray[y:y+h, x:x+w]
    _, binary = cv2.threshold(roi, 128, 255, cv2.THRESH_BINARY_INV)
    marked = cv2.countNonZero(binary)
    total = roi.size
    return (marked / total * 100) if total else 0


def processar_imagem_json(image_path: str) -> dict:
    """
    • Carrega a imagem, faz crop e converte p/ cinza  
    • Extrai QR e procura simulado_id na tabela (05 ou 09)  
    • Ajusta coordenadas p/ 5º ano (id termina em 05) ou padrão  
    • Lê presença e respostas  
    • Devolve dict no formato solicitado (pronto p/ json.dump)
    """
    # --- Leitura da imagem ---
    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"Não consegui abrir {image_path}")
    img = crop_to_limits(img)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # --- QR code & lookup no banco ---
    qr = extrair_qrcode_info(img)
    filename = os.path.basename(image_path)
    qr['filename'] = filename

    simulado_id = None
    if 'estudante_id' in qr:
        df_av = query_table(SCHEMA, SIMULADO) 
        # print(simulado_id)         # apenas ids terminados em 05/09
        linha = df_av[df_av['estudante_id'] == qr.get('estudante_id')]
        # print(linha)
        if not linha.empty:
            simulado_id = linha['simulado_id'].iloc[0]

        # print(simulado_id)
    qr['simulado_id'] = simulado_id

    # --- Escolha de coordenadas conforme o simulado ---
    print(simulado_id)
    if simulado_id and simulado_id.endswith("05"):
        pres_x, pres_y, pres_rect = presence_x_5_ano, presence_y_5_ano, PRESENCE_RECT_5
        resp_x, resp_y = x_coords_5_ano, y_coords_5_ano
    else:
        pres_x, pres_y, pres_rect = presence_x, presence_y, PRESENCE_RECT
        resp_x, resp_y = x_coords, y_coords

    # --- PRESENÇA ---
    campo_presenca = {}
    w_pres, h_pres = pres_rect
    for idx, (xc, yc) in enumerate(zip(pres_x, pres_y)):
        x0, y0 = xc - w_pres // 2, yc - h_pres // 2
        perc = analisar_retangulo(gray, x0, y0, w_pres, h_pres)
        campo_presenca[f'grupo_{idx}'] = 'Marcado' if perc >= LIMIAR_PREENCHIDO else None

    # --- QUESTÕES ---
    questoes = {}
    total_linhas = len(resp_y)
    for col_idx, xb in enumerate(resp_x):
        for row_idx, yb in enumerate(resp_y):
            qid = f'questao_{col_idx * total_linhas + row_idx + 1}'
            marcados = []
            for opt in range(4):
                px = xb + opt * 100
                perc = analisar_retangulo(gray, px, yb, *RECT_SIZE)
                if perc >= LIMIAR_PREENCHIDO:
                    marcados.append(opt)
            questoes[qid] = marcados or None

    # --- RETORNO JSON-ready ---
    return {
        'filename': filename,
        'qrcode': qr,
        'campo_de_presenca': campo_presenca,
        'questoes_retangulos': questoes
    }

from concurrent.futures import ThreadPoolExecutor, as_completed 


import os
import json
import time
import shutil


def main() -> None:
    start = time.perf_counter()

    # cada diretório imediato dentro de PARENT_DIR é tratado como “região”
    for region in sorted(d for d in os.listdir(PARENT_DIR)
                        if os.path.isdir(os.path.join(PARENT_DIR, d))):
        region_dir = os.path.join(PARENT_DIR, region)

        # determina pastas de imagens
        subdirs = [os.path.join(region_dir, d) for d in os.listdir(region_dir)
                   if os.path.isdir(os.path.join(region_dir, d))]
        img_dirs = subdirs or [region_dir]

        # prepara pasta para imagens com QR não reconhecido
        comp_manual = os.path.join(region_dir, region + MANUAL_COMP_DIR_SUFFIX)
        os.makedirs(comp_manual, exist_ok=True)

        # prepara pasta de saída de JSONs para esta região
        region_json_dir = os.path.join(OUTPUT_JSON_DIR, region.replace(" ", "_"))
        os.makedirs(region_json_dir, exist_ok=True)

        # varre cada diretório de imagens
        for img_dir in img_dirs:
            imagens = [f for f in os.listdir(img_dir)
                       if f.lower().endswith((".jpg", ".jpeg", ".png"))]

            # processamento paralelo
            with ThreadPoolExecutor(max_workers=8) as pool:
                futuros = {
                    pool.submit(processar_imagem_json, os.path.join(img_dir, img)): img
                    for img in imagens
                }
                for fut in as_completed(futuros):
                    img_name = futuros[fut]
                    try:
                        dado = fut.result()
                        if not dado:
                            continue

                        # salva JSON individual
                        base, _ = os.path.splitext(img_name)
                        out_path = os.path.join(region_json_dir, f"{base}.json")
                        with open(out_path, "w", encoding="utf-8") as jf:
                            json.dump(dado, jf, ensure_ascii=False, indent=2)

                        # copia imagem com QR 'Unknown' para conferência manual
                        if dado["qrcode"].get("raw") == "Unknown":
                            src = os.path.join(img_dir, img_name)
                            dst = os.path.join(comp_manual, img_name)
                            shutil.copy(src, dst)

                    except Exception as exc:
                        print(f"[ERRO] {img_name}: {exc}")

        print(f"✓ Região '{region}' concluída — JSONs em '{region_json_dir}'")

    elapsed = time.perf_counter() - start
    print(f"Tempo total de execução: {elapsed:.2f}s")


if __name__ == "__main__":
    main()



