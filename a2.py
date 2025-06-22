import os
import json
import pandas as pd

# Diretório onde estão os JSONs gerados pela primeira etapa
JSON_DIR = "reprocessament_9_ano"   # ajuste conforme necessário


def map_presenca(campo_presenca):
    """
    Mapeia o campo de presença para gerar presenca_id conforme as regras:
      - Se nenhum grupo marcado: 0
      - Se mais de um grupo marcado: 99
      - Se apenas um grupo marcado:
           grupo_0 → 2
           grupo_1 → 4
           grupo_2 → 3
           grupo_3 → 5
    """
    marked = [k for k, v in campo_presenca.items() if v == "Marcado"]
    
    if len(marked) == 0:
        return 0
    elif len(marked) > 1:
        return 99
    else:
        mapping = {"0": 2, "1": 4, "2": 5, "3": 3}
        return mapping.get(marked[0][-1], 0)

def process_json_files(json_dir):
    """
    Lê todos os arquivos JSON do diretório e junta os registros em uma lista.
    Cada registro é criado com as seguintes colunas:
        - resultado_id: None
        - simulado_id: ""
        - curso_id, avaliacao_id, estudante_id: extraídos dos dados do QR code;
        - estudante_registro_id: ""
        - cartao_resposta: ""
        - presenca_id: mapeado a partir do campo de presença;
        - as demais colunas informacionais são definidas como None.
        
    O JSON pode estar no formato de uma lista de registros.
    """
    registros = []
    for file in os.listdir(json_dir):
        if file.lower().endswith(".json"):
            file_path = os.path.join(json_dir, file)
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                registro = data
                # # Se o objeto for uma lista, itera sobre ela; se for dict, usa os valores
                # if isinstance(data, list):
                #     registros_json = data
                # elif isinstance(data, dict):
                #     registros_json = list(data.values())
                # else:
                #     continue
                
                # for registro in registros_json:
                qrcode = registro.get("qrcode", {})
                if isinstance(qrcode, dict):
                    curso_id = qrcode.get("curso_id", "")
                    avaliacao_id = qrcode.get("avaliacao_id", "")
                    estudante_id = qrcode.get("estudante_id", "")
                    filename = registro.get("filename", "")
                else:
                    curso_id = ""
                    avaliacao_id = ""
                    estudante_id = ""
                    filename = ""
                
                campo_presenca = registro.get("campo_de_presenca", {})
                presenca_id = map_presenca(campo_presenca)
                
                novo_registro = {
                    "resultado_id": None,
                    "simulado_id": None,
                    "curso_id": curso_id,
                    "avaliacao_id": avaliacao_id,
                    "estudante_registro_id": "",
                    "estudante_id": estudante_id,
                    "cartao_resposta": "",
                    "presenca_id": presenca_id,
                    "informacoes_presenca_markedtargets": None,
                    "informacoes_presenca_n_markedtargets": None,
                    "informacoes_presenca_one_markedtarget": None,
                    "deficiencia_id": None,
                    "codigos_deficiencia_markedtargets": None,
                    "codigos_deficiencia_n_markedtargets": None,
                    "codigos_deficiencia_one_markedtarget": None,
                    "filename": filename
                }
                registros.append(novo_registro)
    return registros

def main():
    registros = process_json_files(JSON_DIR)
    df = pd.DataFrame(registros)
    print(df.head())
    df.to_csv("f_resultados_5_v3.csv", index=False)

if __name__ == "__main__":
    main()
