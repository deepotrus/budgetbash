import pandas as pd
from .fin_cashflow import FinCashflow
from .fin_investments import FinInvestments

# Class to manage the budgetbash backend
class FlaskWrapper:
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