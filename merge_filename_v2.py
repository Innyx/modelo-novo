import os
import pandas as pd

f_resultados = pd.read_csv("f_resultados_5.csv", sep=';', dtype={"estudante_id": str, 'simulado_id': str, 'avaliacao_id': str, 'curso_id': str, 'estudante_registro_id': str, 'presenca_id': str})
image_links = pd.read_csv("image_links_v2.csv", )

merged = pd.merge(f_resultados, image_links, on="filename", how="inner")
merged['cartao_resposta'] = merged['public_url']

print(merged.columns.to_list())
merged.drop(columns=["public_url", 'filename'], inplace=True)
# merged.rename(columns={"presenca_id_x": "presenca_id", 'cartao_resposta_y': 'cartao_resposta', 'estudante_id_y': 'estudante_id'}, inplace=True)

ordem  = ['resultado_id','simulado_id'	,'curso_id'	,'avaliacao_id'	,'estudante_registro_id',
        'estudante_id'	,'cartao_resposta', 'presenca_id','informacoes_presenca_markedtargets', 
        'informacoes_presenca_n_markedtargets','informacoes_presenca_one_markedtarget'	,'deficiencia_id'
        ,'codigos_deficiencia_markedtargets','codigos_deficiencia_n_markedtargets', 'codigos_deficiencia_one_markedtarget']
merged = merged[ordem]  

merged['resultado_id'] = merged['simulado_id'] + '-' + merged['estudante_id']

merged.to_excel("merged_resultados.xlsx", index=False)






