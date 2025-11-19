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
Navigate through the menu and make sure to try the demo data!

### Future work and improvements
At the current state, the application has database operations: view, add, delete. Also implements a cache directory for temporary market data for portfolio calculations.

Next work includes:
  [ok] Better visuals for cashflow expenses
  [ok] Add networth history in the current year
  [ok] Less hardcoding in config.json, allow user to choose its providers. Solved with mappings.json which makes condig.json user-agnostic with template expansion.
  - Handle old plot files
  - Add monthly detailed view for expenses 
  - Add card balances an all accounts
  - Clean cache on data folder (demo already implemented)
  - Revisit categories
  - In view database routine make a groupby on accounts providers (e.g. bank1, bank2)
