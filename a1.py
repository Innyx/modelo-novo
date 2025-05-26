import os
import json
import pandas as pd

# Diretório onde estão os JSONs gerados pela primeira etapa
JSON_DIR = "json_s4_oficial"   # ajuste conforme necessário

def index_to_letter(idx):
    """Converte índice (0,1,2,3) para letra (A, B, C, D)."""
    mapping = {0: "A", 1: "B", 2: "C", 3: "D"}
    return mapping.get(idx, "")

def process_json_files(json_dir):
    """
    Lê todos os arquivos JSON do diretório e cria uma lista de registros para a segunda tabela.
    Cada registro (linha) corresponde à resposta de uma questão de um estudante.
    O JSON esperado é uma lista de dicionários no formato:
    [
       {
           "qrcode": {"estudante_id": "59652", "curso_id": null, "avaliacao_id": null},
           "campo_de_presenca": { "grupo_0": "Marcado", "grupo_1": null, ... },
           "questoes_retangulos": { "questao_1": [3], "questao_2": [3], "questao_3": null, ... }
       },
       ...
    ]
    """
    registros = []
    for file in os.listdir(json_dir):
        if file.lower().endswith(".json"):
            file_path = os.path.join(json_dir, file)
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Se o objeto for uma lista, itera sobre ela; se for dict, usa os valores
                if isinstance(data, list):
                    registros_json = data
                elif isinstance(data, dict):
                    registros_json = list(data.values())
                else:
                    continue
                for reg in registros_json:
                    qrcode = reg.get("qrcode", {})
                    if isinstance(qrcode, dict):
                        curso_id = qrcode.get("curso_id")
                        avaliacao_id = qrcode.get("avaliacao_id")
                        estudante_id = qrcode.get("estudante_id", "")
                    else:
                        curso_id = None
                        avaliacao_id = None
                        estudante_id = ""
                    
                    questoes = reg.get("questoes_retangulos", {})
                    for q_key, alternativas in questoes.items():
                        try:
                            questao_num = int(q_key.split("_")[1])
                        except Exception:
                            continue  # pula se o formato não estiver correto
                        
                        # Define nro_alternativa e alternativa_id conforme regras:
                        if alternativas is None:
                            nro_alternativa = None
                            alternativa_id = str(questao_num)
                        else:
                            if len(alternativas) == 1:
                                nro_alternativa = alternativas[0] + 1  # converte de 0-base para 1-base
                                alternativa_id = f"{questao_num}{index_to_letter(alternativas[0])}"
                            elif len(alternativas) >= 2:
                                # Se houver exatamente duas marcações, retorna "N" sem o símbolo de "+"
                                nro_alternativa = "N"
                                alternativa_id = f"{questao_num}N"
                            else:
                                nro_alternativa = None
                                alternativa_id = f"{questao_num}+{len(alternativas)}"
                        
                        registro_linha = {
                            "data": None,
                            "pergunta_id": None,
                            "resposta_id": None,
                            "respostas_omr_markedtargets": None,
                            "respostas_omr_n_markedtargets": None,
                            "respostas_omr_one_markedtarget": None,
                            "resultado_id": None,
                            "simulado_id": None,
                            "questao_id": questao_num,
                            "nro_alternativa": None,
                            "alternativa_id": alternativa_id,
                            "resultado_resposta_registro_id": None,
                            "curso_id": curso_id,
                            "avaliacao_id": avaliacao_id,
                            "estudante_id": estudante_id,
                            
                        }
                        registros.append(registro_linha)
    return registros

def main():
    registros = process_json_files(JSON_DIR)
    df = pd.DataFrame(registros)
    # Converte 'nro_alternativa' para inteiro se possível (usando Int64 para permitir nulos)
    try:
        df["nro_alternativa"] = pd.to_numeric(df["nro_alternativa"], errors="coerce").astype("Int64")
    except Exception:
        # Caso haja valores não numéricos (ex: "N"), a coluna permanecerá como object
        pass
    # Garante que 'estudante_id' seja string
    df["estudante_id"] = df["estudante_id"].astype(str)
    print(df.head())
    df.to_csv("frr_4.csv", index=False)

if __name__ == "__main__":
    main()
