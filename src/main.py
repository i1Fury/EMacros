from datetime import datetime
from tkinter import DISABLED, HORIZONTAL, Button, Entry, Frame, Label, Scale, StringVar, Tk, filedialog
from tkinter import messagebox
from tkinter.font import Font
import traceback
from typing import Optional
from macros import Macros, Macro, MacroError, get_keyname
import os
import sys
from keyboard import hook, KeyboardEvent
import logging

def try_make_dir(path: str):
    try:
        os.mkdir(path)
    except FileExistsError:
        pass

# Create a logger that logs both to the console and to a file
logFormatter = logging.Formatter("%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s")
rootLogger = logging.getLogger()
rootLogger.setLevel(logging.DEBUG)

appdata_path = str(os.getenv('APPDATA'))
path = os.path.join(str(appdata_path), 'EMacros')

try_make_dir(path)

pathify = lambda *args: os.path.join(path, *args)

try_make_dir(pathify('logs'))

fileHandler = logging.FileHandler(pathify('logs', f"{datetime.now().strftime('%Y-%m-%d %H-%M-%S')}.log"))
fileHandler.setFormatter(logFormatter)
rootLogger.addHandler(fileHandler)

consoleHandler = logging.StreamHandler(sys.stdout)
consoleHandler.setFormatter(logFormatter)
rootLogger.addHandler(consoleHandler)


logging.log(logging.INFO, f'Path: {pathify("/")}')


# Delete all log files older than 3 days
for file in os.listdir(pathify('logs')):
    file = pathify('logs', file)
    if os.stat(file).st_mtime < datetime.now().timestamp() - 3 * 24 * 60 * 60:
        os.remove(file)



overlay = False

logging.log(logging.INFO, 'Starting up...')

configs_dir = pathify('configs')

try_make_dir(configs_dir)

logging.log(logging.INFO, f'Checking for configs in {configs_dir}...')

# find the last opened config file
configs = []
for file in os.listdir(configs_dir):
    if file.endswith('.yml') or file.endswith('.yaml'):
        config = os.path.join(configs_dir, file)
        atime = os.stat(config).st_atime
        configs.append((config, atime))

configs.sort(key=lambda x: x[1], reverse=True)


class MainUI(Tk):
    def __init__(self, macros: Optional[Macros], config_filename: Optional[str] = None):
        super().__init__()

        self.config_filename = config_filename
        self.macros = macros  # type: ignore

        self.table = None
        if not self.macros:
            _configs = configs.copy()
            logging.log(logging.INFO, f'No config file found, trying to load from {_configs}')
            while _configs:
                try:
                    self.config_filename = _configs[0][0]
                    self.macros = Macros(self.config_filename)
                    break
                except Exception:
                    _configs.pop(0)

            if not _configs:
                self.config_filename = None
                self.macros = Macros(self.config_filename)

        self.macros: Macros
        self.menu_frame = None

        self.macros_per_page = 9
        self.page = 0
        self.calculate_pages()

        self.width = 750
        self.height = 500
        self.movable = False

        self.x = self.winfo_screenwidth()//2-200
        self.y = self.winfo_screenheight()//2-100
        self.geometry(f'{self.width}x{self.height}+{self.x}+{self.y}')

        self.configure(background='black')
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.attributes('-alpha', 1)
        self.maximized = True

        self.waiting_for_key = None

        self.populate()

    def calculate_pages(self):
        self.pages = (len(self.macros.get_all()) //
                      self.macros_per_page + 1) if self.macros else 1

    def populate(self):
        self.bind('<Expose>', self.maximize)
        self.bind_all('<Button>', lambda e: e.widget.focus_set())

        moveable = []

        # add an invisible background to the window
        self.background = Frame(self, bg='black', border=0)
        self.background.place(x=0, y=0, width=self.width, height=self.height)
        moveable.append(self.background)

        self.usual_font = lambda size=16: ('Helvetica', size, 'bold')

        # Title
        self.title = Label(self, text="EMacros Config", bg='black',
                           fg='white', font=self.usual_font(25), border=0)
        self.title.place(x=5, y=5, height=40)
        moveable.append(self.title)

        width, height = (70, 40)

        self.play_button = Button(self, text="▶", bg='black', fg='green', font=self.usual_font(
            30), border=0, activebackground='black', activeforeground='white')
        self.play_button.place(
            x=self.width - (width * 6) - 60, y=9, width=width - 50, height=height)
        self.play_button.bind('<ButtonPress-1>', self.play)

        self.opacity_button = Button(self, text="👁", bg='black', fg='white', font=self.usual_font(
            20), border=0, activebackground='black', activeforeground='white')
        self.opacity_button.place(
            x=self.width - (width * 5) - 90, y=8, width=width - 20, height=height - 10)
        self.opacity_button.bind('<ButtonPress-1>', self.opacity)

        self.save_button = Button(self, text="Save", bg='black', fg='white', font=self.usual_font(
        ), border=0, activebackground='black', activeforeground='white')
        self.save_button.place(
            x=self.width - (width * 5) - 40, y=3, width=width, height=height)
        self.save_button.bind('<ButtonPress-1>', self.save)

        self.save_button = Button(self, text="Save As", bg='black', fg='white', font=self.usual_font(
        ), border=0, activebackground='black', activeforeground='white')
        self.save_button.place(
            x=self.width - (width * 4) - 35, y=3, width=width + 25, height=height)
        self.save_button.bind('<ButtonPress-1>', self.save_as)

        self.load_button = Button(self, text="Load", bg='black', fg='white', font=self.usual_font(
        ), border=0, activebackground='black', activeforeground='white')
        self.load_button.place(
            x=self.width - (width * 3) - 5, y=3, width=width, height=height)
        self.load_button.bind('<ButtonPress-1>', self.load)

        self.hide_button = Button(self, text="Hide", bg='black', fg='white', font=self.usual_font(
        ), border=0, activebackground='black', activeforeground='white')
        self.hide_button.place(
            x=self.width - (width * 2) - 5, y=3, width=width, height=height)
        self.hide_button.bind('<ButtonPress-1>', self.minimize)

        self.close_button = Button(self, text="Close", bg='black', fg='white', font=self.usual_font(
        ), border=0, activebackground='black', activeforeground='white')
        self.close_button.place(x=self.width - width - 5,
                                y=3, width=width, height=height)
        self.close_button.bind('<ButtonPress-1>', self.exit)

        for widget in moveable:
            widget.bind('<ButtonPress-1>', self.startMove)
            widget.bind('<ButtonRelease-1>', self.stopMove)
            widget.bind('<B1-Motion>', self.moving)

        self.load_macros(self.page)
    
    def opacity(self, event):
        self.attributes('-alpha', 0.8 if self.attributes('-alpha') == 1 else 1)

    def refresh_table(self):
        self.calculate_pages()

        if self.table:
            self.table.destroy()
            self.table = None

        self.load_macros(self.page)

    def next_page(self):
        self.calculate_pages()
        self.page += 1
        self.refresh_table()

    def previous_page(self):
        self.calculate_pages()
        self.page -= 1
        self.refresh_table()

    def add_macro(self):
        self.macros.add_macro()
        self.refresh_table()

    def delete_macro(self, macro):
        self.macros.remove_macro(macro)
        self.refresh_table()

    def load_macros(self, page=0):
        if page < 0:
            page = 0
        if page > self.pages:
            page = self.pages

        # Create a table of rows
        if not self.table:
            self.table = Frame(self, bg='black', border=0)
            self.table.place(x=0, y=45, width=self.width,
                             height=self.height - 40)
        # make self.table overflow and scroll

        # Create a row with 3 buttons, a text box, and a button.
        row_spacing = 10
        height = 30
        index = 1

        row = Frame(self.table, bg='black', border=0)
        row.place(x=0, y=row_spacing, width=self.width, height=40)

        menubindlabel = Label(row, text="Menu", bg='black',
                              fg='white', font=self.usual_font(), border=0)
        activationbindlabel = Label(
            row, text="Bind", bg='black', fg='white', font=self.usual_font(), border=0)
        chatbindlabel = Label(row, text="Chat", bg='black',
                              fg='white', font=self.usual_font(), border=0)
        textlabel = Label(row, text="What u wanna type homie?",
                          bg='black', fg='white', font=self.usual_font(), border=0)
        self.addmacrobutton = Button(row, text="➕", bg='black', fg='green', font=self.usual_font(15), border=0,
                                     activebackground='black', activeforeground='white', command=self.add_macro)

        menubindlabel.place(x=5, y=0, width=80, height=height)
        activationbindlabel.place(x=90, y=0, width=80, height=height)
        chatbindlabel.place(x=175, y=0, width=80, height=height)
        textlabel.place(x=245, y=0, width=300, height=height)
        self.addmacrobutton.place(x=695, y=-3, width=40, height=height)

        # put a divider under that row
        divider = Frame(self.table, bg='white', border=0)
        divider.place(x=0, y=40, width=self.width, height=1)

        sorted_macros = self.macros.get_all(
        )[self.macros_per_page * page:self.macros_per_page * (page + 1)]
        logging.log(logging.INFO, f'{len(sorted_macros)} macros to insert')
        for macro in sorted_macros:
            logging.log(logging.INFO, f'Inserting macro {macro}')
            self.insert_macro((index * height) +
                              ((index + 1) * row_spacing), height, macro)
            index += 1

        # Put a divider at the bottom
        divider = Frame(self.table, bg='white', border=0)
        divider.place(x=0, y=self.height - 90, width=self.width, height=1)

        # Add a page changer
        page_indicator = Label(
            self.table, text=f'Page {page + 1} of {self.pages}', bg='black', fg='white', font=self.usual_font(18), border=0)
        # Place it in the bottom middle of the frame
        page_indicator_width = 300
        page_indicator_height = 30
        page_indicator_x = self.width / 2 - (page_indicator_width / 2)
        page_indicator_y = self.height - 50 - page_indicator_height
        page_indicator.place(x=page_indicator_x, y=page_indicator_y,
                             width=page_indicator_width, height=page_indicator_height)

        previous_page_button = Button(self.table, text="BACK", bg='black', fg='white', font=self.usual_font(18), border=0,
                                      activebackground='black', activeforeground='white', command=self.previous_page)
        next_page_button = Button(self.table, text="NEXT", bg='black', fg='white', font=self.usual_font(18), border=0,
                                  activebackground='black', activeforeground='white', command=self.next_page)

        if page == 0:
            previous_page_button.config(
                state=DISABLED, disabledforeground='gray', command=lambda: None)
        if page == self.pages - 1:
            next_page_button.config(
                state=DISABLED, disabledforeground='gray', command=lambda: None)

        width, height = 80, 40
        previous_page_button.place(
            x=page_indicator_x - width, y=page_indicator_y, width=width, height=page_indicator_height)
        next_page_button.place(x=page_indicator_x + page_indicator_width,
                               y=page_indicator_y, width=width, height=page_indicator_height)

    def insert_macro(self, y: int, height: int, macro: Macro):
        row = Frame(self.table, bg='black', border=0)
        row.place(x=0, y=y, width=self.width, height=40)

        menubind = Button(row, bg='black', fg='white',
                          font=self.usual_font(), border=0)
        activationbind = Button(
            row, bg='black', fg='white', font=self.usual_font(), border=0)
        chatbind = Button(row, bg='black', fg='white',
                          font=self.usual_font(), border=0)

        text = StringVar()
        entry = Entry(row, textvariable=text, bg='#222222', fg='white',
                      insertbackground='#00ffee', font=self.usual_font(), border=0)
        # entry.bind('<Return>', lambda _: entry.selection_clear())
        delete = Button(row, text="⛔", bg='black', fg='#ff2200', font=self.usual_font(
            15), border=0, activeforeground='white', activebackground='black')

        # place them all evenly spaced
        menubind.place(x=5, y=0, width=80, height=height)
        activationbind.place(x=90, y=0, width=80, height=height)
        chatbind.place(x=175, y=0, width=80, height=height)
        entry.place(x=260, y=0, width=420, height=height)
        delete.place(x=700, y=0, width=30, height=height)

        macro.configure_tk(self, row, menubind,
                           activationbind, chatbind, text, delete)

    def play(self, e=None):
        global overlay
        self.macros.arm_macros()
        if self.macros.has_changed():
            if not self.save(e):
                return
        overlay = True
        self.destroy()

    def save(self, e=None) -> bool:
        logging.log(logging.INFO, self.config_filename)
        if not self.config_filename:
            return self.save_as()

        if not self.macros.has_changed():
            return True

        try:
            yaml = self.macros.to_yaml()
        except MacroError as e:
            do_continue = messagebox.askquestion(e.title, e.body)
            if do_continue == 'no':
                return False
            else:
                yaml = self.macros.to_yaml(force=True)

        do_continue = messagebox.askquestion(
            'Save Macros?', 'Are you sure you want to save them?')
        if do_continue == 'no':
            return False

        try:
            with open(self.config_filename, 'w') as f:
                f.write(yaml)
        except Exception as e:
            messagebox.showerror('Error Saving Macros!',
                                 traceback.format_exc())
            return False

        messagebox.showinfo(
            'Saved!', 'Saved macros to ' + self.config_filename)
        return True

    def save_as(self, e=None) -> bool:

        try:
            yaml = self.macros.to_yaml()
        except MacroError as e:
            do_continue = messagebox.askquestion(e.title, e.body)
            if do_continue == 'no':
                return False
            else:
                yaml = self.macros.to_yaml(force=True)
        
        do_continue = messagebox.askquestion(
            'Save Macros?', 'Are you sure you want to save them?')
        if do_continue == 'no':
            return False

        file = filedialog.asksaveasfilename(initialdir=os.path.dirname(self.config_filename) if self.config_filename else configs_dir, initialfile=os.path.basename(
            self.config_filename) if self.config_filename else 'quickchats.yml', defaultextension='.yml', filetypes=[('YAML', '.yml')])
        if not file:
            return False

        try:
            with open(file, 'w') as f:
                f.write(yaml)
        except Exception as e:
            messagebox.showerror('Error Saving Macros!',
                                 traceback.format_exc())
            return False

        messagebox.showinfo('Saved!', 'Saved macros to ' + file)
        self.config_filename = file
        return True

    def load(self, e=None):
        filename = filedialog.askopenfilename(
            defaultextension='.yml', filetypes=[('YAML', '.yml')])
        if not filename:
            return

        try:
            with open(filename, 'r') as f:
                macros = Macros(filename)
        except Exception as e:
            messagebox.showerror('Error Loading Macros!',
                                 traceback.format_exc())
            return

        self.macros = macros
        self.config_filename = filename

        self.refresh_table()

    def minimize(self, e=None):
        self.overrideredirect(False)
        self.iconify()
        self.maximized = False

    def maximize(self, e=None):
        if self.maximized:
            return

        self.deiconify()
        self.configure(background='black')
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.overrideredirect(True)

    def startMove(self, event):
        self.x = event.x
        self.y = event.y

    def stopMove(self, event):
        if not self.movable:
            self.movable = True
            return

        self.x = event.x_root - self.x
        self.y = event.y_root - self.y

    def moving(self, event):
        x = (event.x_root - self.x)
        y = (event.y_root - self.y)
        self.geometry("+%s+%s" % (x, y))

    def exit(self, e=None):
        self.destroy()


class Overlay(Tk):

    menu_close_delay: float = 2.0

    def __init__(self, macros: Optional[Macros]):
        super().__init__()

        self.macros = macros
        self.unique_scan_codes = self.macros.get_unique_scan_codes() if self.macros else set()
        self.stop_keyloop = lambda: None
        self.down_keys = set()
        self.start_keyloop()

        self.menu_frame = None
        self.width = 250
        self.height = 300
        self.w_offset = 0
        self.h_offset = 0
        self.text_offset = 0
        self.movable = False

        self.x = self.winfo_screenwidth()//2-200
        self.y = self.winfo_screenheight()//2-100
        self.geometry(f'{self.width}x{self.height}+{self.x}+{self.y}')
        

        self.configure(background='black')
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.attributes('-alpha', 0.5)
        self.maximized = True

        self.populate()

        self.current_menu: Optional[int] = None
        self.menu_opened: Optional[datetime] = None
        self.check_hide_menu()

    def key_handler(self, keycode):
        if not self.current_menu and keycode in self.macros.menus:  # type: ignore
            self.current_menu = keycode
            self.menu_opened = datetime.now()
            self.show_menu(keycode)
        
        elif self.current_menu and (macro := self.macros.get_macro(self.current_menu, keycode)):  # type: ignore
            self.current_menu = None
            self.hide_menu()
            macro.play()
        
        elif not self.current_menu and (macro := self.macros.get_macro(None, keycode)):  # type: ignore
            macro.play()

    def start_keyloop(self):
        self.stop_keyloop = hook(self.keyloop, suppress=False)

    def keyloop(self, event: KeyboardEvent):
        if event.scan_code not in self.unique_scan_codes:
            logging.log(logging.INFO, f'Unknown key: {event.scan_code}')
            return

        logging.log(logging.INFO, f'Key {event.name}: {get_keyname(event.scan_code)} [{event.scan_code}]')
        if event.event_type == 'down':
            if event.scan_code in self.down_keys:
                return

            try:
                self.down_keys.add(event.scan_code)
            except KeyError:
                pass

            self.key_handler(event.scan_code)
        elif event.event_type == 'up':
            try:
                self.down_keys.remove(event.scan_code)
            except KeyError:
                pass

    def populate(self):

        self.bind('<Expose>', self.maximize)

        # add an invisible background to the window
        self.background = Frame(self, bg='black', border=0)
        self.background.place(x=0, y=0, width=self.width, height=self.height)
        self.background.bind('<ButtonPress-1>', self.startMove)
        self.background.bind('<ButtonRelease-1>', self.stopMove)
        self.background.bind('<B1-Motion>', self.moving)

        self.hide_button = Button(self, text="Hide", bg='black', fg='white', font=(
            'Helvetica', 16, 'bold'), border=0)
        width, height = (70, 40)
        self.hide_button.place(x=self.width - 70, y=0, width=width, height=height)
        self.hide_button.bind('<ButtonPress-1>', self.minimize)

        self.settings = Button(self, text="⚙", bg='black', fg='white', font=(
            'Helvetica', 16, 'bold'), border=0)
        width, height = (40, 40)
        self.settings.place(x=self.width - 100, y=0, width=width, height=height)
        self.settings.bind('<ButtonPress-1>', self.switch_to_settings)

        self.width_slider = Scale(self, from_=0, to=300, orient=HORIZONTAL, bg='black', fg='white', troughcolor='black',
                             bd=0, sliderlength=20, font=('Helvetica', 16, 'bold'), border=0, showvalue=False)
        self.width_slider.place(x=0, y=0, width=70, height=20)
        self.width_slider.bind('<B1-Motion>', self.resize_width)
        self.width_slider.bind('<ButtonPress-1>', self.resize_width)

        self.height_slider = Scale(self, from_=0, to=300, orient=HORIZONTAL, bg='black', fg='white', troughcolor='black',
                             bd=0, sliderlength=20, font=('Helvetica', 16, 'bold'), border=0, showvalue=False)
        self.height_slider.place(x=0, y=20, width=70, height=20)
        self.height_slider.bind('<B1-Motion>', self.resize_height)
        self.height_slider.bind('<ButtonPress-1>', self.resize_height)

        self.text_size_slider = Scale(self, from_=0, to=25, orient=HORIZONTAL, bg='black', fg='white', troughcolor='black',
                                bd=0, sliderlength=20, font=('Helvetica', 16, 'bold'), border=0, showvalue=False)
        self.text_size_slider.place(x=70, y=0, width=70, height=20)
        self.text_size_slider.bind('<B1-Motion>', self.resize_text)
        self.text_size_slider.bind('<ButtonPress-1>', self.resize_text)

        self.opacity_slider = Scale(self, from_=50, to=100, orient=HORIZONTAL, bg='black', fg='white', troughcolor='black',
                                bd=0, sliderlength=20, font=('Helvetica', 16, 'bold'), border=0, showvalue=False)
        self.opacity_slider.place(x=70, y=20, width=70, height=20)
        self.opacity_slider.bind('<B1-Motion>', self.change_opacity)
        self.opacity_slider.bind('<ButtonPress-1>', self.change_opacity)
    

    def change_opacity(self, event):
        self.attributes('-alpha', self.opacity_slider.get() / 100)


    def show_menu(self, keycode: int):
        """
        They will look like this, where the keys are smaller than the values:

        Num4: Go left!
        Num5: Howard hits those!
        Num6: Faking!

        """
        assert self.macros is not None

        logging.log(logging.DEBUG, f"Showing menu for {keycode}")

        if self.menu_frame:
            self.menu_frame.destroy()

        self.menu_frame = Frame(self, bg='black', border=0)
        self.menu_frame.bind('<ButtonPress-1>', self.startMove)
        self.menu_frame.bind('<ButtonRelease-1>', self.stopMove)
        self.menu_frame.bind('<B1-Motion>', self.moving)
        self.menu_frame.place(
            x=3, y=80, width=self.width + self.w_offset, height=self.height + self.h_offset -40)


        size = 12 + round(self.text_offset)
        key_label_font = Font(family="Helvetica", size=size, weight="bold")
        for i, macro in enumerate(self.macros.get_all(keycode)):
            y = ((key_label_font.metrics('linespace') + 3) * i)
            
            key_name = f'{get_keyname(macro.activation_keycode)}:'
            key_width = key_label_font.measure(key_name)
            key_label = Label(self.menu_frame, text=key_name, bg='black', fg='white', font=key_label_font, border=0, anchor='w')
            key_label.place(x=0, y=y, width=key_width, height=key_label_font.metrics('linespace'))
            # Make sure the text doesnt get cut off

            value = macro.text
            # for size in reversed(range(1, 100)):
                
            #     if font.measure(value) + 60 < self.width and font.metrics('linespace') < 20:
            #         break

            # key_label_font = Font(family="Helvetica", size=size, weight="bold")
            value_label = Label(self.menu_frame, text=value, bg='black', fg='white', font=key_label_font, border=0, anchor='w')
            value_label.place(x=key_width + 5, y=y, width=self.width + self.w_offset - key_width, height=key_label_font.metrics('linespace'))

    def check_hide_menu(self):
        if self.menu_opened:
            # check if self.menu_opened was self.menu_close_delay seconds ago using datetime
            if (datetime.now() - self.menu_opened).total_seconds() > self.menu_close_delay:
                self.hide_menu()
                self.current_menu = None
                self.menu_opened = None
        self.after(100, self.check_hide_menu)

    def hide_menu(self):
        if self.menu_frame:
            self.menu_frame.destroy()

    def minimize(self, e=None):
        self.overrideredirect(False)
        self.iconify()
        self.maximized = False

    def maximize(self, e=None):
        if self.maximized:
            return

        self.deiconify()
        self.configure(background='black')
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.overrideredirect(True)

    def resize_window(self):
        self.geometry(
            f'{self.width + self.w_offset}x{self.height + self.h_offset}+{self.x}+{self.y}')

        self.background.place(x=0, y=0, width=self.width + self.w_offset, height=self.height + self.h_offset)


    def resize_width(self, event):
        self.w_offset = self.width_slider.get()
        self.resize_window()

    def resize_height(self, event):
        self.h_offset = self.height_slider.get()
        self.resize_window()

    def resize_text(self, event):
        self.text_offset = self.text_size_slider.get()

    def startMove(self, event):
        self.x = event.x
        self.y = event.y

    def stopMove(self, event):
        if not self.movable:
            self.movable = True
            return

        self.x = event.x_root - self.x
        self.y = event.y_root - self.y

    def moving(self, event):
        x = (event.x_root - self.x)
        y = (event.y_root - self.y)
        self.geometry("+%s+%s" % (x, y))

    def switch_to_settings(self, e=None):
        global overlay
        overlay = False
        self.stop_keyloop()
        self.destroy()


if __name__ == '__main__':
    macros = None
    config_filename = None
    app = None
    while True:
        if isinstance(app, MainUI):
            macros = app.macros
            config_filename = app.config_filename

        if not isinstance(app, MainUI) and not overlay:
            logging.log(logging.INFO, 'Starting settings ui!')
            app = MainUI(macros, config_filename)
        elif not isinstance(app, Overlay) and overlay:
            logging.log(logging.INFO, 'Starting overlay ui!')
            app = Overlay(macros)
        else:
            break
        
        app.mainloop()


    logging.log(logging.INFO, 'Closed!')
