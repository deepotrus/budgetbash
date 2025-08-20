import sys
sys.path.insert(1, '../')

from lib import FinCashflow
from lib import FinInvestments
from lib import FinPlot
from lib import Logger
from lib.logger import set_logging_level
from lib.common import format_df_for_print

from tabulate import tabulate

persona_data_path = "../../data"


import pandas as pd
def calc_global_nw(row_today_cashflow, df_today_holdings, df_m_cashflow, df_year_holdings):
    nw_current_month = pd.concat([row_today_cashflow['liquidity'], df_today_holdings['Total']], axis=1, keys=['liquidity', 'investments'])
    nw_current_month['networth'] = nw_current_month.liquidity + nw_current_month.investments

    nw = pd.concat([df_m_cashflow['liquidity'], df_year_holdings['Total']], axis=1, keys=['liquidity', 'investments'])
    nw['networth'] = nw.liquidity + nw.investments

    nw_global = pd.concat([nw, nw_current_month])
    nw_global["nwch"] = (nw_global.networth - nw_global.networth.shift(1) )
    nw_global["ch%"] = (nw_global.networth - nw_global.networth.shift(1) )/ nw_global.networth
    return nw_global

if __name__ == "__main__":
    YEAR : int = 2025
    set_logging_level("DEBUG")

    Logger.info("Starting lib test")

    finCashflow = FinCashflow(persona_data_path, YEAR)
    finCashflow.run()

    init_holdings = finCashflow.init_holdings
    df_year_cashflow = finCashflow.df_year_cashflow
    df_m_cashflow = finCashflow.df_m_cashflow

    balances = finCashflow.get_all_balances()
    expenses_year = finCashflow.calc_expenses() # all year
    
    fig_cashflow = FinPlot.plot_cashflow(df_m_cashflow)
    fig_expenses_year = FinPlot.plot_expenses_donut(expenses_year)
    FinPlot.plot_expenses_donut(finCashflow.calc_expenses(month=7)).show()

    fig_cashflow.show()
    fig_expenses_year.show()

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