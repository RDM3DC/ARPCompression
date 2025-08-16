# Adaptive Text Compression (ATC) — Prototype

This repo demonstrates **overlay compression** for text: we remove visible redundancy (like spaces/punctuation/case)
and **embed it into per-character style bits**. The transport format is:
- `carriers`: a plain Unicode string (no spaces, normalized lowercase)
- `style_bytes`: a byte per carrier character (base64-encoded in JSON)

This is a **lossless** round-trip for typical English text with spaces and common punctuation.

## Bit layout (per character)

```
bit 0-1: spaces_before (0..3)          # number of spaces inserted before this char
bit 2-4: punct_after  (0: none,
                       1: '.', 2: ',', 3: '!', 4: '?', 5: ';', 6: ':')
bit 5  : capitalize_self (0/1)          # if 1, uppercase this char in decode
bit 6  : reserved
bit 7  : reserved
```

We **strip spaces** and **lowercase** during encoding. We **store** spaces/case/punctuation in style bits,
achieving an **overlay-style compression**: fewer visible characters, same information.

> This is a research prototype of the idea you proposed: *characters as multi-channel tokens*.
> Future versions can encode grammar tags, word boundaries, or even semantics into the style byte(s).

## Quickstart

```bash
pip install -e .
python -m atc.examples.demo
```

## Python API

```python
from atc.encoder import encode
from atc.decoder import decode

text = "I am in it, okay?  YES!"
pkg = encode(text)
restored = decode(pkg)
assert text == restored
```

## CLI

```bash
# Encode
python -m atc.encoder --text "I am in it, okay?  YES!" --out /tmp/atc.json

# Decode
python -m atc.decoder --in /tmp/atc.json
```

## Transport format (JSON)

```json
{
  "carriers": "iamiinitoakyyes",
  "style_b64": "...."  # base64-encoded bytes, one per carrier char
}
```

## Notes & Roadmap

- Current scheme targets ASCII letters + basic punctuation and spaces.
- Multi-space runs >3 are encoded across successive carriers (rolling budget of 2 bits each).
- Extend to multi-byte style fields, grammatical tags, or language-specific compaction.
- Add steganographic mode using zero-width codepoints for transport (optional and careful!).
- Optional real styled text renderer (e.g., HTML/CSS) mapping style bits to **actual** visual styles.
