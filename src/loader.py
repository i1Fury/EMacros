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
