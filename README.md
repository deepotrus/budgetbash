### A Terminal Based application for handling your finances!
This Python suite was created by me for personal use with the goal to control my finances without relying on any third party tools like office of spreadsheets. Also the application is terminal based for simplicity and practical reasons since literally no GUI libraries are needed (being frugal not only in finances, but also in coding).

### Install Python Dependencies
Create a python environment and install requirements with pip3
```shell
    $ python3 -m venv .fin
    $ source .fin/bin/activate
    $ pip3 install -r requirements.txt
```

### Run the tty application!
After activating the python environment and having installed Dependencies:
```shell
    $ cd app
    $ python3 app-tty.py
```

### Demo data for code testing
I added a directory with demo data so that everyone can get started without having to create a database from zero just to see the thing running. To enable it:
```shell
    CMD> demo
    CMD> cmd 2025
```
At this point a subconsole opens loading data from demo/2025. Some commands for viewing networth and expenses are:
```shell
    CMD 2025> nwstatus
    CMD 2025> expenses january
```
In the current status it is possible to add data to the csv database with a tui console.
```shell
    CMD 2025> append january
```

### Future work and improvements
The application can be improved by adding commands on subconsoles, removing hardcoded categories making the app more flexible to individual users, and finally handling better the investment codebase part with user agents for fetching current asset prices.
