import os

# --- Configurações ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.join(BASE_DIR, 's4_oficial_35.847_arq')  # Pasta raiz com subpastas de regiões
TARGET_EXTS = ('.jpg', '.jpeg', '.png')


def renomea_pastas():
    """
    Renomeia as pastas dentro de 'simulado3' para remover caracteres especiais.
    """
    for root, dirs, _ in os.walk(PARENT_DIR):
        for dir_name in dirs:
            new_dir_name = dir_name.replace('ª', ' ').replace('º', ' ').replace('°', ' ').replace('º', ' ')
            if new_dir_name != dir_name:
                os.rename(os.path.join(root, dir_name), os.path.join(root, new_dir_name))


def main():
    """
    Renomeia todos os arquivos de imagem em todas as subpastas de 'simulado3'
    para uma sequência numérica contínua de 1 até N.
    """
    renomea_pastas()
    counter = 36201  # Inicia a contagem a partir de 36201
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
                new_name = f"{counter}{ext.lower()}"
                src = os.path.join(folder, filename)
                dst = os.path.join(folder, new_name)
                # Verifica se o destino já existe
                while os.path.exists(dst):
                    counter += 1
                    new_name = f"{counter}{ext.lower()}"
                    dst = os.path.join(folder, new_name)
                if src != dst:
                    os.rename(src, dst)
                counter += 1

            caracters = ['ª', 'º', '°', 'º']
            for char in caracters:
                if char in folder:
                    folder = folder.replace(char, ' ')    
    print(f"Renomeação concluída. Total de arquivos: {counter-1}")

if __name__ == '__main__':
    main()
