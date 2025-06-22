import os
import re

# --- Configurações ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.join(BASE_DIR, 'ddzs')  # Pasta raiz com subpastas de regiões
TARGET_EXTS = ('.jpg', '.jpeg', '.png')

def renomea_pastas():
    """
    Renomeia as pastas dentro de 'simulado5' para remover caracteres especiais.
    """
    for root, dirs, _ in os.walk(PARENT_DIR):
        for dir_name in dirs:
            new_dir_name = dir_name.replace('ª', ' ')
            if new_dir_name != dir_name:
                os.rename(os.path.join(root, dir_name), os.path.join(root, new_dir_name))

if __name__ == "__main__":
    renomea_pastas()
    print("Renomeação de pastas concluída.")                