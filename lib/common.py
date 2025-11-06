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
from pathlib import Path
import pandas as pd
import json

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
                #print(e)
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


# -------------- PRETTY PRINTS --------------------

# Assumes df has datetime index!
def format_df_for_print(df):
    dfplot = df.copy()
    dfplot = dfplot.round(2)
    dfplot.index = dfplot.index.strftime('%Y-%m-%d')
    return dfplot