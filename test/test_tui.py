import sys
sys.path.insert(1, '../')

from lib.tuicsv import CategoryComboBox
from lib.tuicsv import SubcategoryComboBox
from lib.tuicsv import DateComboBox
from lib.tuicsv import FloatInputBox
from lib.tuicsv import TextInputBox


import os
import csv
import curses

mydict = {
    'Transfer': ['ToBBVA','ToRevolut','ToDirecta','ToING','ToINGCD','ToHype','ToBitget','ToCash','Invest','FromBBVA','FromRevolut','FromDirecta','FromBitget','FromING','FromINGCD','FromHype'],
    'Subs': ['Bank', 'VPS', 'SIM', 'VPN', 'Amazon'],
    'Groceries': ['Diet', 'Food','Supplements'],
    'Health': ['Gym', 'Hygiene', 'Eyes', 'Visit'],
    'Leisure': ['Food', 'Drink', 'Events', 'Restaurant', 'Games', 'Karma', 'Party', 'Family', 'Coffee'],
    'Transport': ['Bicycle', 'Gasoline', 'Train'],
    'Shop': ['Accessories', 'Clothes'],
    'Bills': ['Wood', 'Water', 'Electricity'],
    'Other': ['Papers', 'Gifts', 'Fines', 'Taxes'],
    'Family': ['Food', 'Favors', 'Groceries', 'Accessories', 'Karma', 'Favor'],
    'Holiday': ['Rent', 'Transport', 'Drink', 'Shop', 'Food', 'Restaurant', 'Gift', 'Party', 'Tassa', 'Groceries'],
    'Gift': ['Karma'],
    'Car': ['Buy', 'Papers', 'RCA', 'Gasoline'],
    'Financial': ['Untaxable'],
    'Income': ['Cashback','Goodselling'],
    'Employement': ['Salary']
}

def save_to_csv(date, bank, number, category, subcategory, description, filename="selections.csv"):
    """Save the current selections to a CSV file"""
    file_exists = os.path.exists(filename)
    
    with open(filename, 'a', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['Date', 'Type', 'Qty', 'Category', 'Subcategory', 'Description']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        # Write header if file is new
        if not file_exists:
            writer.writeheader()
        
        # Write the current selections with timestamp
        writer.writerow({
            'Date': date,
            'Type': bank,
            'Qty': number,
            'Category': category,
            'Subcategory': subcategory,
            'Description': description,
        })

def main(stdscr):
    # stdscr supports displaying text, erase it, ...
    stdscr.clear() # clear the screen
    curses.curs_set(0)

    # Enable keypad mode to properly handle special keys
    stdscr.keypad(True)

    height, width = stdscr.getmaxyx()
    status_text = f"Terminal size: {width}x{height}"

    subtitle = "Press 'q' to quit, any other key to continue"

    stdscr.addstr(0,2,f"row 0| ~~~~~~~~~~~~~~~ ")
    stdscr.addstr(1,2,f"row 1| Curses TUI Demo ")
    stdscr.addstr(2,2,f"row 2| ~~~~~~~~~~~~~~~ ")
    stdscr.addstr(3,2,f"row 3|{status_text}")
    stdscr.addstr(4,2,f"row 4|{subtitle}")

    comboType = CategoryComboBox(["Hype","BBVA","Revolut","Directa","ING","INGCD","Cash"])
    comboCat = CategoryComboBox(list(mydict.keys()))
    comboSubcat = SubcategoryComboBox()
    comboDate = DateComboBox()
    floatInput = FloatInputBox()
    textInput = TextInputBox(max_length=50)

    combo_boxes = [comboType, comboCat, comboSubcat, comboDate, floatInput, textInput]
    idx_combo = 0
    combo_boxes[idx_combo].is_focused = True
    labels = ["Type:","Category:", "Subcategory:", "Selected date:", "Quantity:", "Description"]
    positions = [(6,2),(7,2),(8,2),(9,2),(10,2),(11,2)]

    comboSubcat.update_options(mydict[comboCat.get_selected_value()])

    save_message = ""
    save_message_timer = 0
    while True:

        # Clear previous content
        for line in range(6, 10):
            stdscr.move(line, 0)
            stdscr.clrtoeol()
        
        for i, (label, (x,y)) in enumerate(zip(labels, positions)):
            stdscr.addstr(x, y, label)
            combo_boxes[i].draw(stdscr, x, 20)

        # Show save status message if there is one
        if save_message and save_message_timer > 0:
            stdscr.addstr(15, 2, save_message)
            save_message_timer -= 1
        else:
            stdscr.move(15, 0)
            stdscr.clrtoeol()

        # Refresh before user input
        stdscr.refresh()

        key = stdscr.getch()
        if idx_combo == 4: # Float input is focused and allow to ENTER for saving data
            floatInput.handle_char(key)
        if idx_combo == 5:
            textInput.handle_char(key)

        if key == ord('q') or key == ord('Q'):
            break
        elif key == curses.KEY_RIGHT:
            combo_boxes[idx_combo].move_forward()
            if idx_combo == 1: # Update subcategories based on selected category
                comboSubcat.update_options(mydict[comboCat.get_selected_value()])
        elif key == curses.KEY_LEFT:
            combo_boxes[idx_combo].move_backward()
            if idx_combo == 1: # Update subcategories based on selected category
                comboSubcat.update_options(mydict[comboCat.get_selected_value()])
        elif key == ord('\t') or key == curses.KEY_DOWN:
            combo_boxes[idx_combo].is_focused = False
            idx_combo = (idx_combo + 1) % len(combo_boxes)
            combo_boxes[idx_combo].is_focused = True
        elif key == curses.KEY_UP:
            combo_boxes[idx_combo].is_focused = False
            idx_combo = (idx_combo - 1) % len(combo_boxes)
            combo_boxes[idx_combo].is_focused = True
        elif key == ord('\n') or key == ord('\r') or key == 10 or key == 13:
            try:
                date = comboDate.get_selected_value()
                bank = comboType.get_selected_value()
                quantity = floatInput.get_float_value()
                category = comboCat.get_selected_value()
                subcategory = comboSubcat.get_selected_value()
                description = textInput.get_text_value()

                # Save to CSV
                save_to_csv(date, bank, quantity, category, subcategory, description)
                save_message = f"✓ Saved to new record"
                save_message_timer = 30  # Show message for ~3 seconds (30 refresh cycles)
            except Exception as e:
                save_message = f"✗ Error saving: {str(e)}"
                save_message_timer = 50  # Show error longer
                pass
        else:
            continue

if __name__ == "__main__":
    curses.wrapper(main)