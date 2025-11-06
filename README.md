### A Terminal Based application for handling your finances!
This Python suite was created by me for personal use with the goal to control my finances without relying on any third party tools like office of spreadsheets. Also the application is terminal based for simplicity and practical reasons since literally no GUI libraries are needed (being frugal not only in finances, but also in coding). The goal of this application if to provide a nice terminal flow in handling your finances by navigating a TUI frontend writtend in bash, where menu options call endpoints of a python flask backend. The motivation of this approach is that using bash script for TUI is natively supported in unix.

### Run the application!
After activating a python environment and having installed dependencies (which i do not know what are, ehm flask, sys, os, json, pathlib, datetime, csv, ...):
```shell
    $ ./deepfinance
```
Navigate through the menu and make sure to try the demo data!

### Future work and improvements
At the current state, the application has database operations: view, add, delete. Also implements a cache directory for temporary market data for portfolio calculations.

Next work includes:
  - Better visuals for cashflow expenses
  - Add networth history in the current year
  - Handle old plot files

Future work:
  - Less hardcoding in config.json, allow user to choose its bank (configuration accounts)