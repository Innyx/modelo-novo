import pandas as pd 


df_comp = pd.read_excel("comp.xlsx")

df_links = pd.read_csv("image_links.csv")

merged_df = pd.merge(df_comp, df_links, on="filename", how="inner")

merged_df.to_excel("merged_comp_links.xlsx", index=False)