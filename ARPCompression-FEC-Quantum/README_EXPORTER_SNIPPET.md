## Export quantum plots to ATCP3

Package CSV traces and heatmaps into a single **ATC‑PATH v3** file with an SVG preview.

**Trace (curved text on your measured curve):**
```bash
python tools/export_atcp3.py --mode trace --csv data/2q_gate_trace.csv   --xcol 0 --ycol 1 --text "Rabi sweep (J028 lc090)"   --out artifacts/rabi.atcp3 --svg artifacts/rabi.svg --rdp 3.0
```

**Heatmap (6‑bit GPUC blob + sine guide):**
```bash
python tools/export_atcp3.py --mode heatmap --csv data/GHZ_fidelity_map.csv   --text "GHZ fidelity heatmap" --out artifacts/ghz.atcp3 --svg artifacts/ghz.svg
```
