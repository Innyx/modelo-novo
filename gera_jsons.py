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
PARENT_DIR = os.path.join(BASE_DIR, 'comp_manual')        # pasta com subpastas regionais
OUTPUT_JSON_DIR = os.path.join(BASE_DIR, 'json_comp/resultado.json')  # pasta para salvar os JSONs
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


def processar_imagem(image_path):
    img = cv2.imread(image_path)
    if img is None:
        print(f"Erro ao carregar: {image_path}")
        return None

    img = crop_to_limits(img)
    qr = extrair_qrcode(img)
    filename = os.path.basename(image_path)
    if isinstance(qr, dict):
        qr['filename'] = filename
    else:
        qr = {'raw': qr, 'filename': filename}

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Presença
    pres = {g: None for g in range(len(circles_data))}
    for (x, y, r, grp) in circles_data:
        perc, stat = analisar_circulo(gray, (x, y), r)
        if stat:
            pres[grp] = 'Marcado'

    # Questões: 11 linhas x 4 colunas
    x_coords = [215, 758, 1298, 1840]
    y_coords = [1820 + 85*i for i in range(11)]
    quest = {}
    for col_idx, x_base in enumerate(x_coords):
        for row_idx, y_base in enumerate(y_coords):
            qid = f"questao_{col_idx*11 + row_idx + 1}"
            marked = []
            for opt in range(4):
                px = x_base + opt*100
                p, s = analisar_retangulo(gray, px, y_base, 60, 60, threshold=28)
                if s:
                    marked.append(opt)
            quest[qid] = marked or None

    return { 'qrcode': qr, 'campo_de_presenca': pres, 'questoes_retangulos': quest }


def main():
    start = time.perf_counter()
    regions = [d for d in os.listdir(PARENT_DIR) if os.path.isdir(os.path.join(PARENT_DIR, d))]
    for region in regions:
        region_dir = os.path.join(PARENT_DIR, region)
        # detecta pastas internas com imagens
        subdirs = [os.path.join(region_dir, d) for d in os.listdir(region_dir)
                   if os.path.isdir(os.path.join(region_dir, d))]
        img_dirs = subdirs or [region_dir]

        comp_manual = os.path.join(region_dir, region + MANUAL_COMP_DIR_SUFFIX)
        os.makedirs(comp_manual, exist_ok=True)

        results = {}
        for img_dir in img_dirs:
            imgs = [f for f in os.listdir(img_dir) if f.lower().endswith(('.jpg','.jpeg','.png'))]
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as execs:
                futures = {execs.submit(processar_imagem, os.path.join(img_dir, im)): im for im in imgs}
                for fut in concurrent.futures.as_completed(futures):
                    name = futures[fut]
                    try:
                        data = fut.result()
                        if data:
                            key = json.dumps(data['qrcode'], sort_keys=True)
                            results[key] = data
                            if data['qrcode'].get('raw') == 'Unknown':
                                shutil.copy(os.path.join(img_dir, name), os.path.join(comp_manual, name))
                    except Exception as e:
                        print(f"Erro em {name}: {e}")

        out_file = os.path.join(OUTPUT_JSON_DIR, f"{region.replace(' ','_')}.json")
        with open(out_file, 'w', encoding='utf-8') as jf:
            json.dump(results, jf, indent=4, ensure_ascii=False)
        print(f"Região '{region}' processada. JSON em: {out_file}")

    end = time.perf_counter()
    print(f"Total: {end - start:.2f}s")

if __name__ == '__main__':
    main()
