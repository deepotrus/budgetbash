from operator import index
import requests
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import json
import pandas as pd
import time
import random

from .common import found_cache_files

user_agents = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/121.0',
]

class FinFetch:
    def fetch_crypto_data(symbol, currency="EUR", years_watchback=3):
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}-{currency}?range={years_watchback}y&interval=1mo"
        headers = {'User-Agent': user_agents[0]} # Set the user agent to mimic a web browser, otherwise error 429 too many requests
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            data = response.json()
            
            # Extract the relevant data
            timestamps = data['chart']['result'][0]['timestamp']
            open_prices = data['chart']['result'][0]['indicators']['quote'][0]['open']
            close_prices = data['chart']['result'][0]['indicators']['quote'][0]['close']
            
            asset_history = pd.DataFrame({
                'Date': pd.to_datetime(timestamps, unit='s').strftime('%Y-%m-%d'),
                'Close': close_prices
            })

            asset_history['Close'] = asset_history['Close'].round(2)
            asset_history['Date'] = pd.to_datetime(asset_history['Date'])
            asset_history.set_index('Date',inplace=True)

            # Change dates with end of month instead of start for coherence
            asset_history.index = asset_history.index + pd.offsets.MonthEnd(0)

            return asset_history
        else:
            print(f"Error fetching data: {response.status_code}")
            print(url)
            return None

    def fetch_etf_data(isin, currency="EUR", years_watchback=3):
        today = datetime.now()
        query_end_date = today.strftime('%Y-%m-%d')
        query_start_date = ( today - relativedelta(years=years_watchback) ).strftime('%Y-%m-%d')

        url = f"https://www.justetf.com/api/etfs/{isin}/performance-chart?locale=en&currency={currency}&valuesType=MARKET_VALUE&reduceData=true&includeDividends=false&features=DIVIDENDS&dateFrom={query_start_date}&dateTo={query_end_date}"
        headers = {'User-Agent': user_agents[0]} # User agent to mimic a web browser, otherwise error 429 too many requests

        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            data = response.json()
            
            dates = list()
            close_prices = list()
            for row in data['series']:
                dates.append(row['date'])
                close_prices.append(row['value']['raw'])

            j_asset_history = pd.DataFrame({
                'Date': pd.to_datetime(dates).strftime('%Y-%m-%d'),
                'Close': close_prices
            })

            j_asset_history['Close'] = j_asset_history['Close'].round(2)
            j_asset_history['Date'] = pd.to_datetime(j_asset_history['Date'])
            j_asset_history.set_index('Date',inplace=True)

            # Sample from daily to monthly and take end of month for coherence
            j_asset_history = j_asset_history.resample(rule='ME').last()

            return j_asset_history
        else:
            print(f"Error fetching data: {response.status_code}")
            return None

    def fetch_crypto_data_today(cache_dir, symbol, currency="EUR", years_watchback=1):
        if found_cache_files(cache_dir, symbol, currency):
            asset_today =  pd.read_csv(f"{cache_dir}/cache_{symbol}-{currency}.csv")
            asset_today['Date'] = pd.to_datetime(asset_today['Date'])
            asset_today.set_index('Date',inplace=True)
            return asset_today
        else:
            # Now get real time market data
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}-{currency}?range={years_watchback}y&interval=1d"
            headers = {'User-Agent': user_agents[0]} # Set the user agent to mimic a web browser, otherwise error 429 too many requests
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()

                timestamp = data['chart']['result'][0]['meta']['regularMarketTime']
                close_price = data['chart']['result'][0]['meta']['regularMarketPrice']

                asset_today = pd.DataFrame({
                    'Date': [pd.to_datetime(timestamp, unit='s').strftime('%Y-%m-%d')],
                    'Close': [close_price]
                })

                asset_today['Close'] = asset_today['Close'].round(2)
                asset_today['Date'] = pd.to_datetime(asset_today['Date'])
                asset_today.set_index('Date',inplace=True)
                print(asset_today)

                asset_today.to_csv(f"{cache_dir}/cache_{symbol}-{currency}.csv")
                
                time.sleep(random.uniform(5,7)) # sleep for preventing status resp 500 (ip addres based limitation)

                return asset_today # one row dataframe of current asset value
            else:
                print(f"Error fetching data: {response.status_code}")
                print(url)
                return None

    def fetch_etf_data_today(cache_dir, isin, currency="EUR"):
        if found_cache_files(cache_dir, isin, currency):
            asset_today = pd.read_csv(f"{cache_dir}/cache_{isin}-{currency}.csv")
            asset_today['Date'] = pd.to_datetime(asset_today['Date'])
            asset_today.set_index('Date',inplace=True)
            return asset_today
        else:
            today = datetime.now()
            query_end_date = today.strftime('%Y-%m-%d')
            query_start_date = ( today - relativedelta(months=1) ).strftime('%Y-%m-%d')

            url = f"https://www.justetf.com/api/etfs/{isin}/performance-chart?locale=en&currency={currency}&valuesType=MARKET_VALUE&reduceData=true&includeDividends=false&features=DIVIDENDS&dateFrom={query_start_date}&dateTo={query_end_date}"
            headers = {'User-Agent': user_agents[0]} # User agent to mimic a web browser, otherwise error 429 too many requests

            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()

                close_price = data['latestQuote']['raw']
                date = data['latestQuoteDate']

                asset_today = pd.DataFrame({
                    'Date': [date],
                    'Close': [close_price]
                })

                asset_today['Close'] = asset_today['Close'].round(2)
                asset_today['Date'] = pd.to_datetime(asset_today['Date'])
                asset_today.set_index('Date',inplace=True)

                asset_today.to_csv(f"{cache_dir}/cache_{isin}-{currency}.csv")

                time.sleep(random.uniform(5,7)) # sleep for preventing status resp 500 (ip addres based limitation)

                return asset_today
            else:
                print(f"Error fetching data: {response.status_code}")
                return None
