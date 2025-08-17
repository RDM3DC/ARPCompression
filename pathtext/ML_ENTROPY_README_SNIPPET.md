### ML-Entropy Reference vs Iterations

Below we compare our iteration milestones against an information-theoretic reference computed on the same paragraph and sine path.

- **H₀(text):** zero‑order entropy of the paragraph (lower bound for a good coder)
- **Entropy(path):** H(dx)+H(dy) on RDP‑simplified anchors at ε=5 px
- **Reference line:** H₀(text) + entropy(path), **no** dictionary/GPUC gains

On this sample, the reference is **≈ 6.13 bpc**. Our iterations surpass it after adding **multi‑level dictionary + GPUC**, which exploit structure beyond the H₀/path model.

Artifacts:
- `pathtext/ml_entropy_bound.csv` (numbers)
- `pathtext/ml_entropy_bound.png` (bar chart)
- `pathtext/iter_milestones.csv` (targets & measured points)
- `pathtext/iter_vs_entropy.png` (overlay figure)
