
import base64, json
from typing import Dict, List
from .encoder import encode as atc_encode
from .decoder import decode as atc_decode
from .utils import unpack_style_bytes, parse_style_byte
from .rc import Model, RangeEncoder, RangeDecoder

ZERO_WIDTH = "\u200b"

BASE_ALPHABET = {**{chr(ord('a')+i): i for i in range(26)},
                 **{str(i): 26+i for i in range(10)},
                 ZERO_WIDTH: 36}
def _rev_base():
    return {v:k for k,v in BASE_ALPHABET.items()}

def _carriers_to_symbols(carriers: str, ext_map: Dict[str,int]) -> List[int]:
    sym = []
    for ch in carriers:
        if ch in BASE_ALPHABET:
            sym.append(BASE_ALPHABET[ch])
        elif ch in ext_map:
            sym.append(ext_map[ch])
        else:
            raise ValueError(f'Unsupported carrier char (not in base or ext): {repr(ch)}')
    return sym

def _symbols_to_carriers(symbols: List[int], ext_list: List[str]) -> str:
    rev = _rev_base()
    base_size = len(BASE_ALPHABET)
    out = []
    for s in symbols:
        if s in rev:
            out.append(rev[s])
        else:
            idx = s - base_size
            out.append(ext_list[idx])
    return "".join(out)

def pack(text: str) -> Dict[str, str]:
    pkg = atc_encode(text)
    carriers = pkg["carriers"]
    style_bytes = base64.b64decode(pkg["style_b64"])

    # Build dynamic extension alphabet for any carriers not in base
    ext_chars = []
    base_keys = set(BASE_ALPHABET.keys())
    for ch in carriers:
        if ch not in base_keys and ch not in ext_chars:
            ext_chars.append(ch)
    base_size = len(BASE_ALPHABET)
    ext_map = {ch: base_size + i for i, ch in enumerate(ext_chars)}

    # Split style bits
    spaces, puncts, caps = [], [], []
    for b in style_bytes:
        s, p, c = parse_style_byte(b)
        spaces.append(s); puncts.append(p); caps.append(c)

    # Arithmetic-code each stream adaptively
    enc = RangeEncoder()
    # carriers
    m_car = Model(base_size + len(ext_chars))
    for s in _carriers_to_symbols(carriers, ext_map):
        enc.encode_symbol(m_car, s)
    # spaces
    m_sp = Model(4)
    for s in spaces: enc.encode_symbol(m_sp, s)
    # puncts
    m_pu = Model(8)
    for s in puncts: enc.encode_symbol(m_pu, s)
    # caps
    m_ca = Model(2)
    for s in caps: enc.encode_symbol(m_ca, s)

    blob = enc.finish()
    return {
        "format": "ATC-AC-v1",
        "n": len(style_bytes),
        "ext": "".join(ext_chars),  # store extension chars as a string
        "data_b64": base64.b64encode(blob).decode("ascii")
    }

def unpack(packed: Dict[str, str]) -> str:
    assert packed["format"] == "ATC-AC-v1"
    n = int(packed["n"])
    ext_chars = list(packed.get("ext", ""))
    data = base64.b64decode(packed["data_b64"])

    dec = RangeDecoder(data)
    base_size = len(BASE_ALPHABET)
    # carriers (n)
    m_car = Model(base_size + len(ext_chars))
    carriers_sym = [dec.decode_symbol(m_car) for _ in range(n)]
    carriers = _symbols_to_carriers(carriers_sym, ext_chars)

    # spaces (n), puncts (n), caps (n)
    m_sp = Model(4)
    spaces = [dec.decode_symbol(m_sp) for _ in range(n)]
    m_pu = Model(8)
    puncts = [dec.decode_symbol(m_pu) for _ in range(n)]
    m_ca = Model(2)
    caps = [dec.decode_symbol(m_ca) for _ in range(n)]

    # rebuild style bytes
    style_bytes = bytearray(n)
    for i in range(n):
        b = (spaces[i] & 0b11) | ((puncts[i] & 0b111)<<2) | ((caps[i] & 0b1)<<5)
        style_bytes[i] = b

    pkg = {"carriers": carriers, "style_b64": base64.b64encode(bytes(style_bytes)).decode("ascii")}
    return atc_decode(pkg)
