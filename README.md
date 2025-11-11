### A Terminal Based application for handling your finances!
This Python suite was created by me for personal use with the goal to control my finances without relying on any third party tools like office of spreadsheets. Also the application is terminal based for simplicity and practical reasons since literally no GUI libraries are needed (being frugal not only in finances, but also in coding). The goal of this application is to provide a nice terminal flow in handling your finances by navigating a TUI frontend writtend in bash, where menu options call endpoints of a python flask backend. The motivation of this approach is that using bash script for TUI is natively supported in unix.

Thanks to the work of [piccolomo](https://github.com/piccolomo) it is possible to plot finance statistics directly into the terminal, which i did by creating an endpoint inside the backend, which is accessed via a the bash menu option "Plot".

### Run the application!
After activating a python environment and having installed dependencies (which i do not know what are, ehm flask, sys, os, json, pathlib, datetime, csv, ...):
```shell
    $ ./deepfinance
```
Navigate through the menu and make sure to try the demo data!

### Future work and improvements
At the current state, the application has database operations: view, add, delete. Also implements a cache directory for temporary market data for portfolio calculations.

Next work includes:
  [ok] Better visuals for cashflow expenses
  [ok] Add networth history in the current year
  - Handle old plot files
  - Add monthly detailed view for expenses 
  - Add balances an all bank accounts

Future work:
  - Less hardcoding in config.json, allow user to choose its bank (configuration accounts)
  - Add demo option by default for the first run (making it accessible to people using the first time) and add a setting for changing the default from demo to a path