import pandas as pd 


df_comp = pd.read_csv("f_resultados_5.csv")

df_links = pd.read_csv("image_links_v2.csv")

merged_df = pd.merge(df_comp, df_links, on="filename", how="inner")

merged_df['cartao_resposta'] = merged_df['public_url']
merged_df.drop(columns=['public_url', 'filename'], inplace=True)
# Remove linhas onde estudante_id está vazio ou NaN
merged_df = merged_df[merged_df['estudante_id'].notna() & (merged_df['estudante_id'] != '')]

merged_df.to_excel("merged_resultados_links.xlsx", index=False)