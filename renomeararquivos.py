import os
import pandas as pd 
# --- Configurações ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.join(BASE_DIR, 'contagem')  # Pasta raiz com subpastas de regiões
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
    resumo = {"old_name": [], "new_name": []}
    df = pd.DataFrame()
    
    counter = 105993  # Inicia a contagem a partir de 72048
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
                resumo["old_name"].append(filename)
                resumo["new_name"].append(new_name)
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

    # Salva o resumo em um DataFrame e exporta para CSV
    df = pd.DataFrame(resumo)
    df.to_csv('renomeacao_resultados_v2.csv', sep=';', index=False)
    print(f"Renomeação concluída. Total de arquivos: {counter-1}")

if __name__ == '__main__':
    main()
