
import base64, json
from typing import Dict, List
from .encoder import encode as atc_encode
from .decoder import decode as atc_decode
from .arith import Model, Encoder, Decoder

ZERO_WIDTH = "\u200b"

# Punctuation codes as produced by the encoder:
# 0:none, 1:'.', 2:',', 3:'!', 4:'?', 5:';', 6:':', 7:other
ENDER_CODES = {1,3,4}

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

    # Split style components
    spaces = []; puncts = []; caps = []
    for b in style_bytes:
        s = b & 0b11
        p = (b >> 2) & 0b111
        c = (b >> 5) & 0b1
        spaces.append(s); puncts.append(p); caps.append(c)

    enc = Encoder()
    # carriers
    m_car = Model(base_size + len(ext_chars))
    for s in _to_symbols(carriers, ext_map):
        enc.encode(m_car, s)

    # spaces (single model; keep stream order compatibility)
    m_sp = Model(4)
    for s in spaces:
        enc.encode(m_sp, s)

    # puncts (single model)
    m_pu = Model(8)
    for p in puncts:
        enc.encode(m_pu, p)

    # caps with context on previous punct ender (we know puncts list already)
    m_ca_norm = Model(2)
    m_ca_after_end = Model(2)
    prev_punct = 0
    for i, c in enumerate(caps):
        mdl = m_ca_after_end if (prev_punct in ENDER_CODES) else m_ca_norm
        enc.encode(mdl, c)
        prev_punct = puncts[i]

    blob = enc.finish()
    return {
        "format": "ATC-AC2-v2",
        "n": len(style_bytes),
        "ext": "".join(ext_chars),
        "data_b64": base64.b64encode(blob).decode("ascii")
    }

def unpack(obj: Dict[str, str]) -> str:
    assert obj["format"] in ("ATC-AC2-v1", "ATC-AC2-v2")
    n = int(obj["n"])
    ext_chars = list(obj.get("ext",""))
    data = base64.b64decode(obj["data_b64"])

    dec = Decoder(data)
    base_size = len(BASE_ALPHABET)

    # carriers
    m_car = Model(base_size + len(ext_chars))
    carriers_sym = [dec.decode(m_car) for _ in range(n)]
    carriers = _to_carriers(carriers_sym, ext_chars)

    # spaces (single model; must match encoder order)
    m_sp = Model(4)
    spaces = [dec.decode(m_sp) for _ in range(n)]

    # puncts (single model)
    m_pu = Model(8)
    puncts = [dec.decode(m_pu) for _ in range(n)]

    # caps with context on previous punct ender
    m_ca_norm = Model(2)
    m_ca_after_end = Model(2)
    caps = [0]*n
    prev_punct = 0
    for i in range(n):
        mdl = m_ca_after_end if (prev_punct in ENDER_CODES) else m_ca_norm
        caps[i] = dec.decode(mdl)
        prev_punct = puncts[i]

    # rebuild style bytes
    style_bytes = bytearray(n)
    for i in range(n):
        b = (spaces[i] & 0b11) | ((puncts[i] & 0b111)<<2) | ((caps[i] & 0b1)<<5)
        style_bytes[i] = b

    pkg = {"carriers": carriers, "style_b64": base64.b64encode(bytes(style_bytes)).decode("ascii")}
    return atc_decode(pkg)
