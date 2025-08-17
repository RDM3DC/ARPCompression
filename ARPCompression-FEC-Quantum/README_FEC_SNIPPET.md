## Resilient PATHTEXT (FEC)

We add *optional* forward‑error‑correction to path segments for flaky links / AR‑style overlays.

**Format tweaks (ATCP3 v3.1)**  
- Segment paths every 256B with `RESYNC/32` ops.
- Per‑segment **CRC16** for detection.  
- Optional **RS(255,239)** parity or **LDPC‑UEP** for correction.  
- Geometric concealment (linear/arc bridging) when decode fails.

**CLI (bench):**
```bash
python bench/fec_bench.py --file pathtext/paragraph.atcp2 --mode rs   --p 0.01 0.03 0.05 --seg_size 256 --rs_t_bits 16 --out_csv fec_results_rs.csv

python bench/fec_bench.py --file pathtext/paragraph.atcp2 --mode crc   --p 0.01 0.03 0.05 --seg_size 256 --out_csv fec_results_crc.csv
```
Columns: `p, FER, decode_ms`. Post‑FEC **bpc** ≈ base_bpc×(1+overhead).
