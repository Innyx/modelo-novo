import os
import json
import time
import shutil
import concurrent.futures
import cv2
import numpy as np
import pandas as pd

f_resultados = pd.read_csv("f_resultados_sim03_comp_manual.csv")

comp_manaual = pd.read_excel("Computação Manual.xlsx", dtype={"estudante_id": str})

merged = pd.merge(f_resultados, comp_manaual, on="estudante_id", how="inner")


merged.drop(columns=["cartao_resposta_x", 'Assessor(a)', 'presenca_id_y', 'filename_x', 'STATUS', 'filename_y'], inplace=True)
merged.rename(columns={"presenca_id_x": "presenca_id", 'cartao_resposta_y': 'cartao_resposta'}, inplace=True)

print(merged.columns.to_list())
merged.to_excel("merged_resultados.xlsx", index=False)


