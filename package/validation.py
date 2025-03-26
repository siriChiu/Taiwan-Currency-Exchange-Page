import base64
import json
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import configparser

class GSManager:
    def __init__(self, config_file, credential_file):
        self.scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        self.cfg_dict = self.load_config(config_file)
        self.credentials = self.load_credentials(credential_file)
        self.client = gspread.authorize(self.credentials)

    def load_config(self, config_file):
        """Load configuration from an .ini file."""
        config = configparser.ConfigParser()
        config.read(config_file, encoding='utf-8')
        if 'user_info' not in config:
            raise ValueError('Missing user_info section in the config file')
        return {section: dict(config.items(section)) for section in config.sections()}

    def load_credentials(self, credential_file):
        """Load and decode credentials from a base64 encoded file."""
        with open(credential_file, 'r') as f:
            credential_coded = f.read()
        credential = base64.b64decode(credential_coded).decode('utf-8')
        return ServiceAccountCredentials.from_json_keyfile_dict(json.loads(credential), self.scope)

    def get_sheet(self, spreadsheet_url):
        """Open a Google Sheet by URL."""
        try:
            return self.client.open_by_url(spreadsheet_url).sheet1
        except gspread.exceptions.APIError:
            raise ValueError('Please share the Google Sheet with the client email in the credential.json file')

    def find_company_owner_info(self, sheet, company, owner):
        """Find and return the company owner information."""
        column_data = sheet.get_all_values()
        companies = sheet.col_values(1)
        owners = sheet.col_values(2)

        company_idx = [i for i, x in enumerate(companies) if x == company]
        owner_idx = [i for i, x in enumerate(owners) if x == owner]

        if len(company_idx) == 0 or len(owner_idx) == 0:
            raise ValueError('Not found')
        elif len(company_idx) > 1 or len(owner_idx) > 1:
            raise ValueError('Multiple found')
        elif company_idx[0] != owner_idx[0]:
            raise ValueError('Not match')

        return column_data[0], column_data[company_idx[0]]

    def display_info(self, column_header, info):
        """Display the company owner information."""
        for i in range(len(column_header)):
            print(f'{column_header[i]}: {info[i]}')

def check():
    cfg_file = "./config.ini"
    credential_file = "./credential"
    spreadsheet_url_coded = "aHR0cHM6Ly9kb2NzLmdvb2dsZS5jb20vc3ByZWFkc2hlZXRzL2QvMTVxUEJ0Wl9xWkN3WDNCdHJPandZMkhxRjBPOHktRTBURlBYNGozZXlmYkEvZWRpdD91c3A9c2hhcmluZw=="
    spreadsheet_url = base64.b64decode(spreadsheet_url_coded).decode('utf-8')

    manager = GSManager(cfg_file, credential_file)
    sheet = manager.get_sheet(spreadsheet_url)

    owner = manager.cfg_dict['user_info']['owner']
    company = manager.cfg_dict['user_info']['company']
    header, info = manager.find_company_owner_info(sheet, company, owner)
    # manager.display_info(header, info)

    status_idx = header.index('Status')
    status = info[status_idx]

    return status

# if __name__ == "__main__":
#     check()
