# TESTING UTILITY FOR COMMON.PY METHODS
# Run this test with: $ python3 -m lib.libtest.test_expansion --debug
import sys # for debug flag

from ..common import load_config
from ..common import load_mappings
from ..common import expand_transfer_templates
from ..common import get_db_csv_path
from ..common import determine_month_from_date
from ..common import validate_data

from pathlib import Path

def test_expansion(debug : bool = False):
    if debug: print("Testing template expansion...")

    # Load original config
    config = load_config()
    if debug: print(config['cashflow']['Subcategory']['Transfer'])

    # Expand templates
    expanded_config = expand_transfer_templates(config)
    if debug: print(expanded_config['cashflow']['Subcategory']['Transfer'])

    expected_values = [
        "ToHype", "ToBBVA", "ToRevolut", "ToING", "ToINGCD",
        "ToDirecta", "ToBitget", "ToCash", "Invest",
        "FromHype", "FromBBVA", "FromRevolut", "FromING", "FromINGCD",
        "FromDirecta", "FromBitget", "FromCash"
    ]

    actual_values = expanded_config['cashflow']['Subcategory']['Transfer']

    if debug:
        print(f"Expected {len(expected_values)} subcategories, got {len(actual_values)}")
        print("Expanded subcategories as comma-separated (like API response):")
        print(','.join(actual_values))

    missing = set(expected_values) - set(actual_values)
    extra = set(actual_values) - set(expected_values)

    if not missing and not extra:
        if debug: print(f"All expected subcategories present!")
        print(f"[OK] - {sys.argv[0]} test_expansion")
    else:
        if debug:
            if missing:
                print(f"NOT OK - Missing values: {missing}")
            if extra:
                print(f"NOT OK - Extra values: {extra}")
        print(f"[KO] - {sys.argv[0]}")

def test_get_db_csv_path(debug : bool = False):
    if debug: print("Testing getting csv path...")

    data_type = "cashflow"
    year = 2026
    month = 1
    data_path = Path("demo")

    expected_csv_path = f"{data_path}/{year}/{data_type}/{year}-{month:02d}_{data_type}.csv"
    csv_path = get_db_csv_path(data_type, year, month, data_path)

    if debug:
        print(f"Testing expected csv path: {expected_csv_path}")
        print(f"Testing built csv path: {csv_path}")

    if csv_path == expected_csv_path:
        print(f"[OK] - {sys.argv[0]} test_get_db_csv_path")
    else:
        print(f"[KO] - {sys.argv[0]} test_get_db_csv_path")


if __name__ == "__main__":
    debug = "--debug" in sys.argv[1:]

    test_expansion(debug=debug)
    test_get_db_csv_path(debug=debug)