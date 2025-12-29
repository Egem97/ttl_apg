import pandas as pd
from helpers.helpers import *

def reporte_produccion_transform(df):
    def transform_kg_text_rp_packing(text_num):
        if len(text_num) > 4 and (text_num[1] == "." or text_num[2] == "."):
            text_num = text_num.replace(".", "")
        else:
            text_num = text_num.replace(",", ".")
        return text_num.replace(",",".")
    df["Kg Procesados"] = df["Kg Procesados"].apply(transform_kg_text_rp_packing)
    df["Kg Procesados"] = df["Kg Procesados"].astype(float)
   
    #df["Kg Procesados"] = df["Kg Procesados"].str.replace(",", ".", regex=False).astype(float)
    
    #df["Kg Exportables"] = df["Kg Exportables"].apply(limpiar_kg_exportables)
    df["%. Kg Exportables"] = df["%. Kg Exportables"].str.replace(",", ".", regex=False).astype(float)
    
    df["Kg Exportables"] = df["Kg Procesados"].astype(float) * (df["%. Kg Exportables"].astype(float)/100)
    df["TOTAL CAJAS EXPORTADAS"] = df["TOTAL CAJAS EXPORTADAS"].astype(int)
    
    # Convertir columnas numéricas
    for col in ["Kg Descarte","% Descarte","Kg Sobre Peso","% Sobre Peso","Kg Merma","% Merma","% Rendimiento MP",]:
        df[col] = df[col].str.replace(",", ".", regex=False).astype(float)
    
    #
    df["Fecha de cosecha"] = pd.to_datetime(df["Fecha de cosecha"],dayfirst=True).dt.strftime('%Y-%m-%d')
    df["Fecha de proceso"] = pd.to_datetime(df["Fecha de proceso"],dayfirst=True).dt.strftime('%Y-%m-%d')
    
    return df

def reporte_produccion_costos_transform(df):
    df = reporte_produccion_transform(df)
    df = df[[
        "Semana","Fecha de cosecha","Fecha de proceso","Turno Proceso","Empresa","Tipo","Fundo","Variedad","Kg Procesados","Kg Descarte",
        "% Descarte","Kg Sobre Peso","% Sobre Peso","Kg Merma","% Merma","% Rendimiento MP","Kg Exportables","%. Kg Exportables","TOTAL CAJAS EXPORTADAS"
    ]]
    df = df.rename(columns={
            "Semana":"SEMANA","Fecha de proceso":"FECHA", 'Variedad':"VARIEDAD",'Fundo':"FUNDO",'Empresa':"EMPRESA",
            "Kg Exportables":"KG_EXPORTABLES","Kg Descarte":"KG_DESCARTE","Kg Procesados":"KG_PROCESADOS"
        })
    
    df = df.groupby(["SEMANA","FECHA","VARIEDAD","FUNDO","EMPRESA"])[["KG_EXPORTABLES","KG_DESCARTE","KG_PROCESADOS"]].sum().reset_index()
    df["FECHA_"] = pd.to_datetime(df["FECHA"])
    df["FECHA"] = pd.to_datetime(df["FECHA"]).dt.date
    df["Año"] = df["FECHA_"].dt.year
    df["Mes"] = df["FECHA_"].dt.month
    #df["Semana"] = df["FECHA_"].dt.isocalendar().week
    df = df.drop(columns=["FECHA_"])
    return df


def kg_presupuesto_packing_transform(df):
    
    df = df[df["SEMANA"].notna()]
    df["MES"] = df["MES"].replace(change_month)	
    
    df["AÑO"] = df["AÑO"].astype(int).astype(str)
    df["AÑO"] = df["AÑO"].str.strip()
    df = df.rename(columns={
        "KG PROCESADOS - PPTO":"KG PPTO PROCESADOS ",
        "KG EXPORTADOS - PPTO" :"KG PPTO EXPORTADOS"
        }
    )
    
    return df

def phl_pt_transform(df):
    print("--------------------------------")
    #print(df["F. PRODUCCION"].unique())
    df = df[df["F. PRODUCCION"].notna()]
    df["DESCRIPCION DEL PRODUCTO"] = df["DESCRIPCION DEL PRODUCTO"].str.strip()
    #df["F. PRODUCCION"] = pd.to_datetime(df["F. PRODUCCION"],dayfirst=True).dt.date
    return df