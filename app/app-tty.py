import sys
sys.path.insert(1, '../')
import os 
import datetime

from lib import FinCashflow
from lib import FinInvestments
from lib import FinPlot
from lib import Logger
from lib.logger import set_logging_level
from lib.common import format_df_for_print

from tabulate import tabulate
import pandas as pd

months_map = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12
}

def calc_global_nw(row_today_cashflow, df_today_holdings, df_m_cashflow, df_year_holdings):
    nw_current_month = pd.concat([row_today_cashflow['liquidity'], df_today_holdings['Total']], axis=1, keys=['liquidity', 'investments'])
    nw_current_month['networth'] = nw_current_month.liquidity + nw_current_month.investments

    nw = pd.concat([df_m_cashflow['liquidity'], df_year_holdings['Total']], axis=1, keys=['liquidity', 'investments'])
    nw['networth'] = nw.liquidity + nw.investments

    nw_global = pd.concat([nw, nw_current_month])
    nw_global["nwch"] = (nw_global.networth - nw_global.networth.shift(1) )
    nw_global["ch%"] = (nw_global.networth - nw_global.networth.shift(1) )/ nw_global.networth
    return nw_global

def status(YEAR : int, finCashflow : FinCashflow, finInvest : FinInvestments):
    init_holdings = finCashflow.init_holdings
    df_year_cashflow = finCashflow.df_year_cashflow
    df_m_cashflow = finCashflow.df_m_cashflow

    balances = finCashflow.get_all_balances()
    expenses_year = finCashflow.calc_expenses() # all year

    df_year_investments = finInvest.df_year_investments
    df_year_holdings = finInvest.df_year_holdings

    if (YEAR == datetime.datetime.now().year ):
        df_today_cashflow = finCashflow.df_last_month_cashflow
        df_today_holdings = finInvest.last_update_run()
        
        nw_global = calc_global_nw(df_today_cashflow, df_today_holdings, df_m_cashflow, df_year_holdings)
        print(tabulate(format_df_for_print(nw_global).T, headers='keys', tablefmt='psql'))
    else:
        nw = pd.concat([df_m_cashflow['liquidity'], df_year_holdings['Total']], axis=1, keys=['liquidity', 'investments'])
        nw['networth'] = nw.liquidity + nw.investments
        nw["nwch"] = (nw.networth - nw.networth.shift(1) )
        nw["ch%"] = (nw.networth - nw.networth.shift(1) )/ nw.networth
        print(tabulate(format_df_for_print(nw).T, headers='keys', tablefmt='psql'))

def cmd_fullview(YEAR : int):
    Logger.info("Starting lib test")

    finCashflow = FinCashflow("../../data", YEAR)
    finCashflow.run()

    init_holdings = finCashflow.init_holdings
    df_year_cashflow = finCashflow.df_year_cashflow
    df_m_cashflow = finCashflow.df_m_cashflow

    balances = finCashflow.get_all_balances()
    expenses_year = finCashflow.calc_expenses() # all year
    
    #fig_cashflow = FinPlot.plot_cashflow(df_m_cashflow)
    #fig_expenses_year = FinPlot.plot_expenses_donut(expenses_year)
    #FinPlot.plot_expenses_donut(finCashflow.calc_expenses(month=7)).show()
    #fig_cashflow.show()
    #fig_expenses_year.show()

    print(tabulate(format_df_for_print(df_m_cashflow).T, headers='keys', tablefmt='psql'))
    print(balances)

    finInvest = FinInvestments("../../data", YEAR)
    finInvest.run()

    df_year_investments = finInvest.df_year_investments
    df_year_holdings = finInvest.df_year_holdings

    print(tabulate(format_df_for_print(df_year_holdings).T, headers='keys', tablefmt='psql'))

    df_today_cashflow = finCashflow.df_last_month_cashflow
    df_today_holdings = finInvest.last_update_run()

    nw_global = calc_global_nw(df_today_cashflow, df_today_holdings, df_m_cashflow, df_year_holdings)
    print(tabulate(format_df_for_print(nw_global).T, headers='keys', tablefmt='psql'))

def preload(finCashflow : FinCashflow, finInvest : FinInvestments):
    Logger.info("Preloading Financial Data...")
    finCashflow.run()
    finInvest.run()
    Logger.info("Preloading Completed!")

def show_expenses(finCashflow : FinCashflow, month : str = None, detailed : bool = False):
    if month is not None:
        df = finCashflow.calc_expenses(month=months_map[month])
    else:
        df = finCashflow.calc_expenses()
    
    if not(detailed):
        df_grouped = df.groupby('Category')["Qty"].sum().reset_index().sort_values(by="Qty", ascending=False)
        total_expense = df_grouped['Qty'].sum()

        total_row = pd.DataFrame({'Category' : ['Total'], 'Qty' : [total_expense]})
        df_expenses = pd.concat([df_grouped, total_row])
        df_expenses['%'] = (100*(df_expenses.Qty/total_expense)).round(1)

        print(tabulate(df_expenses, headers='keys'))
    else:
        print(tabulate(df, headers='keys'))


def show_help():
    print("Available commands:")
    print("  help                   - Show this help message")
    print("  cmd <year>             - Launch the app for desired year")
    print("  setloglevel <loglevel> - Set log level")
    print("  exit                   - Exit the console")
    print("  clear                  - Clear the screen")

def show_help_subconsole():
    print("Available commands:")
    print("  help                       - Show this help message")
    print("  expenses <month>           - Show expenses per category for desired month")
    print("  expenses <month> detailed  - Show all expenses for desired month")
    print("  exit                       - Exit the console")
    print("  clear                      - Clear the screen")

def clear_screen():
    # Clear the console screen
    os.system('cls' if os.name == 'nt' else 'clear')

def subconsole(YEAR : int):

    finCashflow = FinCashflow("../../data", YEAR)
    finInvest = FinInvestments("../../data", YEAR)
    
    preload(finCashflow, finInvest)

    while True:
        command = input(f"CMD {YEAR}> ").strip().lower()  # Get user input and normalize it
        if command == "exit":
            print("Returning to the main console.")
            break
        elif command == "help":
            show_help_subconsole()
        elif command == "clear":
            clear_screen()
        elif command == "status":
            status(YEAR, finCashflow, finInvest)
        elif command.startswith("expenses"):
            parts = command.split()
            if len(parts) == 1:
                show_expenses(finCashflow)
            elif len(parts) > 1 and len(parts) < 4 and parts[0] == "expenses":
                month = parts[1].strip()
                if month in months_map.keys():
                    if len(parts) == 2:
                        show_expenses(finCashflow, month)
                    elif len(parts) == 3:
                        show_expenses(finCashflow, month, detailed=True)
                else:
                    print("Invalid month. Please enter january, february, ...")
            else:
                print("Usage: expenses <month>")
                print("    or expenses <month> detailed")
        else:
            print(f"Unknown command: {command}. Type 'help' for a list of commands.")

def main():
    print("Welcome to the tty app deepfinance! Type 'help' for a list of commands.")
    
    YEAR : int = 2025

    while True:
        command = input("CMD> ").strip().lower()  # Get user input and normalize it
        
        if command == "exit":
            print("Exiting the console. Goodbye!")
            break
        elif command == "help":
            show_help()
        elif command == "clear":
            clear_screen()
        elif command.startswith("setloglevel"):
            parts = command.split()
            if len(parts) == 2 and parts[0] == "setloglevel":
                loglevel = str(parts[1].strip()).upper()
                set_logging_level(loglevel)
            else:
                print("Usage: setloglevel <level>")
        elif command.startswith("cmd"):
            parts = command.split()
            if len(parts) == 2 and parts[0] == "cmd":
                year = parts[1].strip()
                if year in ["2023", "2024", "2025"]:
                    YEAR = int(year)
                    subconsole(YEAR)
                else:
                    print("Invalid year. Please enter either 2023, 2024 or 2025.")
            else:
                print("Usage: cmd <year>")
        elif command.startswith("launch"):
            # Split the command into parts
            parts = command.split()
            if len(parts) == 2 and parts[0] == "launch":
                year = parts[1].strip()
                if year in ["2023", "2024", "2025"]:
                    cmd_fullview(int(year))
                else:
                    print("Invalid year. Please enter either 2023, 2024 or 2025.")
            else:
                print("Usage: launch <year>")
        else:
            print(f"Unknown command: {command}. Type 'help' for a list of commands.")

if __name__ == "__main__":
    main()