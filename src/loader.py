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


from strictyaml import Map, Str, Float, Int, MapPattern, Optional
from strictyaml.representation import OrderedDict
from strictyaml import load as _load

from strictyaml import as_document


schema = MapPattern(Str(), Map({
    Optional("menu_keycode"): Int(),
    "activation_keycode": Int(),
    Optional("chat_opener_keycode"): Int(),
    "text": Str(),
    # Optional("delays"): MapPattern(Float(), Float())
}))
 # type: ignore

def load(filename: str) -> OrderedDict:
    stryaml = ''
    with open(filename, 'r') as f:
        stryaml = f.read()
    
    return _load(stryaml, schema).data # type: ignore

def dump(data: dict) -> str:
    return as_document(data, schema).as_yaml()
