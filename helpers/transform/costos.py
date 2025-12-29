import pandas as pd
from helpers.helpers import *

def mayor_analitico_opex_transform(df,agrupador_costos_df):

    df = df[df["Cuenta"].notna()]
    agrupador_costos_df = agrupador_costos_df.rename(columns={"ITEM":"Descripción Proyecto"})
    agrupador_costos_df["Descripción Proyecto"] = agrupador_costos_df["Descripción Proyecto"].str.strip()
    agrupador_costos_df["Descripción Proyecto"] = agrupador_costos_df["Descripción Proyecto"].str.upper()
    
    df[["Cod Cta. Contable",'Nombre Cta. Contable']] = df['Nombre Cta. Contable'].apply(split_if_colon_at_3).apply(pd.Series)
    var_category = ['Cuenta', 'Nombre Cta. Contable','Numero Operacion', 'Documento Referencia', 'Glosa','Voucher Contable','Código Cliente/Proveedor', 'Razón Social',
       'IDCCOSTO ', 'Doc. Origen Moneda', 'Descripción Moneda','Cod. Proyecto', 'Descripción Proyecto', 'Cod. Actividad','Descripción Actividad', 'Cod Cta. Contable',]
    
    df["Dólares Cargo"] = df["Dólares Cargo"] - df["Dólares Abono"] 
    #############################3

    df["Cod Cta. Contable"] = df["Cod Cta. Contable"].astype(str)
    df["Cod. Actividad"] = df["Cod. Actividad"].astype(str)
    df["Cod. Proyecto"] = df["Cod. Proyecto"].astype(str)
    df["Doc. Origen Moneda"] = df["Doc. Origen Moneda"].astype(str)
    df["Código Cliente/Proveedor"] = df["Código Cliente/Proveedor"].astype(str)
    df["Numero Operacion"] = df["Numero Operacion"].astype(str)
    df["Voucher Contable"] = df["Voucher Contable"].astype(str)
    df["Cuenta"] = df["Cuenta"].astype(str)
    for col in var_category:
        df[col] = df[col].str.strip()
    df["Descripción Actividad"] = df["Descripción Actividad"].fillna("NO ESPECIFICADO")
    df["Descripción Proyecto"] = df["Descripción Proyecto"].fillna("NO ESPECIFICADO")
    df["Descripción Moneda"] = df["Descripción Moneda"].fillna("-")
    df["Razón Social"] = df["Razón Social"].fillna("NO ESPECIFICADO")
    df["Glosa"] = df["Glosa"].fillna("NO ESPECIFICADO")
    df["Descripción Proyecto"] = df["Descripción Proyecto"].replace("", "OTROS_")
    df["Cod Cta. Contable"] = df["Cod Cta. Contable"].fillna("XX").replace("None", "XX")
    #manalitico_df["Cod Cta. Contable"] = manalitico_df["Cod Cta. Contable"]
    

    df["Fecha"] = pd.to_datetime(df["Fecha"])
    df["AÑO"] = df["Fecha"].dt.year
    df["MES"] = df["Fecha"].dt.month
    
    df["MES"] = df["MES"].apply(get_month_name)
    
    df["Cod Cta. Contable"] = df["Cod Cta. Contable"].replace("XX", "OTROS")
    ##### CONDICIONES MAYOR ANALITICO
    
    df["COD_DESCARTE"] = df["Cod. Proyecto"].fillna("PP000").str[:-3]
    df["COD_CUENTA_DESCARTE"] = df["Cuenta"].str[:2]
    df["COD_VAUCHER"] = df["Voucher Contable"].str[:3]
    df = df[df["COD_DESCARTE"]=="PO"]
    df = df[df["COD_CUENTA_DESCARTE"]!="95"]
    df = df[df["COD_VAUCHER"]!="020"]
    df = df.drop(columns=["COD_DESCARTE","COD_CUENTA_DESCARTE","COD_VAUCHER"])
    df = df[df["Descripción Proyecto"]!="INTERESES FINANCIEROS"]
    df["Descripción Proyecto"] = df["Descripción Proyecto"].replace({
        
        "SERVICIOS TI" : "SERVICIOS T.I.",
        "AGUA":"AGUA POTABLE",
        "AGUA PARA BEBER":"AGUA PARA BEBER + VASOS DESCARTABLES",
        "BUS PACKING (PERSONAL)":"BUS (PERSONAL)",
        "ENERGÍA ELÉCTRICA / GAS":"ENERGÍA ELÉCTRICA / PETRÓLEO",
        "UTENSILIOS PRODUCCIÓN":"UTENSILIOS DE PRODUCCIÓN",
        "MATERIAL ESCRITORIO":"MATERIAL DE ESCRITORIO",
        "REMUNERACIONES RR.HH":"REMUNERACIONES RRHH.",
        "PETRÓLEO / GASOLINA":"GLP / GASOLINA"

    })
    
    df = pd.merge(df,agrupador_costos_df,on="Descripción Proyecto",how="left")
    #print(df)
    df["AGRUPADOR"] = df["AGRUPADOR"].fillna("IMPREVISTOS")
    df["Descripción Proyecto"] = df["Descripción Proyecto"].str.upper()
    df["SUB AGRUPADOR"] = df["SUB AGRUPADOR"].fillna("IMPREVISTOS")
    return df

def presupuesto_packing_transform(df):
    
    var_category = ['EMPRESA', 'SEDE', 'AGRUPADOR', 'CUENTA', 'SUBCUENTA','TIPO PRESUPUESTO', 'ITEM','NOMBRE', 'VALIDAR_BLANCO', 'ITEM_CORREGIDO']
    for col in var_category:
        df[col] = df[col].str.strip()
    df["NOMBRE"] = df["NOMBRE"].fillna("XXXX")
    df["ITEM_CORREGIDO"] = df["ITEM_CORREGIDO"].replace("SEVICIOS T.I.","SERVICIOS T.I.")
    df["PERIODO"] = df["PERIODO"].astype(str)
    df["Mes"] = df["MES"].map(change_month_TEXT)
    df = df.rename(columns={"AÑO":"Año"})
    return df

def agrupador_costos_transform(df):
    df["ITEM"] = df["ITEM"].str.upper()
    df["AGRUPADOR"] = df["AGRUPADOR"].str.upper()
    df["SUB AGRUPADOR"] = df["SUB AGRUPADOR"].str.upper()
    return df
