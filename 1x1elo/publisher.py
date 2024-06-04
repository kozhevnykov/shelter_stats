import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime


def results_to_sheet(df, worksheet=1):
    scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/spreadsheets',
             'https://www.googleapis.com/auth/drive.file','https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name('../shelter-elo-f89a18b95341.json', scope)
    client = gspread.authorize(creds)
    sheet = client.open('UA PUB haxball statistics')
    sheet_instance = sheet.get_worksheet(worksheet)
    sheet_instance.clear()
    sheet_instance.insert_rows([[str(f'last update: {datetime.now()}')]] + [df.columns.values.tolist()] + df.values.tolist(), 1)
    sheet_instance.format("A2:I2", {
        "backgroundColor": {
            "red": 0.6,
            "green": 0.1,
            "blue": 0.0
        },
        "horizontalAlignment": "CENTER",
        "textFormat": {
            "foregroundColor": {
                "red": 1.0,
                "green": 1.0,
                "blue": 1.0
            },
            "fontSize": 10,
            "bold": True
        }
    })
    print(f'ELO worksheet {worksheet} updated')