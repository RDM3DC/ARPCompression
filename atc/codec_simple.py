
import base64, zlib
from typing import Dict, List
from .encoder import encode as atc_encode
from .decoder import decode as atc_decode
from .utils import parse_style_byte
from .bitpack import pack_bits, unpack_bits

ZERO_WIDTH = "\u200b"
BASE_ALPHABET = {**{chr(ord('a')+i): i for i in range(26)},
                 **{str(i): 26+i for i in range(10)},
                 ZERO_WIDTH: 36}
def _rev_base():
    return {v:k for k,v in BASE_ALPHABET.items()}

def _to_symbols(carriers: str, ext_map):
    for ch in carriers:
        if ch in BASE_ALPHABET:
            yield BASE_ALPHABET[ch]
        else:
            yield ext_map[ch]

def _to_carriers(symbols, ext_list):
    rev = _rev_base()
    base_size = len(BASE_ALPHABET)
    out = []
    for s in symbols:
        if s in rev: out.append(rev[s])
        else: out.append(ext_list[s - base_size])
    return "".join(out)

def pack(text: str) -> Dict[str, str]:
    pkg = atc_encode(text)
    carriers = pkg["carriers"]
    style_bytes = base64.b64decode(pkg["style_b64"])

    # Build ext alphabet
    base_keys = set(BASE_ALPHABET.keys())
    ext_chars = []
    for ch in carriers:
        if ch not in base_keys and ch not in ext_chars:
            ext_chars.append(ch)
    base_size = len(BASE_ALPHABET)
    ext_map = {ch: base_size + i for i, ch in enumerate(ext_chars)}

    # Streams
    car_syms = list(_to_symbols(carriers, ext_map))
    # style components
    spaces = []; puncts = []; caps = []
    for b in style_bytes:
        s = b & 0b11
        p = (b >> 2) & 0b111
        c = (b >> 5) & 0b1
        spaces.append(s); puncts.append(p); caps.append(c)

    # Bit-pack carriers at 6 bits (covers up to 64 symbols)
    car_packed = pack_bits(car_syms, 6)
    # Bit-pack styles at 6 bits (2+3+1) by recombining as 6-bit codes
    style_syms = [ (spaces[i] | (puncts[i]<<2) | (caps[i]<<5)) for i in range(len(spaces)) ]
    sty_packed = pack_bits(style_syms, 6)

    # Concatenate and compress
    header = {
        "format": "ATC-BITZ-v1",
        "n": len(style_syms),
        "ext": "".join(ext_chars),
        "car_len": len(car_packed),
        "sty_len": len(sty_packed)
    }
    payload = car_packed + sty_packed
    comp = zlib.compress(payload, level=9)
    return {
        "header": header,
        "data_b64": base64.b64encode(comp).decode("ascii")
    }

def unpack(obj: Dict[str, str]) -> str:
    header = obj["header"]
    n = int(header["n"])
    ext_chars = list(header.get("ext",""))
    car_len = int(header["car_len"])
    comp = base64.b64decode(obj["data_b64"])
    payload = zlib.decompress(comp)
    car_packed = payload[:car_len]
    sty_packed = payload[car_len:]

    car_syms = unpack_bits(car_packed, n, 6)
    style_syms = unpack_bits(sty_packed, n, 6)
    # split style syms
    spaces = [ s & 0b11 for s in style_syms ]
    puncts = [ (s>>2) & 0b111 for s in style_syms ]
    caps   = [ (s>>5) & 0b1 for s in style_syms ]

    carriers = _to_carriers(car_syms, ext_chars)

    # rebuild style bytes
    style_bytes = bytearray(n)
    for i in range(n):
        b = (spaces[i] & 0b11) | ((puncts[i] & 0b111)<<2) | ((caps[i] & 0b1)<<5)
        style_bytes[i] = b

    pkg = {
        "carriers": carriers,
        "style_b64": base64.b64encode(bytes(style_bytes)).decode("ascii")
    }
    return atc_decode(pkg)
