"""
ATC encoder: text -> {"carriers": str, "style_b64": str}
"""
import argparse, base64, json, sys
from typing import Dict, List, Tuple
from .utils import make_style_byte, pack_style_bytes, PUNCT2CODE
ZERO_WIDTH = "\u200b"  # zero-width carrier

# allowed punctuation we encode by attaching to the previous carrier char
PUNCT_SET = set([".", ",", "!", "?", ";", ":"])

def _flush_spaces(spaces_run: int) -> List[int]:
    """
    Returns a list of 2-bit chunks (each 0..3) summing to spaces_run,
    to be consumed by successive carriers.
    """
    chunks = []
    while spaces_run > 3:
        chunks.append(3)
        spaces_run -= 3
    chunks.append(spaces_run)
    return chunks

def encode(text: str) -> Dict[str, str]:
    carriers: List[str] = []
    style_bytes: List[int] = []

    from collections import deque
    spaces_queue = deque()  # queue of 2-bit chunks of spaces to assign (0..3 each)
    last_carrier_idx = None      # index of last pushed carrier to attach punctuation

    i = 0
    while i < len(text):
        ch = text[i]

        # Handle spaces: accumulate run and skip visible emission
        if ch == " ":
            # accumulate spaces as 2-bit chunks into a queue
            # we only push chunks when we see a non-space carrier
            if not spaces_queue or spaces_queue[-1] == 3:
                spaces_queue.append(1)
            else:
                spaces_queue[-1] += 1
            i += 1
            continue

        # Handle punctuation attached AFTER the previous carrier (postfix punctuation)
        if ch in PUNCT_SET:
            # collect full run of consecutive punctuation
            run = []
            while i < len(text) and text[i] in PUNCT_SET:
                run.append(text[i])
                i += 1
            if last_carrier_idx is None:
                # Punctuation at start: represent via zero-width carriers
                for p in run:
                    carriers.append(ZERO_WIDTH)
                    style_bytes.append(make_style_byte(spaces_before=0, punct_after_code=PUNCT2CODE[p], capitalize_self=0))
            else:
                # Attach first to previous carrier, extras as zero-width carriers
                first = True
                for p in run:
                    if first:
                        b = style_bytes[last_carrier_idx]
                        b = (b & 0b11100011) | ((PUNCT2CODE[p] & 0b111) << 2)
                        style_bytes[last_carrier_idx] = b
                        first = False
                    else:
                        carriers.append(ZERO_WIDTH)
                        style_bytes.append(make_style_byte(spaces_before=0, punct_after_code=PUNCT2CODE[p], capitalize_self=0))
            continue

        # visible letters/payload chars become carriers; normalize to lowercase
        base = ch
        cap_flag = 0
        if "A" <= ch <= "Z":
            base = ch.lower()
            cap_flag = 1

        # Pre-flush any leading space chunks beyond one using zero-width carriers
        while len(spaces_queue) > 1:
            sb = spaces_queue.popleft()
            carriers.append(ZERO_WIDTH)
            style_bytes.append(make_style_byte(spaces_before=sb, punct_after_code=0, capitalize_self=0))
        # allocate one chunk of spaces_before from queue (0 if empty)
        if spaces_queue:
            spaces_before = spaces_queue.popleft()
        else:
            spaces_before = 0

        b = make_style_byte(spaces_before=spaces_before, punct_after_code=0, capitalize_self=cap_flag)
        carriers.append(base)
        style_bytes.append(b)
        last_carrier_idx = len(style_bytes) - 1
        i += 1

    # If spaces_buffer remains at end, we cannot represent trailing spaces without a trailing carrier.
    # We drop trailing spaces (typical visual semantics). Optionally, could append a sentinel.

    carriers_str = "".join(carriers)
    style_blob = pack_style_bytes(style_bytes)
    style_b64 = base64.b64encode(style_blob).decode("ascii")
    return {"carriers": carriers_str, "style_b64": style_b64}

def main():
    ap = argparse.ArgumentParser(description="Adaptive Text Compression (ATC) encoder")
    ap.add_argument("--text", type=str, help="Input text to encode")
    ap.add_argument("--infile", type=str, help="Read text from a file (mutually exclusive with --text)")
    ap.add_argument("--out", type=str, default="-", help="Path to write JSON package (or '-' for stdout)")
    args = ap.parse_args()

    if (args.text is None) == (args.infile is None):
        print("Provide exactly one of --text or --infile", file=sys.stderr)
        sys.exit(1)

    text = args.text if args.text is not None else open(args.infile, "r", encoding="utf-8").read()
    pkg = encode(text)
    out_json = json.dumps(pkg, ensure_ascii=False, indent=2)

    if args.out == "-" or args.out is None:
        print(out_json)
    else:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(out_json)

if __name__ == "__main__":
    main()
