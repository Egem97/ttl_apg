import pandas as pd
from helpers.get_api import listar_archivos_en_carpeta_compartida
from helpers.get_api import get_access_token
from helpers.helpers import get_download_url_by_name
from helpers.config import load_config

config = load_config()

def load_data_cosecha_campo():
    print("📊 Cargando datos de Transformación Materia Prima...")
    try:
        data = listar_archivos_en_carpeta_compartida(
            drive_id=config['dataset']['cosecha']['drive_id'], 
            item_id=config['dataset']['cosecha']['item_id'],
            access_token=get_access_token()
        )
        url_excel_1 = get_download_url_by_name(data, "COSECHA CAMPO.parquet")
        df = pd.read_parquet(url_excel_1)
        
        # Procesamiento básico de fechas si existe la columna
        if "FECHA" in df.columns:
            df["FECHA"] = pd.to_datetime(df["FECHA"], errors='coerce')
            
            # Agregar Numero de Semana
            df['SEMANA'] = df["FECHA"].dt.isocalendar().week
            # Corrección: Si es Diciembre y la semana es 1, cambiar a 52
            df.loc[(df["FECHA"].dt.month == 12) & (df['SEMANA'] == 1), 'SEMANA'] = 52
            
            # Agregar Nombre del Mes en Español
            meses_es = {
                1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio",
                7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
            }
            df['MES'] = df["FECHA"].dt.month.map(meses_es)
            
            df["FECHA"] = df["FECHA"].dt.strftime('%d/%m/%Y')
        
        netsuite_columns = {
            "SAN PEDRO": ["EXCELLENCE FRUIT SAC",5,"SAN PEDRO : SP ALMACEN MATERIA PRIMA",16,"SPE"],
            "SAN JOSE": ["EXCELLENCE FRUIT SAC",5,"SAN JOSE I : SJ ALMACEN MATERIA PRIMA",6,"SJO"],
            "SAN JOSE II": ["EXCELLENCE FRUIT SAC",5,"SAN JOSE I : SJ ALMACEN MATERIA PRIMA",6,"SJO"],
            "LICAPA": ["QBERRIES SAC",3,"QBERRIES : QB ALMACEN MATERIA PRIMA",61,"QB1"],
            "GAP BERRIES": ["GAP BERRIES SAC",15,"GAP : GA ALMACEN MATERIA PRIMA",34,"GAP"],
            "LAS BRISAS": ["TARA FARM SAC",6,"TARA : TR ALMACEN MATERIA PRIMA",74,"TAR"],
            "EL POTRERO": ["CANYON BERRIES SAC",14,"CANYON : CY ALMACEN MATERIA PRIMA",25,"CAN"],
            "LA COLINA": ["BIG BERRIES SAC",12,"BIG : BB ALMACEN MATERIA PRIMA",52,"BIG"],
        }
        
        # Mapeo de columnas
        df['SUBSIDIARIA'] = df['FUNDO'].map(lambda x: netsuite_columns.get(x, [None]*5)[0])
        df['COD_SUBSIDIARIA'] = df['FUNDO'].map(lambda x: netsuite_columns.get(x, [None]*5)[1])
        df['ALMACEN'] = df['FUNDO'].map(lambda x: netsuite_columns.get(x, [None]*5)[2])
        df['COD_ALMACEN'] = df['FUNDO'].map(lambda x: netsuite_columns.get(x, [None]*5)[3])
        df['COD_FUNDO'] = df['FUNDO'].map(lambda x: netsuite_columns.get(x, [None]*5)[4])
        filtro_big = (df["FUNDO"] == "LA COLINA") & (df['LOTE'].isin(["LOTE 003","LOTE 004","LOTE 005","LOTE 010"]))
        df.loc[filtro_big, ['SUBSIDIARIA', 'COD_SUBSIDIARIA', 'ALMACEN','COD_ALMACEN','COD_FUNDO']] = [
            "GOLDEN BERRIES SAC", 
            13, 
            "GO ALMACEN MATERIA PRIMA",
            44,
            "GOL"
        ]
        df['LOTE'] = df['LOTE'].str.replace("-1", "I")
        # Creación columna PARCELA: COD_FUNDO - M0{MODULO} - {LOTE_5_DIGITOS}
        df['PARCELA'] = (
            df['COD_FUNDO'].fillna('') + 
            '-M0' + df['MODULO'].astype(str).str.extract(r'(\d+)')[0].fillna('') + 
            '-' + 
            df['LOTE'].str[5:].str.zfill(5)
        )
        
        
        df['KILOS NETOS'] = df['KILOS BRUTOS'] - df['DESCARTE']
        df = df[[
            "MES","SEMANA","FECHA","FUNDO","MODULO","LOTE","PARCELA","KILOS BRUTOS","DESCARTE","KILOS NETOS","SUBSIDIARIA","COD_SUBSIDIARIA","ALMACEN","COD_ALMACEN"
        ]]
        return df
    except Exception as e:
        print(f"Error cargando datos: {e}")
        return pd.DataFrame()