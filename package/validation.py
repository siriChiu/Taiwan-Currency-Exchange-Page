import base64
import json
import gspread
import platform
import datetime as dt
from pathlib import Path
from oauth2client.service_account import ServiceAccountCredentials
import configparser
try:
    import streamlit as st
    _ST_AVAILABLE = True
except ImportError:
    _ST_AVAILABLE = False


SPREADSHEET_URL_CODED = "aHR0cHM6Ly9kb2NzLmdvb2dsZS5jb20vc3ByZWFkc2hlZXRzL2QvMTVxUEJ0Wl9xWkN3WDNCdHJPandZMkhxRjBPOHktRTBURlBYNGozZXlmYkEvZWRpdD91c3A9c2hhcmluZw=="


def _normalize_header(header):
    return header.strip().lower().replace(" ", "_")


def _get_value(row_dict, key, default=""):
    return row_dict.get(key, default).strip() if isinstance(row_dict.get(key, default), str) else row_dict.get(key, default)


def _normalize_date(value):
    if not value:
        return ""

    if not isinstance(value, str):
        value = str(value)

    cleaned = value.strip()
    if not cleaned:
        return ""

    date_formats = [
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%m/%d/%Y",
        "%m/%d/%y",
        "%Y.%m.%d",
        "%m-%d-%Y",
        "%m-%d-%y",
    ]
    for date_format in date_formats:
        try:
            return dt.datetime.strptime(cleaned, date_format).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return cleaned


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

    def get_rows(self, sheet):
        values = sheet.get_all_values()
        if not values:
            raise ValueError("Google Sheet is empty")

        header = [_normalize_header(column) for column in values[0]]
        rows = []
        for row in values[1:]:
            padded_row = row + [""] * (len(header) - len(row))
            rows.append(dict(zip(header, padded_row)))
        return rows

    def find_subscription_row(self, sheet, company, owner, ssid=""):
        """Find and return the matching subscription row."""
        rows = self.get_rows(sheet)
        matches = []

        for row in rows:
            row_company = _get_value(row, "company")
            row_owner = _get_value(row, "owner")
            row_ssid = _get_value(row, "ssid")

            company_matched = row_company == company
            owner_matched = row_owner == owner
            ssid_matched = not ssid or not row_ssid or row_ssid == ssid

            if company_matched and owner_matched and ssid_matched:
                matches.append(row)

        if len(matches) == 0:
            raise ValueError("Not found")
        if len(matches) > 1:
            raise ValueError("Multiple found")
        return matches[0]

    def get_subscription_info(self, sheet, company, owner, ssid=""):
        row = self.find_subscription_row(sheet, company, owner, ssid)
        return {
            "company": _get_value(row, "company"),
            "owner": _get_value(row, "owner"),
            "ssid": _get_value(row, "ssid"),
            "service_type": _get_value(row, "service_type", "monthly"),
            "registered_date": _normalize_date(_get_value(row, "initial_date")),
            "start_date": _normalize_date(_get_value(row, "start_date")),
            "end_date": _normalize_date(_get_value(row, "end_date")),
            "alert_date": _normalize_date(_get_value(row, "alert_date")),
            "expiration_date": _normalize_date(_get_value(row, "stop_date") or _get_value(row, "end_date")),
            "stop_date": _normalize_date(_get_value(row, "stop_date")),
            "status": _get_value(row, "status", "active").lower(),
            "paid": _get_value(row, "paid"),
            "source": "google_sheet",
        }

    def display_info(self, column_header, info):
        """Display the company owner information."""
        for i in range(len(column_header)):
            print(f'{column_header[i]}: {info[i]}')


def _get_credential_b64() -> str:
    """Return base64-encoded credential string. Prefers st.secrets, falls back to file."""
    if _ST_AVAILABLE:
        try:
            return st.secrets["google_sheets"]["credential_b64"]
        except (KeyError, Exception):
            pass
    _app_dir = Path.home() / ".currency_app"
    credential_file = str(_app_dir / "credential") if (_app_dir / "credential").exists() else "./credential"
    with open(credential_file, 'r') as f:
        return f.read().strip()


def _get_operator_info() -> dict:
    """Return {'company', 'owner', 'ssid'} from st.secrets or config.ini."""
    if _ST_AVAILABLE:
        try:
            sec = st.secrets["operator"]
            return {
                "company": sec["company"],
                "owner": sec["owner"],
                "ssid": sec.get("ssid", "") or platform.node(),
            }
        except (KeyError, Exception):
            pass
    _app_dir = Path.home() / ".currency_app"
    cfg_file = str(_app_dir / "config.ini") if (_app_dir / "config.ini").exists() else "./config.ini"
    config = configparser.ConfigParser()
    config.read(cfg_file, encoding='utf-8')
    if 'user_info' not in config:
        raise ValueError('Missing operator info: add [operator] to st.secrets or create config.ini')
    info = dict(config.items('user_info'))
    return {
        "company": info['company'],
        "owner": info['owner'],
        "ssid": info.get('ssid', '') or platform.node(),
    }


def _build_google_sheet_client():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    credential_coded = _get_credential_b64()
    credentials = ServiceAccountCredentials.from_json_keyfile_dict(
        json.loads(base64.b64decode(credential_coded).decode('utf-8')), scope
    )
    client = gspread.authorize(credentials)
    return scope, credentials, client


def write_config(company: str, owner: str, ssid: str) -> None:
    """Write company/owner/ssid to ~/.currency_app/config.ini"""
    _app_dir = Path.home() / ".currency_app"
    _app_dir.mkdir(parents=True, exist_ok=True)
    config = configparser.ConfigParser()
    config['user_info'] = {'company': company, 'owner': owner, 'ssid': ssid}
    with open(_app_dir / "config.ini", 'w', encoding='utf-8') as f:
        config.write(f)


def update_ssid_in_sheet(company: str, owner: str, ssid: str) -> None:
    """Find the Google Sheet row matching company+owner and write ssid if blank."""
    spreadsheet_url = base64.b64decode(SPREADSHEET_URL_CODED).decode('utf-8')

    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    credential_coded = _get_credential_b64()
    credentials = ServiceAccountCredentials.from_json_keyfile_dict(
        json.loads(base64.b64decode(credential_coded).decode('utf-8')), scope
    )
    client = gspread.authorize(credentials)
    sheet = client.open_by_url(spreadsheet_url).sheet1

    values = sheet.get_all_values()
    if not values:
        raise ValueError("Google Sheet is empty")

    header = [_normalize_header(h) for h in values[0]]
    if 'ssid' not in header or 'company' not in header or 'owner' not in header:
        raise ValueError("Google Sheet 缺少必要欄位 (company / owner / ssid)")

    ssid_col = header.index('ssid')
    company_col = header.index('company')
    owner_col = header.index('owner')

    for row_num, row in enumerate(values[1:], start=2):
        padded = row + [''] * max(len(header) - len(row), 0)
        if padded[company_col].strip() == company and padded[owner_col].strip() == owner:
            existing_ssid = padded[ssid_col].strip() if ssid_col < len(padded) else ''
            if not existing_ssid:
                sheet.update_cell(row_num, ssid_col + 1, ssid)
            return

    raise ValueError(f"找不到符合的訂閱記錄：{company} / {owner}")


def get_subscription_info():
    operator = _get_operator_info()
    return get_subscription_info_for_user(
        company=operator["company"],
        owner=operator["owner"],
        ssid=operator["ssid"],
    )


def get_subscription_info_for_user(company: str, owner: str, ssid: str = ""):
    spreadsheet_url = base64.b64decode(SPREADSHEET_URL_CODED).decode('utf-8')
    scope, credentials, client = _build_google_sheet_client()
    try:
        sheet = client.open_by_url(spreadsheet_url).sheet1
    except gspread.exceptions.APIError:
        raise ValueError('Please share the Google Sheet with the service account email')

    manager = GSManager.__new__(GSManager)
    manager.scope = scope
    manager.credentials = credentials
    manager.client = client
    return manager.get_subscription_info(sheet, company, owner, ssid)


def check():
    return get_subscription_info()["status"]

# if __name__ == "__main__":
#     check()
