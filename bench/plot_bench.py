
import argparse, pandas as pd, matplotlib.pyplot as plt
from pathlib import Path

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    ap.add_argument("--out", default="bench_plot.png")
    args = ap.parse_args()
    df = pd.read_csv(args.csv)
    # aggregate per codec
    agg = df.groupby("codec")["size"].sum().reset_index()
    plt.figure(figsize=(6,4))
    plt.bar(agg["codec"], agg["size"])
    plt.ylabel("Total bytes (sum over files)")
    plt.title("Corpus size by codec")
    plt.tight_layout()
    plt.savefig(args.out, dpi=150)

if __name__ == "__main__":
    main()
