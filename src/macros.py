# MIT License

# Copyright (c) 2023 ElliotCS

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


from __future__ import annotations
from typing import Optional, TYPE_CHECKING
if TYPE_CHECKING:
    from main import MainUI
    from macros import Macros
from loader import load, dump
from keyboard import press, release, read_event
from time import sleep
from string import ascii_uppercase
from tkinter import Button, StringVar, Frame
from keycodes import scancode_to_keyname, get_keyname
import logging
from strictyaml.exceptions import YAMLValidationError, YAMLSerializationError, MarkedYAMLError

to_shift = {
    '!': '1',
    '@': '2',
    '#': '3',
    '$': '4',
    '%': '5',
    '^': '6',
    '&': '7',
    '*': '8',
    '(': '9',
    ')': '0',
    '_': '-',
    '+': '=',
    '{': '[',
    '}': ']',
    '|': '\\',
    ':': ';',
    '"': "'",
    '<': ',',
    '>': '.',
    '?': '/',
    '~': '`'
} | {key: key.lower() for key in ascii_uppercase}


class MacroError(Exception):

    def __init__(self, bad_macros: list[Macro]) -> None:
        super().__init__(f'You have incomplete macros, do you want to continue and only save the valid ones?')
        self.title = 'You have some incomplete Macros!'
        self.body = f'Do you want to continue without saving the following macros:\n'
        for macro in bad_macros:
            self.body += f'Menu key: {get_keyname(macro.menu_keycode)}, Activation key: {get_keyname(macro.activation_keycode)}, Text: {macro.text}\n'


class Macro(object):

    name: str
    menu_keycode: int
    activation_keycode: int
    text: str
    delays: dict[float, float]
    enabled: bool

    root: Optional[MainUI]
    row: Optional[Frame]
    menu_button: Optional[Button]
    activation_button: Optional[Button]
    chat_opener_button: Optional[Button]
    text_string_var: Optional[StringVar]
    delete_button: Optional[Button]

    def __init__(self, macros: Macros, name: str = '', data: dict = {}) -> None:
        logging.log(logging.INFO, f'Loading macro: {data}')
        self._macros = macros
        self.name = name
        self.menu_keycode = data.get('menu_keycode', -1)
        self.activation_keycode = data.get('activation_keycode', -1)
        self.chat_opener_keycode = data.get(
            'chat_opener_keycode', 20)  # Default is "T"

        self.solo = self.menu_keycode is None

        self.text = data.get('text', None)

        self.enabled = self.is_valid()

        self.root = None
        self.row = None
        self.menu_button = None
        self.activation_button = None
        self.chat_opener_button = None
        self.text_string_var = None
        self.delete_button = None

    def refresh_enabled(self) -> None:
        self.enabled = self.is_valid()
        logging.log(logging.INFO, f'Macro: {self.name} is enabled: {self.enabled}')

    def is_valid(self):
        return self.activation_keycode != -1 and self.text is not None and self.text != ''

    def play(self) -> None:
        if not self.enabled:
            return
        logging.log(logging.INFO, f'Playing macro: {self.name}')
        if self.chat_opener_keycode:
            press(self.chat_opener_keycode)
            release(self.chat_opener_keycode)
            sleep(0.05)  # TODO: Make this configurable

        speed: float = 0  # TODO: Make this configurable

        if not speed:
            for key in self.text:

                if key in to_shift:
                    key = to_shift[key]

                    press('shift')
                    press(key)
                    release(key)
                    release('shift')
                else:
                    press(key)
                    release(key)
                sleep(0.0001)
            press('enter')
            release('enter')
            return

        for key in self.text:
            if key in to_shift:
                key = to_shift[key]

                press('shift')
                press(key)

                sleep(speed)

                release(key)
                release('shift')

                sleep(speed)
            else:
                press(key)

                sleep(speed)

                release(key)

                sleep(speed)
            press('enter')
            release('enter')

    def to_dict(self) -> Optional[dict]:
        if not self.is_valid():
            return None

        out = {
            'activation_keycode': self.activation_keycode,
            'text': self.text
        }
        if self.menu_keycode != -1:
            out['menu_keycode'] = self.menu_keycode
        if self.chat_opener_keycode:
            out['chat_opener_keycode'] = self.chat_opener_keycode

        return out

    def __str__(self) -> str:
        return f'Macro: {self.name}'

    def __repr__(self) -> str:
        return f'Macro: {self.name}'

    def configure_tk(self, root: MainUI, row: Frame, menu_button: Button, activation_button: Button, chat_opener_button: Button, text_string_var: StringVar, delete_button: Button) -> None:
        self.root = root
        self.row = row
        self.menu_button = menu_button
        self.activation_button = activation_button
        self.chat_opener_button = chat_opener_button
        self.text_string_var = text_string_var
        self.delete_button = delete_button

        self.menu_button.configure(text=get_keyname(
            self.menu_keycode) if self.menu_keycode != -1 else '', command=self.set_menu_keycode)
        self.activation_button.configure(text=get_keyname(
            self.activation_keycode), command=self.set_activation_keycode)
        self.chat_opener_button.configure(text=get_keyname(
            self.chat_opener_keycode), command=self.set_chat_opener_keycode)
        self.text_string_var.set(self.text)
        self.text_string_var.trace("w", self.set_text)
        self.delete_button.configure(
            command=lambda self=self: root.delete_macro(self))

    def set_menu_keycode(self) -> None:
        """ Sets the menu keycode for the macro by waiting for a keypress. """
        assert self.root is not None
        assert self.menu_button is not None
        assert self.activation_button is not None

        old_menu = self.menu_keycode
        old_activation = self.activation_keycode
        # old = self.menu_button.cget('text')
        self.menu_button.configure(text='...')
        self.root.update()

        scan_code = None
        while scan_code is None:
            scan_code = read_event(suppress=True).scan_code
            logging.log(logging.INFO, f'Key Pressed! {scan_code}')

            if scan_code not in scancode_to_keyname:
                scan_code = None
                continue

            code, message = self._macros.verify_key_combo(
                scan_code, self.activation_keycode)
            if code != 0:
                self.activation_keycode = -1
                self.activation_button.configure(
                    text=get_keyname(self.activation_keycode))
                # self.root.show_error(message)

        if scan_code == 1:  # Esc
            self.menu_keycode = -1
            self.menu_button.configure(text='')
        else:
            self.menu_keycode = scan_code
            self.menu_button.configure(text=get_keyname(self.menu_keycode))

        self._macros.update_macro(old_menu, old_activation, self)

    def set_activation_keycode(self) -> None:
        """ Sets the activation keycode for the macro by waiting for a keypress. """
        assert self.root is not None
        assert self.activation_button is not None
        assert self.menu_button is not None

        old_menu = self.menu_keycode
        old_activation = self.activation_keycode
        self.activation_button.configure(text='...')
        self.root.update()

        scan_code = None
        while scan_code is None:
            scan_code = read_event(suppress=True).scan_code
            logging.log(logging.INFO, f'Key Pressed! {scan_code}')
            if scan_code not in scancode_to_keyname:
                scan_code = None
                continue

            code, message = self._macros.verify_key_combo(
                self.menu_keycode, scan_code)
            if code != 0:
                self.menu_keycode = -1
                self.menu_button.configure(text=get_keyname(self.menu_keycode))
                # self.root.show_error(message)

        self.activation_keycode = scan_code
        self.activation_button.configure(
            text=get_keyname(self.activation_keycode))
        self._macros.update_macro(old_menu, old_activation, self)

    def set_chat_opener_keycode(self) -> None:
        """ Sets the chat opener keycode for the macro by waiting for a keypress. """
        assert self.root is not None
        assert self.chat_opener_button is not None

        self.chat_opener_button.configure(text='...')
        self.root.update()

        scan_code = None
        while scan_code is None:
            scan_code = read_event(suppress=True).scan_code
            logging.log(logging.INFO, f'Key Pressed! {scan_code}')
            if scan_code not in scancode_to_keyname:
                scan_code = None

        self.chat_opener_keycode = scan_code
        self.chat_opener_button.configure(
            text=get_keyname(self.chat_opener_keycode))

    def set_text(self, name, index, mode) -> None:
        """ Sets the text for the macro. """
        assert self.text_string_var is not None

        self.text = self.text_string_var.get()
        self.name = self.text


class Macros:

    def __init__(self, filename: Optional[str]) -> None:
        self.menus: dict[int, dict[int, Macro]] = {}
        _menus: set[int] = set(self.menus.keys())
        

        if not filename:
            return

        for macro_name, macro_data in load(filename).items():
            macro = Macro(self, macro_name, macro_data)

            if macro.activation_keycode in _menus and macro.menu_keycode == -1:
                raise ValueError(
                    f'Activation keycode {macro.activation_keycode} is already in use by another macro.')

            self.insert_macro(macro)
        
        self.last_yaml = self.to_yaml()
    

    def arm_macros(self) -> None:
        """ Arms all valid macros. """
        for menu in self.menus.values():
            for macro in menu.values():
                macro.refresh_enabled()


    def has_changed(self) -> bool:
        try:
            return self.last_yaml != self.to_yaml()
        except Exception:
            return True
    

    def get_unique_scan_codes(self) -> set[int]:
        """ Returns a set of all scan codes used by any macro. """
        scan_codes = set()
        scan_codes.update(self.menus.keys())
        for menu in self.menus.values():
            scan_codes.update(menu.keys())
        scan_codes.discard(-1)
        return scan_codes

    def verify_key_combo(self, menu_keycode: int, activation_keycode: int) -> tuple[int, str]:
        """ Check if any of the macros share any invalid keycodes. 

        Returns:
            0: No errors
            1: Activation keycode is already in use by another macro
            2: Activation keycode is occupied by an existing menu
        """
        menu = self.menus.get(menu_keycode, {})
        if activation_keycode in menu:
            return 1, f'Activation keycode {activation_keycode} is already in use by another macro.'

        if menu_keycode == -1 and activation_keycode in self.menus:
            return 2, f'Activation keycode {activation_keycode} is occupied by an existing menu.'

        return 0, ''

    def insert_macro(self, macro: Macro) -> None:
        logging.log(logging.INFO, f'Loading macro {macro.name}')
        if macro.menu_keycode not in self.menus:
            logging.log(logging.INFO, 'Creating menu')
            self.menus[macro.menu_keycode] = {}

        logging.log(logging.INFO, 
            f'Inserting macro {macro.name} into menu {macro.menu_keycode} with activation keycode {macro.activation_keycode}')
        self.menus[macro.menu_keycode][macro.activation_keycode] = macro

    def update_macro(self, old_menu: int, old_active: int, macro: Macro) -> None:
        del self.menus[old_menu][old_active]
        self.insert_macro(macro)

    def get_macro(self, menu_keycode: Optional[int], activation_keycode: Optional[int]) -> Optional[Macro]:
        return \
            self.menus.get(menu_keycode or -1, {}) \
                      .get(activation_keycode or -1, None)
    
    def get_menu(self, menu_keycode: Optional[int]) -> Optional[dict[int, Macro]]:
        return self.menus.get(menu_keycode or -1, None)

    def remove_macro(self, macro: Macro) -> None:
        del self.menus[macro.menu_keycode][macro.activation_keycode]

    def add_macro(
        self,
        menu_keycode: Optional[int] = None,
        activation_keycode: Optional[int] = None,
        chat_opener_keycode: Optional[int] = 20,
        text: str = 'What a save!'
    ) -> Macro:
        logging.log(logging.INFO, 
            f'Adding macro with menu keycode {menu_keycode}, activation keycode {activation_keycode}, chat opener keycode {chat_opener_keycode}, and text {text}')
        macro = Macro(self, text, {
            'menu_keycode': menu_keycode or -1,
            'activation_keycode': activation_keycode or -1,
            'chat_opener_keycode': chat_opener_keycode or -1,
            'text': text
        })

        self.insert_macro(macro)
        return macro

    def get_all(self, keycode: Optional[int] = None) -> list[Macro]:
        """
            Return all macros first sorted by menu keycode, then by activation keycode.
        """

        out = []

        if keycode is None:
            for menu_keycode in sorted(self.menus.keys(), key=lambda c: get_keyname(c, '')):
                for macro in sorted(self.menus[menu_keycode].values(),
                                    key=lambda macro: get_keyname(macro.activation_keycode, '')):
                    out.append(macro)
            return out

        out = []
        for macro in sorted(self.menus.get(keycode, {}).values(),
                            key=lambda macro: get_keyname(macro.activation_keycode, '')):
            out.append(macro)
        return out

    def to_yaml(self, force=False) -> str:
        try:
            out = {}
            incomplete: list[Macro] = []
            for macro in self.get_all():
                mdict = macro.to_dict()
                if mdict:
                    if macro.name in out:
                        macro.name = f'{macro.name} ({macro.activation_keycode})'
                    out[macro.name] = mdict
                elif not force:
                    incomplete.append(macro)

            if incomplete and not force:
                raise MacroError(incomplete)

            return dump(out)
        except (YAMLSerializationError, YAMLValidationError, MarkedYAMLError):
            return ''
