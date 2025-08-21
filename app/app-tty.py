import sys
sys.path.insert(1, '../')


import datetime
import os
import csv
import curses

from lib import FinCashflow
from lib import FinInvestments
from lib import FinPlot
from lib import Logger
from lib.logger import set_logging_level
from lib.common import format_df_for_print

from lib.tuicsv import CategoryComboBox
from lib.tuicsv import SubcategoryComboBox
from lib.tuicsv import DateComboBox
from lib.tuicsv import FloatInputBox
from lib.tuicsv import TextInputBox

from tabulate import tabulate
import pandas as pd

mydict = {
    'Transfer': ['ToBBVA','ToRevolut','ToDirecta','ToING','ToINGCD','ToHype','ToBitget','ToCash','Invest','FromBBVA','FromRevolut','FromDirecta','FromBitget','FromING','FromINGCD','FromHype'],
    'Subs': ['Bank', 'VPS', 'SIM', 'VPN', 'Amazon'],
    'Groceries': ['Diet', 'Food','Supplements'],
    'Health': ['Gym', 'Hygiene', 'Eyes', 'Visit'],
    'Leisure': ['Food', 'Drink', 'Events', 'Restaurant', 'Games', 'Karma', 'Party', 'Family', 'Coffee'],
    'Transport': ['Bicycle', 'Gasoline', 'Train'],
    'Shop': ['Accessories', 'Clothes'],
    'Bills': ['Wood', 'Water', 'Electricity'],
    'Other': ['Papers', 'Gifts', 'Fines', 'Taxes'],
    'Family': ['Food', 'Favors', 'Groceries', 'Accessories', 'Karma', 'Favor'],
    'Holiday': ['Rent', 'Transport', 'Drink', 'Shop', 'Food', 'Restaurant', 'Gift', 'Party', 'Tassa', 'Groceries'],
    'Gift': ['Karma'],
    'Car': ['Buy', 'Papers', 'RCA', 'Gasoline','Services','Repairs'],
    'Financial': ['Untaxable'],
    'Income': ['Cashback','Goodselling'],
    'Employement': ['Salary']
}

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

def cmd_fullview(YEAR : int, persona_data_path : str):
    Logger.info("Starting lib test")

    finCashflow = FinCashflow(persona_data_path, YEAR)
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

    finInvest = FinInvestments(persona_data_path, YEAR)
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



def save_to_csv(date, bank, number, category, subcategory, description, filename="selections.csv"):
    """Save the current selections to a CSV file"""
    file_exists = os.path.exists(filename)
    
    with open(filename, 'a', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['Date', 'Type', 'Coin', 'Qty', 'Category', 'Subcategory', 'Description']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        # Write header if file is new
        if not file_exists:
            writer.writeheader()
        
        # Write the current selections with timestamp
        writer.writerow({
            'Date': date,
            'Type': bank,
            'Coin': "EUR", # always at the moment
            'Qty': number,
            'Category': category,
            'Subcategory': subcategory,
            'Description': description,
        })

def start_tuicsv(stdscr, month : str, YEAR : int, persona_data_path : str):
    # stdscr supports displaying text, erase it, ...
    stdscr.clear() # clear the screen
    curses.curs_set(0)

    # Enable keypad mode to properly handle special keys
    stdscr.keypad(True)

    height, width = stdscr.getmaxyx()
    status_text = f"Terminal size: {width}x{height}"

    subtitle = "Press 'q' to quit, any other key to continue"

    stdscr.addstr(0,2,f"row 0| ~~~~~~~~~~~~~~~ ")
    stdscr.addstr(1,2,f"row 1| Curses TUI Demo ")
    stdscr.addstr(2,2,f"row 2| ~~~~~~~~~~~~~~~ ")
    stdscr.addstr(3,2,f"row 3|{status_text}")
    stdscr.addstr(4,2,f"row 4|{subtitle}")

    comboType = CategoryComboBox(["Hype","BBVA","Revolut","Directa","ING","INGCD","Cash"])
    comboCat = CategoryComboBox(list(mydict.keys()))
    comboSubcat = SubcategoryComboBox()
    comboDate = DateComboBox()
    floatInput = FloatInputBox()
    textInput = TextInputBox(max_length=50)

    combo_boxes = [comboType, comboCat, comboSubcat, comboDate, floatInput, textInput]
    idx_combo = 0
    combo_boxes[idx_combo].is_focused = True
    labels = ["Type:","Category:", "Subcategory:", "Selected date:", "Quantity:", "Description"]
    positions = [(6,2),(7,2),(8,2),(9,2),(10,2),(11,2)]

    comboSubcat.update_options(mydict[comboCat.get_selected_value()])

    save_message = ""
    save_message_timer = 0
    while True:

        # Clear previous content
        for line in range(6, 10):
            stdscr.move(line, 0)
            stdscr.clrtoeol()
        
        for i, (label, (x,y)) in enumerate(zip(labels, positions)):
            stdscr.addstr(x, y, label)
            combo_boxes[i].draw(stdscr, x, 20)

        # Show save status message if there is one
        if save_message and save_message_timer > 0:
            stdscr.addstr(15, 2, save_message)
            save_message_timer -= 1
        else:
            stdscr.move(15, 0)
            stdscr.clrtoeol()

        # Refresh before user input
        stdscr.refresh()

        key = stdscr.getch()
        if idx_combo == 4: # Float input is focused and allow to ENTER for saving data
            floatInput.handle_char(key)
        if idx_combo == 5:
            textInput.handle_char(key)

        if key == ord('q') or key == ord('Q'):
            break
        elif key == curses.KEY_RIGHT:
            combo_boxes[idx_combo].move_forward()
            if idx_combo == 1: # Update subcategories based on selected category
                comboSubcat.update_options(mydict[comboCat.get_selected_value()])
        elif key == curses.KEY_LEFT:
            combo_boxes[idx_combo].move_backward()
            if idx_combo == 1: # Update subcategories based on selected category
                comboSubcat.update_options(mydict[comboCat.get_selected_value()])
        elif key == ord('\t') or key == curses.KEY_DOWN:
            combo_boxes[idx_combo].is_focused = False
            idx_combo = (idx_combo + 1) % len(combo_boxes)
            combo_boxes[idx_combo].is_focused = True
        elif key == curses.KEY_UP:
            combo_boxes[idx_combo].is_focused = False
            idx_combo = (idx_combo - 1) % len(combo_boxes)
            combo_boxes[idx_combo].is_focused = True
        elif key == ord('\n') or key == ord('\r') or key == 10 or key == 13:
            try:
                date = comboDate.get_selected_value()
                bank = comboType.get_selected_value()
                quantity = floatInput.get_float_value()
                category = comboCat.get_selected_value()
                subcategory = comboSubcat.get_selected_value()
                description = textInput.get_text_value()

                # Save to CSV
                append_data_path = f"{persona_data_path}/{YEAR}/cashflow/{YEAR}-{months_map[month]:0=2}_cashflow.csv"
                save_to_csv(date, bank, quantity, category, subcategory, description, filename = append_data_path)
                save_message = f"✓ Saved to new record"
                save_message_timer = 30  # Show message for ~3 seconds (30 refresh cycles)
            except Exception as e:
                save_message = f"✗ Error saving: {str(e)}"
                save_message_timer = 50  # Show error longer
                pass
        else:
            continue


def show_help():
    print("Available commands:")
    print("  help                   - Show this help message")
    print("  cmd <year>             - Launch the app for desired year")
    print("  setloglevel <loglevel> - Set log level")
    print("  demo                   - Config path to demo data folder")
    print("  normal                 - Config path to external personal data folder")
    print("  exit                   - Exit the console")
    print("  clear                  - Clear the screen")

def show_help_subconsole():
    print("Available commands:")
    print("  help                       - Show this help message")
    print("  nwstatus                   - Show Networth status")
    print("  expenses <month>           - Show expenses per category for desired month")
    print("  expenses <month> detailed  - Show all expenses for desired month")
    print("  append <month>             - Append new data to csv database")
    print("  exit                       - Exit the console")
    print("  clear                      - Clear the screen")

def clear_screen():
    # Clear the console screen
    os.system('cls' if os.name == 'nt' else 'clear')

def subconsole(YEAR : int, persona_data_path : str):
    finCashflow = FinCashflow(persona_data_path, YEAR)
    finInvest = FinInvestments(persona_data_path, YEAR)
    
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
        elif command == "nwstatus":
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
        elif command.startswith("append"):
            parts = command.split()
            if len(parts) == 2 and parts[0] == "append":
                month = parts[1].strip()
                if month in months_map.keys():
                    stdscr = curses.initscr()
                    curses.noecho()  # Turn off echoing of keyboard input
                    curses.cbreak()  # Enable cbreak mode (don't wait for newline)

                    try:
                        start_tuicsv(stdscr, month, YEAR, persona_data_path)
                    finally: # Clean up curses
                        curses.nocbreak()
                        stdscr.keypad(False)
                        curses.echo()
                        curses.endwin()
                else:
                    print("Invalid month. Please enter january, february, ...")
            else:
                print("Usage: append <month>")                
        else:
            print(f"Unknown command: {command}. Type 'help' for a list of commands.")

def main():
    print("Welcome to the tty app deepfinance! Type 'help' for a list of commands.")
    
    persona_data_path = "../../data"
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
        elif command == "demo":
            persona_data_path = "../demo"
        elif command == "normal":
            persona_data_path = "../../data"
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
                    subconsole(YEAR, persona_data_path)
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
                    cmd_fullview(int(year), persona_data_path)
                else:
                    print("Invalid year. Please enter either 2023, 2024 or 2025.")
            else:
                print("Usage: launch <year>")
        else:
            print(f"Unknown command: {command}. Type 'help' for a list of commands.")

if __name__ == "__main__":
    main()