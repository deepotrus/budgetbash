from typing import Dict
from pathlib import Path
import pandas as pd

from .logger import Logger

from .common import *
from .errors import *

class FinCashflow:
    """
    A class to load personal financial data.

    Attributes:
        init_holdings (dict): A dictionary to store initial holdings.
        df_year_cashflow (pd.DataFrame): DataFrame to track yearly cash flow.
        df_m_cashflow (pd.DataFrame) : Table which resumes monthly data
    """
    def __init__(self, path: str, YEAR: int):
        Logger.info("Initializing FinCashflow class.")
        path_o = Path(path)
        if path_o.exists():
            self.path = path_o
        else:
            Logger.error("Wrong path!")
            raise PathError(f"Entered path {path_o} does not exist! Cannot load files.")

        self.YEAR : int = YEAR
        self.init_holdings : Dict[str, float] = load_init_holdings(self.path, self.YEAR)
        self.df_year_cashflow : pd.DataFrame = load_data("cashflow", self.path, self.YEAR)
        self.df_m_cashflow : pd.DataFrame = pd.DataFrame()
        self.df_last_month_cashflow : pd.DataFrame = pd.DataFrame()
        pass

    def get_all_balances(self):
        balances = dict()
        accounts = self.df_year_cashflow['Type'].unique().tolist()
        for cc in accounts:
            if cc in self.init_holdings['liquidity_eur'].keys():
                val = self.df_year_cashflow.loc[self.df_year_cashflow["Type"] == cc]['Qty'].sum() + self.init_holdings['liquidity_eur'][cc]
                balances[cc] = round(float(val), 2)
            else:
                val = self.df_year_cashflow.loc[self.df_year_cashflow["Type"] == cc]['Qty'].sum()
                balances[cc] = round(float(val), 2)

        return balances
    
    def calc_expenses(self, month : int = None): # For donut plot expenses
        # If month is provided, filter by month; otherwise, use the entire DataFrame
        if month is not None:
            df_selected = self.df_year_cashflow[self.df_year_cashflow.index.month == month]
        else:
            df_selected = self.df_year_cashflow  # Use the entire DataFrame for yearly calculation

        df_expenses = df_selected.loc[
            (df_selected["Category"] != "Transfer") & (df_selected["Qty"] < 0)
        ]
        expenses = df_expenses['Qty'].abs().values
        df_expenses = df_expenses.assign(Expenses = expenses) # Creates new columns "Expenses"
        
        df_expenses["Qty"] = df_expenses.Qty.abs() # plotly sunburst does not understand negative values

        return df_expenses
    
    def calc_monthly_cashflow(self):
        end_date = define_end_date(self.YEAR)
        df_year_cashflow = self.df_year_cashflow.loc[self.df_year_cashflow.index <= end_date]

        incomes = df_year_cashflow.loc[(df_year_cashflow["Category"] != "Transfer") & (df_year_cashflow["Qty"] > 0)]
        liabilities = df_year_cashflow.loc[(df_year_cashflow["Category"] != "Transfer") & (df_year_cashflow["Qty"] <= 0)]
        investments = df_year_cashflow.loc[ (df_year_cashflow["Category"] == "Transfer") & (df_year_cashflow["Subcategory"] == "Invest")]
        
        m_incomes = incomes.resample(rule='ME')['Qty'].sum()
        m_liab = liabilities.resample(rule='ME')['Qty'].sum()
        m_savings = incomes.resample(rule='ME')['Qty'].sum() + liabilities.resample(rule='ME')['Qty'].sum()
        m_investments = investments.resample(rule='ME')['Qty'].sum()
        m_savingrate = m_savings / m_incomes

        Logger.debug("\n m_incomes:\n%s", m_incomes.to_string())
        Logger.debug("\n m_liab:\n%s", m_liab.to_string())
        Logger.debug("\n m_savings:\n%s", m_savings.to_string())
        Logger.debug("\n m_investments:\n%s", m_investments.to_string())
        Logger.debug("\n m_savingrate:\n%s", m_savingrate.to_string())


        # Add fill values to m_investments otherwise shifted data
        complete_index = pd.date_range(start=f"{self.YEAR}-01-01", end=end_date, freq='ME') # End of month
        df_month_fill = pd.DataFrame(index=complete_index, data=0.0, columns=["Qty"], dtype='float64')
        temp_fill = df_month_fill.Qty.copy()
        temp_fill.update(m_investments)

        zipped = zip(
            m_incomes.index, m_incomes.values,
            m_liab.values, m_savings.values,
            m_savingrate.values, temp_fill.values, # m_investments
        )

        df_m_cashflow = pd.DataFrame(zipped,columns=["Date","incomes","liabilities","savings","saving_rate","investments"]).set_index("Date")
        
        # if in a month no transactions happen, then add column of that month filled with zero
        df_m_cashflow = df_m_cashflow.reindex(temp_fill.index, fill_value=0)

        # Calculate cumulative savings + init 
        init_liquidity = 0
        for cc, val in self.init_holdings['liquidity_eur'].items():
            init_liquidity += val

        init_row = pd.DataFrame({
            "incomes": ['-'],
            "liabilities": ['-'],
            "savings": [init_liquidity],
            "saving_rate": ['-'],
            "investments": [0]
        }, index=[datetime(self.YEAR-1, 12, 31)])

        df_monthly_cashflow = pd.concat([init_row, df_m_cashflow])
        df_monthly_cashflow['liquidity'] = df_monthly_cashflow['savings'].values.cumsum() - df_monthly_cashflow['investments'].abs().values.cumsum()
        return df_monthly_cashflow

    def calc_curr_month_cashflow(self):
        today_date_str, today_month_str, today = define_today_date()
        prev_month_liquidity, prev_month_investments = define_prev_month_holdings(self.df_m_cashflow)
        df_curr_month_cashflow = self.df_year_cashflow.loc[today_month_str]

        incomes = df_curr_month_cashflow.loc[(df_curr_month_cashflow["Category"] != "Transfer") & (df_curr_month_cashflow["Qty"] > 0)]
        liabilities = df_curr_month_cashflow.loc[(df_curr_month_cashflow["Category"] != "Transfer") & (df_curr_month_cashflow["Qty"] <= 0)]
        investments = df_curr_month_cashflow.loc[ (df_curr_month_cashflow["Category"] == "Transfer") & (df_curr_month_cashflow["Subcategory"] == "Invest")]

        m_incomes     = float(incomes    ['Qty'].sum()  )
        m_liab        = float(liabilities['Qty'].sum()  )
        m_savings     = float(incomes    ['Qty'].sum() + liabilities['Qty'].sum()  )
        m_investments = float(investments['Qty'].sum()  )
        try:
            m_savingrate  = float(m_savings / m_incomes     )
        except Exception as ZeroDivisionError:
            m_savingrate = 0

        row_today_cashflow = pd.DataFrame({
            "incomes": [m_incomes],
            "liabilities": [m_liab],
            "savings": [m_savings],
            "saving_rate": [m_savingrate],
            "investments": [prev_month_investments + m_investments],
            "liquidity": [prev_month_liquidity + m_savings - abs(m_investments)]
        }, index=[datetime(today.year, today.month, today.day)])

        return row_today_cashflow

    def run(self):
        self.df_m_cashflow = self.calc_monthly_cashflow()
        self.df_last_month_cashflow = self.calc_curr_month_cashflow()