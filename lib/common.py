from pathlib import Path
import pandas as pd
import json
from datetime import datetime, timedelta

def last_day_of_previous_month(date):
    first_day_of_current_month = date.replace(day=1)
    last_day_of_prev_month = first_day_of_current_month - timedelta(days=1)
    return last_day_of_prev_month

def define_end_date(YEAR: int):
    today = datetime.now()
    #today_strf = today.strftime('%Y-%m-%d')
    if today.year > YEAR: # full year of a past year
        end_date = f"{YEAR}-12-31"
    else: # current year till last day of previous month
        #end_date = today_strf
        end_date = last_day_of_previous_month(today).strftime('%Y-%m-%d')
    return end_date

def define_today_date():
    today = datetime.now()
    today_date_str = today.strftime("%Y-%m-%d")
    today_month_str = today.strftime("%Y-%m")

    return today_date_str, today_month_str, today

def define_prev_month_holdings(df_m_cashflow):
    prev_month_liquidity = float(df_m_cashflow.iloc[-1].liquidity)
    prev_month_investments = float(df_m_cashflow.iloc[-1].investments)

    return prev_month_liquidity, prev_month_investments


# ------------------ LOAD DATA -------------------------
def load_init_holdings(path : Path, YEAR : int):
    try:
        with open(f"{path}/{YEAR}/{YEAR}_init.json") as file:
            data = file.read()
        init_holdings = json.loads(data)
        return init_holdings
    except Exception as e:
        #print(e)
        return None

def load_data(typedata : str, path : Path, YEAR : int):
    if typedata not in ["cashflow", "investments"]:
        raise TypeDataError(f"Type data is not either cashflow or investments")
    else:
        basepath = f"{path}/{YEAR}/{typedata}/"
        dfl = list()
        for i in range(1,13):
            try:
                filepath = f"{path}/{YEAR}/{typedata}/{YEAR}-{i:0=2}_{typedata}.csv"
                df = pd.read_csv(filepath, skipinitialspace=True, na_filter=False)
                df.columns = df.columns.str.strip() # remove whitespaces from columns
                # Strip whitespace from Date column
                if 'Date' in df.columns:
                    df['Date'] = df['Date'].astype(str).str.strip()
                df.Category = df.Category.str.strip()
                df.Subcategory = df.Subcategory.str.strip()
                df.Type = df.Type.str.strip()
                if typedata == "cashflow":
                    df.Coin = df.Coin.str.strip()
                elif typedata == "investments":
                    df.Symbol = df.Symbol.str.strip()

                if not(df.empty):
                    dfl.append(df)
            except Exception as e:
                print(e)
                continue

        df_year = pd.concat(dfl)
        df_year['Date'] = pd.to_datetime(df_year['Date'])
        df_year.set_index('Date',inplace=True)
        return df_year

def found_cache_files(cache_dir : str, symbol, currency):
    try:
        cache_path = Path(cache_dir)
        
        # Check if directory exists and is accessible
        if not cache_path.exists():
            return False
        if not cache_path.is_dir():
            return False
            
        file_to_check = cache_path / f"cache_{symbol}-{currency}.csv"
        return file_to_check.exists() and file_to_check.is_file()
        
    except (OSError, PermissionError):
        return False

# ------------------ HELPER FUNCTIONS FOR FLASK WRAPPER -------------
def load_config():
    """Load and return config.json"""
    try:
        with open('config.json', 'r') as f:
            return json.load(f)
    except Exception as e:
        return None

def load_mappings():
    """Load and return mappings.json"""
    try:
        with open('mappings.json', 'r') as f:
            return json.load(f)
    except Exception as e:
        return None

def expand_transfer_templates(config):
    """Expand Transfer subcategories templates with actual provider names from mappings.json"""
    try:
        mappings = load_mappings()
        if mappings is None:
            return config

        # Expand for cashflow
        if 'cashflow' in config and 'Subcategory' in config['cashflow'] and 'Transfer' in config['cashflow']['Subcategory']:
            transfer_templates = config['cashflow']['Subcategory']['Transfer']
            expanded = []

            for template in transfer_templates:
                # Check if template contains placeholder
                if '{' in template and '}' in template:
                    # Extract placeholder: "To{Acc1}" -> "Acc1"
                    start = template.index('{')
                    end = template.index('}')
                    placeholder = template[start+1:end]

                    # Get mapped value
                    if placeholder in mappings:
                        # Replace placeholder with actual value
                        expanded_value = template[:start] + mappings[placeholder] + template[end+1:]
                        expanded.append(expanded_value)
                    else:
                        # Placeholder not found in mappings, keep as-is
                        expanded.append(template)
                else:
                    # No placeholder (e.g., "Invest"), keep as-is
                    expanded.append(template)

            # Update config with expanded values
            config['cashflow']['Subcategory']['Transfer'] = expanded

        return config
    except Exception as e:
        # If expansion fails, return original config
        return config

def get_db_csv_path(data_type, year, month, data_path=None):
    """Construct CSV file path for cashflow or investments"""
    if data_path is None:
        raise ValueError("Data path not set. Please initialize the backend first.")
    
    if data_type == "cashflow":
        return f"{data_path}/{year}/cashflow/{year}-{month:02d}_cashflow.csv"
    elif data_type == "investments":
        return f"{data_path}/{year}/investments/{year}-{month:02d}_investments.csv"
    else:
        raise ValueError(f"Invalid data_type: {data_type}. Must be 'cashflow' or 'investments'")

def determine_month_from_date(date_str):
    """Extract month from date string (YYYY-MM-DD format)"""
    try:
        # Strip whitespace from date string
        date_str = date_str.strip()
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        return date_obj.month
    except ValueError:
        raise ValueError(f"Invalid date format: {date_str}. Expected YYYY-MM-DD")

def validate_data(data_type, category, subcategory, coin=None, symbol=None):
    """Validate category and subcategory against config.json"""
    config = load_config()
    if config is None:
        return False, "Config file not found"

    # Expand Transfer templates
    config = expand_transfer_templates(config)

    # Get the appropriate section based on data_type
    if data_type not in ["cashflow", "investments"]:
        return False, f"Invalid data_type: {data_type}. Must be 'cashflow' or 'investments'"

    data_config = config.get(data_type, {})
    if not data_config:
        return False, f"Config section for {data_type} not found"

    # Validate category
    valid_categories = data_config.get("Category", [])
    if category not in valid_categories:
        return False, f"Invalid category. Must be one of {valid_categories}"

    # Validate subcategory
    subcategories = data_config.get("Subcategory", {})
    if category in subcategories:
        if subcategory not in subcategories[category]:
            return False, f"Invalid subcategory for {category}. Must be one of {subcategories[category]}"

    # Validate coin (for cashflow)
    if data_type == "cashflow" and coin is not None:
        valid_coins = data_config.get("Coin", [])
        if coin not in valid_coins:
            return False, f"Invalid coin. Must be one of {valid_coins}"

    return True, "Valid"

# preserves stable order of lists a and b to merge
def merge_lists_unique_into_set(a, b):
    merged = [x for x in a if x not in b] + b
    return merged