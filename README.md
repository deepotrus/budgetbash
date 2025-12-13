# Budget Bash
BudgetBash is a terminal application for tracking your spending, incomes and investments. This suite was created by me for personal use with the goal to control my finances without relying on any third party tools like office of spreadsheets. Also the application is terminal based for simplicity and practical reasons since literally no GUI libraries are needed (being frugal not only in finances, but also in coding). The goal of this application is to provide a nice terminal flow in handling your finances by navigating a TUI frontend writtend in bash, where menu options call endpoints of a python flask backend. The motivation of this approach is that using bash script for TUI is natively supported in unix.

Thanks to the work of [piccolomo](https://github.com/piccolomo) it is possible to plot finance statistics directly into the terminal, which i did by creating an endpoint inside the backend, which is accessed via a the bash menu option "Plot".
### Dependencies
For python the following libraries are needed: tabulate, pandas, flask, requests, plotext, plotly (going to be removed soon)

For bash only jq is needed for parsing json files in bash.
### Run the application!
After activating a python environment and having installed dependencies (which i do not know what are, ehm flask, sys, os, json, pathlib, datetime, csv, ...):
```shell
    $ ./budgetbash
```
Navigate through the menu, enable the backend from Settings menú, then in the main menu initialize database, which loads your cashflow and investments data, then updates market data for assets. Then user can check his networth updated to the last market prices of the assets he posses!

### Testing existing methods
For testing existing methods in the library for validation, cd into project dir and run with package context:
```shell
    $ python3 -m lib.libtest.test_expansion 
```
How to test backend routes? Run the deepbackend.py script and use curl to check its status
```shell
    $ python3 deepbackend.py 5001
    $ curl -X GET localhost:5001/
```
There is a route which shows all available routes:
```shell
    $ curl -X GET localhost:5001/_routes
```
Launch the commands used by the bash frontend, which are just GET and POST requests:
```shell
    $ curl -X POST localhost:5001/initialize -d "year=2025&data_path=demo"
```
To make a query on the csv database, GET requests with data must be provided in this form:
```shell
    $ curl -s "localhost:5001/view_database?data_type=cashflow&year=2025&month=3"
```
### Future work and improvements
At the current state, the application has database operations: view, add, delete. Also implements a cache directory for temporary market data for portfolio calculations.

Next work includes:
  - [ok] Better visuals for cashflow expenses
  - [ok] Add networth history in the current year
  - [ok] Less hardcoding in config.json, allow user to choose its providers. Solved with mappings.json which makes condig.json user-agnostic with template expansion.
  - Handle old plot files
  - [ok] Add monthly detailed view for expenses 
  - [ok] Add card balances an all accounts
  - Clean cache on data folder (demo already implemented)
  - Revisit categories
  - In view database routine make a groupby on accounts providers (e.g. bank1, bank2)
