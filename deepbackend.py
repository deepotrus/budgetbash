import sys        # for passing port number argument
import threading  # For shutting down server
import os
import signal

from tabulate import tabulate # for pretty printing finance dataframes
import pandas as pd

from flask import Flask, request, jsonify

from lib import FinCashflow, FinInvestments
from lib.common import format_df_for_print

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

# Initialize flask app and wrapper
app = Flask(__name__)
deepManager = DeepManager()

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
    year = int(request.form.get('year'))
    data_path = request.form.get('data_path')

    try:
        deepManager.initialize(year, data_path)
    except Exception as e:
        return f"Error initializing: {e}"

    return f"Succesfully initialized {year} data from path {data_path}."

@app.route("/dashboard_status", methods=['GET'])
def dashboard_status():
    try:
        deepManager.calc_global_nw()
        nw_status = deepManager.get_nw_status()

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

if __name__ == "__main__":
    app.run(debug=True, port=sys.argv[1])