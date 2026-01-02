# TESTING UTILITY FOR COMMON.PY METHODS
# Run this test with: $ python3 -m lib.libtest.test_load_data --debug
import sys # for debug flag

from ..common import load_init_holdings
from ..common import load_data
from ..common import found_cache_files

from pathlib import Path
import pandas as pd

def test_load_data(year : int, data_path : Path, debug : bool = False):
  if debug: print("Testing load data common.py")

  init_holdings = load_init_holdings(data_path, year)
  df = load_data("cashflow", data_path, year)

  if init_holdings is None:
    if debug: print("ERROR: Initial holdings loading failed")

  required = ["Type", "Coin", "Qty", "Category", "Subcategory", "Description"]
  cashflow_load_failed = any(col not in df.columns for col in required) or df.empty
  if cashflow_load_failed:
    if debug: print("ERROR: Cashflow loading failed")

  df = load_data("investments", data_path, year)
  required = ["Type", "Symbol", "Qty", "Category", "Subcategory", "Description"]
  investments_load_failed = any(col not in df.columns for col in required) or df.empty
  if investments_load_failed:
    if debug: print("ERROR: Investments loading failed")

  if (init_holdings is None) or cashflow_load_failed or investments_load_failed:
    print(f"[KO] - {sys.argv[0]} test_load_data")
  else:
    print(f"[OK] - {sys.argv[0]} test_load_data")


if __name__ == "__main__":
  debug = "--debug" in sys.argv[1:]
  year = 2026
  data_path = Path("../data")

  test_load_data(year=year, data_path=data_path, debug=debug)