import cv2
import numpy as np
import json
import os
import concurrent.futures
import time
import shutil
from pyzbar.pyzbar import decode

# --- Diretórios base ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.join(BASE_DIR, 'ultimos')        # pasta com subpastas regionais
OUTPUT_JSON_DIR = os.path.join(BASE_DIR, 'json_ultimo')  # pasta para salvar os JSONs
MANUAL_COMP_DIR_SUFFIX = '_comp_manual'                # sufixo para pasta compensação manual

# --- Configurações globais ---
LIMIAR_PREENCHIDO = 30
MAX_WIDTH = 2280
MAX_HEIGHT = 3240

# Dados para o campo de presença (círculos): [x, y, radius, group]
circles_data = [
    [120, 1057, 24, 0],
    [121, 1136, 22, 1],
    [712, 1135, 23, 2],
    [383, 1055, 21, 3],
]

# Garante que o diretório de saída exista
os.makedirs(OUTPUT_JSON_DIR, exist_ok=True)


def crop_to_limits(image, max_width=MAX_WIDTH, max_height=MAX_HEIGHT):
    h, w = image.shape[:2]
    if w > max_width or h > max_height:
        x_start = (w - max_width) // 2
        y_start = (h - max_height) // 2
        return image[y_start:y_start+max_height, x_start:x_start+max_width]
    return image


def extrair_qrcode(image):
    roi = image[1:470, 1:470]
    detector = cv2.QRCodeDetector()
    data, points, _ = detector.detectAndDecode(roi)
    if data:
        parts = data.strip().split('-')
        if len(parts) == 3 and all(part.isdigit() for part in parts):
            return {"curso_id": parts[0], "avaliacao_id": parts[1], "estudante_id": parts[2]}
    return "Unknown"


def analisar_circulo(img_gray, center, radius, threshold=LIMIAR_PREENCHIDO):
    _, binary = cv2.threshold(img_gray, 128, 255, cv2.THRESH_BINARY_INV)
    mask = np.zeros_like(binary)
    cv2.circle(mask, center, radius, 255, -1)
    masked = cv2.bitwise_and(binary, binary, mask=mask)
    total = np.count_nonzero(mask)
    marked = np.count_nonzero(masked)
    perc = (marked / total * 100) if total else 0
    status = "Marcado" if perc >= threshold else None
    return perc, status


def analisar_retangulo(img_gray, x, y, width, height, threshold=LIMIAR_PREENCHIDO):
    roi = img_gray[y:y+height, x:x+width]
    _, binary = cv2.threshold(roi, 128, 255, cv2.THRESH_BINARY_INV)
    total = roi.size
    marked = cv2.countNonZero(binary)
    perc = (marked / total * 100) if total else 0
    status = "Marcado" if perc >= threshold else None
    return perc, status


def processar_imagem(image_path: str) -> dict:
    # 1) Carrega e valida imagem
    img = cv2.imread(image_path)
    if img is None:
        print(f"Erro ao carregar: {image_path}")
        return {
            "qrcode": {
                "estudante_id": "",
                "avaliacao_id": "",
                "path": image_path
            },
            "campo_de_presenca": {
                "presente": None,
                "deficiente": None,
                "ausente": None,
                "transferido": None
            },
            "respostas": {}
        }

    # 2) Pré-processa e extrai QR
    img = crop_to_limits(img)
    qr_raw = extrair_qrcode(img)
    qr_data = qr_raw if isinstance(qr_raw, dict) else {}
    estudante_id = qr_data.get("estudante_id", "")
    avaliacao_id = qr_data.get("avaliacao_id", "")

    # 3) Converte para grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # 4) Analisa presença
    label_map = {0: "presente", 1: "deficiente", 2: "ausente", 3: "transferido"}
    campo_de_presenca = { label: None for label in label_map.values() }
    for (x, y, r, grp) in circles_data:
        _, marcado = analisar_circulo(gray, (x, y), r)
        if marcado:
            campo_de_presenca[label_map[grp]] = "Marcado"

    # 5) Analisa respostas (1…44)
    x_coords = [215, 758, 1298, 1840]
    y_coords = [1820 + 85 * i for i in range(11)]
    respostas = {}
    for ci, x_base in enumerate(x_coords):
        for ri, y_base in enumerate(y_coords):
            qnum = ci * len(y_coords) + ri + 1
            marcadas = []
            for opt in range(4):
                px = x_base + opt * 100
                _, sel = analisar_retangulo(gray, px, y_base, 60, 60, threshold=28)
                if sel:
                    marcadas.append(opt)
            respostas[str(qnum)] = marcadas

    # 6) Retorna sem 'link_do_cartao' — será preenchido no main.py
    return {
        "qrcode": {
            "estudante_id": estudante_id,
            "avaliacao_id": avaliacao_id,
            "path": image_path
        },
        "campo_de_presenca": campo_de_presenca,
        "respostas": respostas
    }

