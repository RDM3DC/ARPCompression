
# ARPCompression Adapter (for Adaptive-PI phases 15–18)

- **Lossless/log-safe:** fixed-point (2^44) + delta + zigzag varint + zlib, ideal for `log(p)` shards.
- **Optional lossy:** use your **ARPCompression.gpuc** quantizer for large arrays (e.g., H(t)) where slight loss is fine.

## Install
Just drop `arp_adapter/` (or the single-file `arp_adapter.py`) in your repo PYTHONPATH.

## Examples

### Compress / decompress log(p) shards
```bash
python -m arp_adapter.compress_logp  --in data/shards/logp_shard0001.npy --out data/shards_vzc/logp_shard0001
python -m arp_adapter.decompress_logp --in data/shards_vzc/logp_shard0001 --out data/recovered/logp_shard0001.npy
```

### Quantize / dequantize big arrays with GPUC
```bash
python -m arp_adapter.gpuc_quant   --in outputs_phase16/H.npy --bits 12 --out outputs_phase16/H_q.npz
python -m arp_adapter.gpuc_dequant --in outputs_phase16/H_q.npz --out outputs_phase16/H_restored.npy
```
