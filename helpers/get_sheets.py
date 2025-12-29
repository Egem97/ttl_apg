import re
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Paso 1: Autenticación
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]
creds = ServiceAccountCredentials.from_json_keyfile_name("nifty-might-269005-cd303aaaa33f.json", scope)
client = gspread.authorize(creds)

def read_sheet(key_sheet, sheet_name):
    try:
        spreadsheet = client.open_by_key(key_sheet)
        sheet = spreadsheet.worksheet(sheet_name)
        data = sheet.get_all_values()

        return data
    except Exception as e:
        return key_sheet, f"Error: {str(e)}"