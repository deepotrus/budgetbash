import sys        # for passing port number argument
import threading  # For shutting down server
import os
import signal
import json
from pathlib import Path
from datetime import datetime

from tabulate import tabulate # for pretty printing finance dataframes
import pandas as pd

from flask import Flask, request, jsonify

from lib import FinCashflow, FinInvestments
from lib.common import format_df_for_print

import plotext as plt
plt.date_form('d/m/Y')

# Class to manage the deepfinance backend
class DeepManager:
    def __init__(self):
        self.finCashflow : FinCashflow = None
        self.finInvestments : FinInvestments = None

        self.nw_global : pd.DataFrame = None

    def initialize(self, year, data_path):
        self.finCashflow = FinCashflow(data_path, year)
        self.finInvestments = FinInvestments(data_path, year)
        
        self.finCashflow.run()
        self.finInvestments.run()
        pass

    def get_cashflow_info(self):
        df = self.finCashflow.df_m_cashflow
        df_m_cashflow = df.iloc[1:] # Exclude the first row which has '-' in some columns

        df_expenses_year = self.finCashflow.calc_expenses()
        df_expenses_year_by_category = df_expenses_year.groupby('Category')['Qty'].sum().reset_index(name='Expenses')
        df_expenses_year_by_category = df_expenses_year_by_category.sort_values('Expenses', ascending=False)
        df_expenses_year_by_category['Percentage'] = ((df_expenses_year_by_category['Expenses'] / df_expenses_year_by_category['Expenses'].sum()) * 100).round(2)

        df_incomes_year = self.finCashflow.calc_incomes()
        df_incomes_year_by_category = df_incomes_year.groupby('Category')['Qty'].sum().reset_index(name="Incomes")
        df_incomes_year_by_category = df_incomes_year_by_category.sort_values('Incomes', ascending=False)
        df_incomes_year_by_category['Percentage'] = ((df_incomes_year_by_category['Incomes'] / df_incomes_year_by_category['Incomes'].sum()) * 100).round(2)

        return df_m_cashflow, df_expenses_year_by_category, df_incomes_year_by_category

    def calc_global_nw(self):
        # Retrieve data from classes
        row_today_cashflow = self.finCashflow.df_last_month_cashflow
        df_today_holdings = self.finInvestments.df_today_holdings
        df_m_cashflow = self.finCashflow.df_m_cashflow
        df_year_holdings = self.finInvestments.df_year_holdings

        # Calculate networth
        nw_current_month = pd.concat([row_today_cashflow['liquidity'], df_today_holdings['Total']], axis=1, keys=['liquidity', 'investments'])
        nw_current_month['networth'] = nw_current_month.liquidity + nw_current_month.investments

        nw = pd.concat([df_m_cashflow['liquidity'], df_year_holdings['Total']], axis=1, keys=['liquidity', 'investments'])
        nw['networth'] = nw.liquidity + nw.investments

        nw_global = pd.concat([nw, nw_current_month])
        nw_global["nwch"] = (nw_global.networth - nw_global.networth.shift(1) )
        nw_global["ch%"] = (nw_global.networth - nw_global.networth.shift(1) )/ nw_global.networth

        self.nw_global = nw_global
        return nw_global

    # Today Networth status
    def get_nw_status(self):
        return self.nw_global.iloc[-1].round(2)
    
    def get_all_balances(self):
        all_balances = self.finCashflow.get_all_balances()

        return all_balances

# Initialize flask app and wrapper
app = Flask(__name__)
deepManager = DeepManager() # init wrapper with year and data_path

# Global variable to store data_path (set during initialization)
DATA_PATH = None

# Helper functions
def load_config():
    """Load and return config.json"""
    try:
        with open('config.json', 'r') as f:
            return json.load(f)
    except Exception as e:
        return None

def get_csv_path(data_type, year, month, data_path=None):
    """Construct CSV file path for cashflow or investments"""
    if data_path is None:
        data_path = DATA_PATH
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


@app.route("/", methods=['GET'])
def root():
    return "Deepfinance Backend OK"

@app.route("/shutdown", methods=['GET'])
def shutdown():
    def shutdown_server():
        os.kill(os.getpid(), signal.SIGTERM)
    
    threading.Timer(1, shutdown_server).start()  # Wait 1 second before killing
    return "Server is shutting down..."

@app.route("/initialize", methods=['POST'])
def initialize():
    global DATA_PATH
    year = int(request.form.get('year'))
    data_path = request.form.get('data_path')
    DATA_PATH = data_path

    try:
        deepManager.initialize(year, data_path)
    except Exception as e:
        return f"Error initializing: {e}"

    return f"Succesfully initialized {year} data from path {data_path}."

@app.route("/plot", methods=["GET"])
def plot():
    try:
        nw_global = deepManager.calc_global_nw()

        dates = plt.datetimes_to_string(nw_global.index)
        liquidity = list(nw_global.liquidity)
        investments = list(nw_global.investments)
        networth = liquidity + investments

        plt.theme("pro")
        plt.plotsize(60, 20)
        plt.simple_stacked_bar(dates, [investments, liquidity], labels = ["investments", "liquidity"], width=80, title="Networth")
        plt.title("Networth")
        plt.xlabel("Date")
        plt.ylabel("Euro")
        plt.show()
        plt.clear_figure()  # Clear the previous plot
        print()
        df_m_cashflow, df_expenses_year, df_incomes_year = deepManager.get_cashflow_info()
        #dates = plt.datetimes_to_string(df_m_cashflow.index)
        #incomes = list(df_m_cashflow.incomes)
        #liabilities = list(df_m_cashflow.liabilities.abs())
        #plt.simple_multiple_bar(dates, [incomes, liabilities], width = 50, labels = ["incomes", "liabilities"])
        #plt.title("Cashflow")
        #plt.show()
        #plt.clear_figure()  # Clear the previous plot

        #print(df_expenses_year)

        categories = list(df_expenses_year["Category"])
        total_expenses_by_category = list(df_expenses_year["Expenses"])
        percentage = list(df_expenses_year["Percentage"])

        plt.simple_bar(categories, total_expenses_by_category, width=60, title = "Yearly Expenses", color="orange")
        #plt.title("Expenses by
        plt.show()
        plt.clear_figure()  # Clear the previous plot
        print()

        #print(df_incomes_year)
        categories = list(df_incomes_year["Category"])
        total_incomes_by_category = list(df_incomes_year["Incomes"])
        percentage = list(df_incomes_year["Percentage"])

        plt.simple_bar(categories, total_incomes_by_category, width=60, title = "Yearly Incomes", color="cyan")
        plt.show()

        return "Done"
    except Exception as e:
        return f"{e}"

@app.route("/dashboard_status", methods=['GET'])
def dashboard_status():
    try:
        deepManager.calc_global_nw()
        nw_status = deepManager.get_nw_status()
        all_balances = deepManager.get_all_balances()

        print(all_balances)

        liquidity = nw_status['liquidity']
        investments = nw_status['investments']
        networth = nw_status['networth']
        nwch = nw_status['nwch']
        pct_ch = nw_status['ch%']

        return jsonify({
          "liquidity": liquidity,
          "investments": investments,
          "networth": networth,
          "nwch": nwch,
          "pct_ch": pct_ch,
          "status": "success"
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        })

@app.route("/add_data", methods=['POST'])
def add_data():
    """Add a row to cashflow or investments CSV"""
    try:
        data_type = request.form.get('data_type')  # 'cashflow' or 'investments'
        year = int(request.form.get('year'))
        date = request.form.get('date')
        type_field = request.form.get('type')  # Bank/account type
        qty = float(request.form.get('qty'))
        category = request.form.get('category')
        subcategory = request.form.get('subcategory')
        description = request.form.get('description', '')
        
        # Determine month from date
        month = determine_month_from_date(date)
        
        # Get coin or symbol based on data_type
        coin = None
        symbol = None
        if data_type == "cashflow":
            coin = request.form.get('coin')
            if not coin:
                return "Error: Coin is required for cashflow data"
        elif data_type == "investments":
            symbol = request.form.get('symbol')
            if not symbol:
                return "Error: Symbol is required for investments data"
        else:
            return f"Error: Invalid data_type: {data_type}. Must be 'cashflow' or 'investments'"
        
        # Validate data
        is_valid, error_msg = validate_data(data_type, category, subcategory, coin, symbol)
        if not is_valid:
            return f"Error: {error_msg}"
        
        # Get CSV path
        csv_path = get_csv_path(data_type, year, month)
        csv_file = Path(csv_path)
        
        # Load config to get columns
        config = load_config()
        if config is None:
            return "Error: Config file not found"
        
        # Prepare new row
        if data_type == "cashflow":
            new_row = {
                'Date': date,
                'Type': type_field,
                'Coin': coin,
                'Qty': qty,
                'Category': category,
                'Subcategory': subcategory,
                'Description': description
            }
            columns = ['Date', 'Type', 'Coin', 'Qty', 'Category', 'Subcategory', 'Description']
        else:  # investments
            new_row = {
                'Date': date,
                'Type': type_field,
                'Symbol': symbol,
                'Qty': qty,
                'Category': category,
                'Subcategory': subcategory,
                'Description': description
            }
            columns = ['Date', 'Type', 'Symbol', 'Qty', 'Category', 'Subcategory', 'Description']
        
        # Load existing data or create new DataFrame
        if csv_file.exists():
            df = pd.read_csv(csv_path, skipinitialspace=True, na_filter=False)
            df.columns = df.columns.str.strip()
            # Strip whitespace from Date column if it exists
            if 'Date' in df.columns:
                df['Date'] = df['Date'].astype(str).str.strip()
            # Append new row
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        else:
            # Create directory if it doesn't exist
            csv_file.parent.mkdir(parents=True, exist_ok=True)
            # For new file, create DataFrame directly with the new row
            df = pd.DataFrame([new_row])
        
        # Save to CSV
        df.to_csv(csv_path, index=False)
        
        return f"Successfully added: {date}, {type_field}, {qty}, {category}, {subcategory}"
    except Exception as e:
        return f"Error adding data: {str(e)}"

@app.route("/delete_row", methods=['POST'])
def delete_row():
    """Delete a row from cashflow or investments CSV"""
    try:
        data_type = request.form.get('data_type')
        year = int(request.form.get('year'))
        month = int(request.form.get('month'))
        line_number = int(request.form.get('line_number'))
        
        # Get CSV path
        csv_path = get_csv_path(data_type, year, month)
        
        if not Path(csv_path).exists():
            return "Error: CSV file does not exist"
        
        # Load CSV
        df = pd.read_csv(csv_path, skipinitialspace=True, na_filter=False)
        df.columns = df.columns.str.strip()
        # Strip whitespace from Date column if it exists
        if 'Date' in df.columns:
            df['Date'] = df['Date'].astype(str).str.strip()
        
        if line_number < 0 or line_number >= len(df):
            return "Error: Invalid line number"
            
        # Get row data before deleting for confirmation
        row_data = df.iloc[line_number]
        
        # Delete the row
        df = df.drop(df.index[line_number])
        df.to_csv(csv_path, index=False)
        
        return f"Successfully deleted row: {line_number}"
    except Exception as e:
        return f"Error deleting row: {str(e)}"

@app.route("/view_database", methods=['GET'])
def view_database():
    """View cashflow or investments data"""
    try:
        data_type = request.args.get('data_type')
        year = int(request.args.get('year'))
        month = int(request.args.get('month'))
        
        # Get CSV path
        csv_path = get_csv_path(data_type, year, month)
        
        if not Path(csv_path).exists():
            return "Error: CSV file does not exist"
        
        # Load CSV
        df = pd.read_csv(csv_path, skipinitialspace=True, na_filter=False)
        df.columns = df.columns.str.strip()
        # Strip whitespace from Date column if it exists
        if 'Date' in df.columns:
            df['Date'] = df['Date'].astype(str).str.strip()
        
        if df.empty:
            return "Database is empty"
        
        # Format table
        table = tabulate(df, headers='keys', tablefmt='psql', showindex=True)
        return f"{table}"
    except Exception as e:
        return f"Error viewing database: {str(e)}"

@app.route("/get_row_data", methods=['GET'])
def get_row_data():
    """Get specific row data for confirmation"""
    try:
        data_type = request.args.get('data_type')
        year = int(request.args.get('year'))
        month = int(request.args.get('month'))
        line_number = int(request.args.get('line_number'))
        
        # Get CSV path
        csv_path = get_csv_path(data_type, year, month)
        
        if not Path(csv_path).exists():
            return "Error: CSV file does not exist"
        
        # Load CSV
        df = pd.read_csv(csv_path, skipinitialspace=True, na_filter=False)
        df.columns = df.columns.str.strip()
        # Strip whitespace from Date column if it exists
        if 'Date' in df.columns:
            df['Date'] = df['Date'].astype(str).str.strip()
        
        if line_number < 0 or line_number >= len(df):
            return "Error: Invalid line number"
        
        row_data = df.iloc[line_number]
        
        # Format row data as string
        if data_type == "cashflow":
            return f"{row_data['Date']}, {row_data['Type']}, {row_data['Coin']}, {row_data['Qty']}, {row_data['Category']}, {row_data['Subcategory']}"
        else:  # investments
            return f"{row_data['Date']}, {row_data['Type']}, {row_data['Symbol']}, {row_data['Qty']}, {row_data['Category']}, {row_data['Subcategory']}"
    except Exception as e:
        return f"Error getting row data: {str(e)}"

@app.route("/get_row_count", methods=['GET'])
def get_row_count():
    """Get number of rows in CSV"""
    try:
        data_type = request.args.get('data_type')
        year = int(request.args.get('year'))
        month = int(request.args.get('month'))
        
        # Get CSV path
        csv_path = get_csv_path(data_type, year, month)
        
        if not Path(csv_path).exists():
            return "0"
        
        # Load CSV
        df = pd.read_csv(csv_path, skipinitialspace=True, na_filter=False)
        
        return str(len(df))
    except Exception as e:
        return f"Error getting row count: {str(e)}"

@app.route("/get_subcategories", methods=['GET'])
def get_subcategories():
    """Get subcategories for a category"""
    try:
        category = request.args.get('category')
        data_type = request.args.get('data_type', 'cashflow')  # Default to cashflow for backward compatibility
        
        config = load_config()
        
        if config is None:
            return ""
        
        # Get the appropriate section based on data_type
        if data_type not in ["cashflow", "investments"]:
            return ""
        
        data_config = config.get(data_type, {})
        subcategories = data_config.get("Subcategory", {})
        
        if category in subcategories:
            return ','.join(subcategories[category])
        else:
            return ""
    except Exception as e:
        return f"Error getting subcategories: {str(e)}"

if __name__ == "__main__":
    app.run(debug=True, port=sys.argv[1])