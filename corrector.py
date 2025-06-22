import os
import json
import time
import shutil
import concurrent.futures
import cv2
import numpy as np
import pandas as pd

# ===== Configurações Globais =====
# Diretório pai onde estão as subpastas (ex.: "Simulado 1")
# deixar juntas todas as pastas de computacao manual
PARENT_DIR = "comp_manual"
# Arquivo JSON único de saída
OUTPUT_JSON_FILE = "json_comp/resultado2.json"
# Sufixo para a pasta de compensação manual (quando não achamos estudante_id na planilha)
MANUAL_COMP_DIR_SUFFIX = "_comp_manual"
# Tamanho máximo para recorte
MAX_WIDTH = 2280
MAX_HEIGHT = 3240
# Limiar de preenchimento para considerar "Marcado"
LIMIAR_PREENCHIDO = 30

# Dados para campo de presença (círculos):
# Cada item: [x, y, r, group]
circles_data = [
    [120, 1057, 24, 0],
    [121, 1136, 22, 1],
    [712, 1135, 23, 2],
    [383, 1055, 21, 3],
]

def crop_to_limits(image, max_width=2280, max_height=3240):
    """Recorta centralmente a imagem se ela ultrapassar os limites definidos."""
    h, w = image.shape[:2]
    if w > max_width or h > max_height:
        x_start = (w - max_width) // 2
        y_start = (h - max_height) // 2
        return image[y_start:y_start+max_height, x_start:x_start+max_width]
    return image

def analisar_circulo(image_gray, center, radius, threshold=LIMIAR_PREENCHIDO):
    """Analisa um círculo na imagem e retorna (fill_percentage, status)."""
    _, binary = cv2.threshold(image_gray, 128, 255, cv2.THRESH_BINARY_INV)
    mask = np.zeros_like(binary, dtype=np.uint8)
    cv2.circle(mask, center, radius, 255, -1)
    masked_region = cv2.bitwise_and(binary, binary, mask=mask)
    total_pixels = np.sum(mask == 255)
    marked_pixels = np.sum(masked_region == 255)
    fill_percentage = (marked_pixels / total_pixels * 100) if total_pixels > 0 else 0
    status = "Marcado" if fill_percentage >= threshold else None
    return fill_percentage, status

def analisar_retangulo(image_gray, x, y, width, height, threshold=LIMIAR_PREENCHIDO):
    """Analisa um retângulo na imagem e retorna (fill_percentage, status)."""
    roi = image_gray[y:y+height, x:x+width]
    _, binary = cv2.threshold(roi, 128, 255, cv2.THRESH_BINARY_INV)
    total_pixels = roi.size
    marked_pixels = cv2.countNonZero(binary)
    fill_percentage = (marked_pixels / total_pixels * 100) if total_pixels > 0 else 0
    status = "Marcado" if fill_percentage >= threshold else None
    return fill_percentage, status

def index_to_letter(idx):
    """Converte índice (0,1,2,3) para letras (A, B, C, D)."""
    mapping = {0: "A", 1: "B", 2: "C", 3: "D"}
    return mapping.get(idx, "")

def processar_imagem(image_path, mapping):
    """
    Processa uma única imagem, ignorando a extração do QR:
      - Carrega a imagem e aplica o recorte (crop_to_limits).
      - Obtém o estudante_id a partir do mapeamento (baseado no nome do arquivo).
      - Define "curso_id" e "avaliacao_id" como None.
      - Processa os círculos (campo de presença) e os retângulos adicionais das questões.
    Retorna um dicionário com:
        { "qrcode": {"estudante_id": ..., "curso_id": None, "avaliacao_id": None},
          "campo_de_presenca": {...},
          "questoes_retangulos": {...} }
    """
    image = cv2.imread(image_path)
    if image is None:
        print(f"Erro ao carregar a imagem: {image_path}")
        return None

    image = crop_to_limits(image, MAX_WIDTH, MAX_HEIGHT)
    base_filename = os.path.basename(image_path)
    estudante_id = mapping.get(base_filename, "Unknown")
    # Agora, definindo curso_id e avaliacao_id como None
    qr_data = {"estudante_id": estudante_id, "curso_id": None, "avaliacao_id": None,'filename': base_filename}
    
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Processamento do campo de presença
    resultados = {0: [], 1: [], 2: [], 3: []}
    for (x, y, r, group) in circles_data:
        perc, stat = analisar_circulo(gray, (x, y), r)
        resultados[group].append({"status": stat})
    campo_presenca = {}
    for group in sorted(resultados.keys()):
        found = None
        for item in resultados[group]:
            if item["status"] == "Marcado":
                found = "Marcado"
                break
        campo_presenca[f"{group}"] = found

    # Processamento das questões (44 questões: 11 linhas x 4 colunas)
    x1, x2, x3, x4 = 215, 758, 1298, 1840
    y_coords = [1820 + 85*i for i in range(11)]
    questoes_info = []
    questoes_info += [{"id": f"questao_{i+1}", "x": x1, "y": y_coords[i], "width": 60, "height": 60} for i in range(11)]
    questoes_info += [{"id": f"questao_{i+12}", "x": x2, "y": y_coords[i], "width": 60, "height": 60} for i in range(11)]
    questoes_info += [{"id": f"questao_{i+23}", "x": x3, "y": y_coords[i], "width": 60, "height": 60} for i in range(11)]
    questoes_info += [{"id": f"questao_{i+34}", "x": x4, "y": y_coords[i], "width": 60, "height": 60} for i in range(11)]
    
    questoes_retangulos = {}
    for q in questoes_info:
        qid = q["id"]
        bx, by = q["x"], q["y"]
        marcados = []
        for i in range(4):
            new_x = bx + i * 100
            fperc, stat = analisar_retangulo(gray, new_x, by, 60, 60, threshold=17)
            if stat is not None:
                marcados.append(i)
        questoes_retangulos[qid] = marcados if marcados else None

    return {
        "qrcode": qr_data,
        "campo_de_presenca": campo_presenca,
        "questoes_retangulos": questoes_retangulos
    }

def process_image(img_path, mapping):
    return processar_imagem(img_path, mapping)

def main():
    start_time = time.perf_counter()
    # Carrega o mapeamento a partir da planilha gerada pelo iter.py ("imagens_simulados.xlsx")
    df_map = pd.read_excel("Computacao_manual.xlsx")
    # Cria um dicionário: chave = nome do arquivo, valor = estudante_id (convertido para inteiro e depois para string)
    mapping = {}
    for _, row in df_map.iterrows():
        arquivo = row["filename"]
        try:
            estudante = int(row["estudante_id"])
            mapping[arquivo] = str(estudante)
        except (ValueError, TypeError):
            mapping[arquivo] = "Unknown"

    resultados_finais = []
    
    # Itera sobre todas as subpastas dentro de PARENT_DIR
    for nome_simulado in os.listdir(PARENT_DIR):
        caminho_simulado = os.path.join(PARENT_DIR, nome_simulado)
        if os.path.isdir(caminho_simulado):
            print(f"Processando simulado: {nome_simulado}")
            # Cria a pasta de compensação manual para esse simulado
            comp_manual_folder = os.path.join(caminho_simulado, nome_simulado + MANUAL_COMP_DIR_SUFFIX)
            os.makedirs(comp_manual_folder, exist_ok=True)

            # Obtém os nomes dos arquivos de imagem na subpasta
            arquivos_imagem = [
                f for f in os.listdir(caminho_simulado)
                if os.path.isfile(os.path.join(caminho_simulado, f)) and f.lower().endswith(('.jpg', '.png', '.jpeg'))
            ]
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
                future_to_file = {
                    executor.submit(process_image, os.path.join(caminho_simulado, f), mapping): f
                    for f in arquivos_imagem
                }
                for future in concurrent.futures.as_completed(future_to_file):
                    nome_arq = future_to_file[future]
                    try:
                        res = future.result()
                        if res is not None:
                            resultados_finais.append(res)
                            # Se estudante_id for "Unknown", copia a imagem para a pasta de compensação manual
                            if res.get("qrcode", {}).get("estudante_id", "Unknown") == "Unknown":
                                src = os.path.join(caminho_simulado, nome_arq)
                                dst = os.path.join(comp_manual_folder, nome_arq)
                                shutil.copy(src, dst)
                    except Exception as e:
                        print(f"Erro ao processar {nome_arq}: {e}")
    
    # Salva TODOS os resultados num único arquivo JSON
    with open(OUTPUT_JSON_FILE, "w", encoding="utf-8") as out_file:
        json.dump(resultados_finais, out_file, indent=4, ensure_ascii=False)
    
    end_time = time.perf_counter()
    print("Processamento concluído.")
    print(f"Tempo total: {round(end_time - start_time, 2)}s")

if __name__ == "__main__":
    main()
