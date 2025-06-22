import os
import csv
import pandas as pd 

# Caminho para a pasta principal
base_dir = 'contagem'
# Caminho para o CSV
csv_path = 'renomeacao_resultados1.csv'

# Lê os nomes antigos do CSV
old_names = set()
with open(csv_path, newline='', encoding='utf-8') as csvfile:
    reader = csv.DictReader(csvfile, delimiter=';')
    for row in reader:
        old_names.add(row['old_name'])

# print(f'Encontrados {old_names} nomes antigos no CSV.')
# --- Configurações ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.join(BASE_DIR, 'contagem')  # Pasta raiz com subpastas de regiões
TARGET_EXTS = ('.jpg', '.jpeg', '.png')

def renomea_pastas():
    for root, dirs, _ in os.walk(PARENT_DIR):
        for dir_name in dirs:
            new_dir_name = dir_name.replace('ª', ' ').replace('º', ' ').replace('°', ' ').replace('º', ' ')
            if new_dir_name != dir_name:
                os.rename(os.path.join(root, dir_name), os.path.join(root, new_dir_name))
renomea_pastas()

# Percorre as regiões
for region in sorted(os.listdir(PARENT_DIR)):
    region_dir = os.path.join(PARENT_DIR, region)
    if not os.path.isdir(region_dir):
        continue
    # Verifica subpastas de imagens dentro da região
    subdirs = [os.path.join(region_dir, d) for d in sorted(os.listdir(region_dir))
                if os.path.isdir(os.path.join(region_dir, d))]
    target_dirs = subdirs or [region_dir]
    # Renomeia em cada diretório alvo
    for folder in target_dirs:
        # Lista todos os arquivos de imagem ordenados
        files = [f for f in sorted(os.listdir(folder))
                    if os.path.isfile(os.path.join(folder, f)) and f.lower().endswith(TARGET_EXTS)]
        for filename in files:
            name, ext = os.path.splitext(filename)
            src = os.path.join(folder, filename)
            if filename in old_names:
                print(f"Excluindo arquivo já processado: {filename}")
                os.remove(src)
                continue
        
            