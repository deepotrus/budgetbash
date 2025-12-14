import sys        # for passing port number argument
import threading  # For shutting down server
import os
import signal
import json
from pathlib import Path
from datetime import datetime

import pandas as pd
from flask import Flask, request, jsonify
from tabulate import tabulate # for pretty printing dataframes

# Budget Lib
from lib import FinCashflow, FinInvestments
from lib import BudgetPlotter
from lib import FlaskWrapper

# Helper functions for flask wrapper
from lib.common import load_config, load_mappings, expand_transfer_templates, get_db_csv_path, determine_month_from_date, validate_data

# Terminal plot
import plotext as plt
plt.date_form('d/m/Y')

# Initialize flask app and wrapper
app = Flask(__name__)
deepManager = FlaskWrapper()

DATA_PATH = None # set during initialization

import logging
logging.getLogger('werkzeug').setLevel(logging.WARNING)  # Set flask logging level

# ------------ FLASK ROUTES ------------------

@app.route("/", methods=['GET'])
def root():
    return "BudgetBash Backend OK"

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

@app.route("/investments", methods=["GET"])
def investments():
    df_holdings, df_today_holdings = deepManager.get_investments_info()
    print(df_holdings)
    print(df_today_holdings)
    return "Done"

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

        expenses_dict = df_expenses_year.set_index('Category')['Expenses'].to_dict()
        budgetPlotter = BudgetPlotter()
        budgetPlotter.draw_pie_chart(expenses_dict, width=50, height=30)

        #plt.simple_bar(categories, total_expenses_by_category, width=60, title = "Yearly Expenses", color="orange")
        #plt.show()
        #plt.clear_figure()  # Clear the previous plot
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

@app.route("/get_expenses_categories", methods=["GET"])
def get_expenses_categories():
    try:
        month = int(request.args.get('month'))
        
        if month < 1 or month > 12:
            return jsonify({"error": f"Invalid month {month}"}), 400
        
        df_expenses_month = deepManager.finCashflow.calc_expenses(month=month)
        
        if df_expenses_month.empty:
            return jsonify({"categories": []})
        
        categories = sorted(df_expenses_month['Category'].unique().tolist())
        return jsonify({"categories": categories})
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/plot_month", methods=["GET"])
def plot_month():
    try:
        # Get parameters from query string
        month = int(request.args.get('month'))
        category = request.args.get('category')

        if month < 1 or month > 12:
            return f"Error: Invalid month {month}. Must be between 1 and 12"

        # Get monthly expense data using existing method
        df_expenses_month = deepManager.finCashflow.calc_expenses(month=month)

        df_expenses_month_by_category = df_expenses_month.groupby('Category')['Qty'].sum().reset_index(name='Expenses')
        df_expenses_month_by_category = df_expenses_month_by_category.sort_values('Expenses', ascending=False)

        # Prepare data for plotting
        categories = list(df_expenses_month_by_category["Category"])
        total_expenses_by_category = list(df_expenses_month_by_category["Expenses"])

        # Configure plotext
        plt.theme("pro")
        plt.plotsize(60, 20)

        # Create bar chart with orange color
        plt.simple_bar(categories, total_expenses_by_category, width=60,
                      title=f"{deepManager.finCashflow.YEAR}-{month:02d} Expenses", color="orange")
        plt.show()
        plt.clear_figure()

        # Filter data for selected category
        df_filtered = df_expenses_month[df_expenses_month['Category'] == category]

        if df_filtered.empty:
            return "No data found for category: {category}"

        # Group by subcategory
        df_subcat = df_filtered.groupby('Subcategory')['Qty'].sum().reset_index(name='Total')
        df_subcat = df_subcat.sort_values('Total', ascending=False)

        if len(df_subcat) == 0:
            return "No subcategories found for {category}"

        # Convert to dictionary for pie chart
        subcat_dict = df_subcat.set_index('Subcategory')['Total'].to_dict()

        # Create pie chart using BudgetPlotter
        budgetPlotter = BudgetPlotter()
        budgetPlotter.draw_pie_chart(subcat_dict, width=50, height=30)

        return ""
    except ValueError as e:
        return f"Error: Invalid month parameter - {str(e)}"
    except AttributeError as e:
        return f"Error: Database not initialized. Please initialize the database first."
    except Exception as e:
        return f"Error: {str(e)}"

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
          "all_balances": all_balances,
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
        csv_path = get_db_csv_path(data_type, year, month, DATA_PATH)
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
        csv_path = get_db_csv_path(data_type, year, month, DATA_PATH)
        
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
        csv_path = get_db_csv_path(data_type, year, month, DATA_PATH)
        
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
        csv_path = get_db_csv_path(data_type, year, month, DATA_PATH)
        
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
        csv_path = get_db_csv_path(data_type, year, month, DATA_PATH)
        
        if not Path(csv_path).exists():
            return "0"
        
        # Load CSV
        df = pd.read_csv(csv_path, skipinitialspace=True, na_filter=False)
        
        return str(len(df))
    except Exception as e:
        return f"Error getting row count: {str(e)}"

@app.route("/get_categories_for_month", methods=['GET'])
def get_categories_for_month():
    """Get list of categories with expenses for a specific month"""
    try:
        month = int(request.args.get('month'))

        # Validate month
        if month < 1 or month > 12:
            return jsonify({"error": "Invalid month"}), 400

        # Get monthly expense data
        df_expenses_month = deepManager.finCashflow.calc_expenses(month=month)

        # Check if there's data
        if df_expenses_month.empty:
            return jsonify({"categories": []})

        # Get unique categories and sort
        categories = df_expenses_month['Category'].unique().tolist()
        categories.sort()

        # Add "All Categories" as first option
        categories.insert(0, "All Categories")

        return jsonify({"categories": categories})

    except ValueError as e:
        return jsonify({"error": f"Invalid month parameter - {str(e)}"}), 400
    except AttributeError as e:
        return jsonify({"error": "Database not initialized"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/get_subcategories", methods=['GET'])
def get_subcategories():
    """Get subcategories for a category"""
    try:
        category = request.args.get('category')
        data_type = request.args.get('data_type', 'cashflow')  # Default to cashflow for backward compatibility

        config = load_config()

        if config is None:
            return ""

        # Expand Transfer templates
        config = expand_transfer_templates(config)

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

#$ curl -X GET _routes to view all routes
@app.route("/_routes")
def routes():
    lines = []
    for rule in app.url_map.iter_rules():
        if str(rule).startswith("/static/"):
            continue
        methods = ",".join(sorted(rule.methods - {"HEAD","OPTIONS"}))
        lines.append(f"{methods:10s} {rule}")
    return "\n".join(lines)


if __name__ == "__main__":
    app.run(debug=True, port=sys.argv[1])