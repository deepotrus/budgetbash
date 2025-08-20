import curses
import datetime

class ComboBox:
    def __init__(self):
        self.options : list = None
        self.idx : int = 0
        self.is_focused : bool = False
    
    def get_selected_value(self):
        return self.options[self.idx]
    
    def draw(self, stdscr, y, x):
        selected_text : str = self.get_selected_value()
        stdscr.addstr(y, x, " " * 30)  # Clear with spaces is important to avoid Giraffe into Dog which shows Dogaffe
        if self.is_focused:
            stdscr.attron(curses.A_REVERSE)
            stdscr.addstr(y, x, selected_text)
            stdscr.attroff(curses.A_REVERSE)
        else:
            stdscr.addstr(y, x, selected_text)

    def move_forward(self):
        if self.idx < len(self.options) - 1:
            self.idx += 1

    def move_backward(self):
        if self.idx > 0:
            self.idx -= 1


class CategoryComboBox(ComboBox):
    """Child class combo box for categories"""
    def __init__(self, options):
        super().__init__()
        self.options = options

class SubcategoryComboBox(ComboBox):
    """Child class combo box for subcategories"""
    def __init__(self):
        super().__init__()

    def update_options(self, options : list):
        self.idx = 0 # to make it safe for list with 1 element
        self.options = options

class DateComboBox(ComboBox):
    """Child class combo box for date selection"""
    def __init__(self):
        super().__init__()
        self.ref_day = datetime.datetime.now().date()
        self.day_offset : int = 0
        self.is_focused = False

    """Override parent class methods"""
    def get_selected_value(self):
        selected_date = self.ref_day - datetime.timedelta(days=self.day_offset)
        return selected_date.strftime("%Y-%m-%d") 

    def move_forward(self):
        if self.day_offset > 0:
            self.day_offset -= 1

    def move_backward(self):
        if self.day_offset < 365:
            self.day_offset += 1


class FloatInputBox(ComboBox):
    """Child class input box for quantities"""
    def __init__(self):
        self.value_str = str(0.0)
        self.cursor_pos = len(self.value_str)
        self.is_focused = False
    
    def get_float_value(self):
        """Convert string to float, return 0.0 if invalid"""
        try:
            return float(self.value_str) if self.value_str else 0.0
        except ValueError:
            return 0.0
    
    def get_selected_value(self):
        """Return the string representation for display"""
        return self.value_str if self.value_str else ""
    
    def draw(self, stdscr, y, x):
        # Clear the area first
        display_text = self.get_selected_value()
        stdscr.addstr(y, x, " " * 20)
        stdscr.addstr(y, x, display_text)
        
        # Show cursor if focused
        if self.is_focused:
            cursor_x = x + self.cursor_pos
            if cursor_x < x + 20:  # Make sure cursor is visible
                stdscr.addch(y, cursor_x, ord('_'))
    
    def handle_char(self, ch):
        """Handle character input"""
        if ch == curses.KEY_BACKSPACE or ch == 8 or ch == 127:  # Backspace
            if self.cursor_pos > 0:
                self.value_str = self.value_str[:self.cursor_pos-1] + self.value_str[self.cursor_pos:]
                self.cursor_pos -= 1
        elif ch == curses.KEY_DC:  # Delete key
            if self.cursor_pos < len(self.value_str):
                self.value_str = self.value_str[:self.cursor_pos] + self.value_str[self.cursor_pos+1:]
        elif ch == curses.KEY_LEFT:
            if self.cursor_pos > 0:
                self.cursor_pos -= 1
        elif ch == curses.KEY_RIGHT:
            if self.cursor_pos < len(self.value_str):
                self.cursor_pos += 1
        elif ch == curses.KEY_HOME:
            self.cursor_pos = 0
        elif ch == curses.KEY_END:
            self.cursor_pos = len(self.value_str)
        elif 32 <= ch <= 126:  # Printable characters
            char = chr(ch)
            # Allow digits, minus sign, decimal point
            if char.isdigit() or char in '.-':
                # Don't allow multiple decimal points
                if char == '.' and '.' in self.value_str:
                    return
                # Don't allow minus sign except at beginning
                if char == '-' and self.cursor_pos != 0:
                    return
                # Don't allow multiple minus signs
                if char == '-' and '-' in self.value_str:
                    return
                
                # Insert character at cursor position
                self.value_str = self.value_str[:self.cursor_pos] + char + self.value_str[self.cursor_pos:]
                self.cursor_pos += 1
    
    def move_backward(self):
        """For consistency with other combo boxes - decrement value"""
        try:
            current = float(self.value_str) if self.value_str else 0.0
            new_value = current - 1.0
            self.value_str = str(new_value)
            self.cursor_pos = len(self.value_str)
        except ValueError:
            pass

    def move_forward(self):
        """For consistency with other combo boxes - increment value"""
        try:
            current = float(self.value_str) if self.value_str else 0.0
            new_value = current + 1.0
            self.value_str = str(new_value)
            self.cursor_pos = len(self.value_str)
        except ValueError:
            pass


class TextInputBox(ComboBox):
    def __init__(self, default_value="", max_length=50):
        self.value_str = str(default_value)
        self.max_length = max_length
        self.cursor_pos = len(self.value_str)
        self.is_focused = False
    
    def get_text_value(self):
        """Return the text value"""
        return self.value_str
    
    def get_selected_value(self):
        """Return the string representation for display"""
        return self.value_str
    
    def draw(self, stdscr, y, x):
        # Clear the area first
        display_text = self.get_selected_value()
        # Show max 40 chars on screen, scroll if needed
        display_width = 40
        stdscr.addstr(y, x, " " * display_width)
        
        # Handle horizontal scrolling if text is too long
        if len(display_text) <= display_width:
            visible_text = display_text
            cursor_display_pos = self.cursor_pos
        else:
            # Scroll to keep cursor visible
            if self.cursor_pos < display_width // 2:
                # Cursor near start, show from beginning
                visible_text = display_text[:display_width]
                cursor_display_pos = self.cursor_pos
            elif self.cursor_pos > len(display_text) - display_width // 2:
                # Cursor near end, show end
                visible_text = display_text[-display_width:]
                cursor_display_pos = display_width - (len(display_text) - self.cursor_pos)
            else:
                # Cursor in middle, center it
                start = self.cursor_pos - display_width // 2
                visible_text = display_text[start:start + display_width]
                cursor_display_pos = display_width // 2
        
        stdscr.addstr(y, x, visible_text)
        
        # Show cursor if focused
        if self.is_focused:
            cursor_x = x + cursor_display_pos
            if cursor_x < x + display_width:
                stdscr.addch(y, cursor_x, ord('_'))
    
    def handle_char(self, ch):
        """Handle character input - returns True if key was handled, False if not"""
        if ch == curses.KEY_BACKSPACE or ch == 8 or ch == 127:  # Backspace
            if self.cursor_pos > 0:
                self.value_str = self.value_str[:self.cursor_pos-1] + self.value_str[self.cursor_pos:]
                self.cursor_pos -= 1
            return True
        elif ch == curses.KEY_DC:  # Delete key
            if self.cursor_pos <= len(self.value_str):
                self.value_str = self.value_str[:self.cursor_pos] + self.value_str[self.cursor_pos+1:]
            return True
        elif ch == curses.KEY_LEFT:
            if self.cursor_pos > 0:
                self.cursor_pos -= 1
            return True
        elif ch == curses.KEY_RIGHT:
            if self.cursor_pos < len(self.value_str):
                self.cursor_pos += 1
            return True
        elif ch == curses.KEY_HOME:
            self.cursor_pos = 0
            return True
        elif ch == curses.KEY_END:
            self.cursor_pos = len(self.value_str)
            return True
        elif ch == ord('\n') or ch == ord('\r') or ch == 10 or ch == 13:  # Enter key
            # Don't handle Enter - let the main loop handle it for saving
            return False
        elif 32 <= ch <= 126:  # Printable characters
            char = chr(ch)
            # Don't allow commas
            if char == ',':
                return True  # Ignore comma
            
            # Check length limit
            if len(self.value_str) >= self.max_length:
                return True  # Ignore if at max length
            
            # Insert character at cursor position
            self.value_str = self.value_str[:self.cursor_pos] + char + self.value_str[self.cursor_pos:]
            self.cursor_pos += 1
            return True
        
        return False  # Key not handled
    
    def move_forward(self):
        """For consistency with other combo boxes - move cursor right"""
        if self.cursor_pos < len(self.value_str):
            self.cursor_pos += 1
    
    def move_backward(self):
        """For consistency with other combo boxes - move cursor left"""
        if self.cursor_pos > 0:
            self.cursor_pos -= 1