import csv
import numpy as np
import matplotlib.pyplot as plt
from cmc.one_d import encode_1d, decode_1d


def psnr(x, y):
    mse = np.mean((x - y) ** 2)
    if mse == 0:
        return 100.0
    peak = np.max(np.abs(x))
    return 20 * np.log10(peak / np.sqrt(mse))


def sweep(n=1000,
          taus=(0.0,),
          max_errs=(0.002,),
          alphas=(0.1, 0.2, 0.3),
          mus=(0.005, 0.01, 0.02)):
    signals = {
        "sin": np.sin(np.linspace(0, 4 * np.pi, n)).astype(np.float32),
        "ramp": np.linspace(0, 1, n).astype(np.float32),
    }
    rd_rows = []
    bias_rows = []
    for name, x in signals.items():
        for tau in taus:
            for max_err in max_errs:
                pkg = encode_1d(x, tau=tau, max_err=max_err)
                K = len(pkg["anchors"])
                for alpha in alphas:
                    for mu in mus:
                        y = decode_1d(pkg, n=n, alpha=alpha, mu=mu)
                        ps = psnr(x, y)
                        rd_rows.append({
                            "signal": name,
                            "n": n,
                            "tau": tau,
                            "max_err": max_err,
                            "alpha": alpha,
                            "mu": mu,
                            "K": K,
                            "PSNR_dB": ps,
                        })
                        bias_rows.append({
                            "signal": name,
                            "n": n,
                            "tau": tau,
                            "max_err": max_err,
                            "alpha": alpha,
                            "mu": mu,
                            "alpha_over_mu": alpha / mu,
                            "K": K,
                            "PSNR_dB": ps,
                            "max_abs_e": float(np.max(np.abs(x - y))),
                        })
    return rd_rows, bias_rows


def write_csv(fname, rows, fieldnames):
    with open(fname, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def plot_rd(rd_rows):
    import itertools
    # group by signal
    for name in sorted(set(r["signal"] for r in rd_rows)):
        plt.figure()
        sub = [r for r in rd_rows if r["signal"] == name]
        for alpha in sorted(set(r["alpha"] for r in sub)):
            xs = [r["mu"] for r in sub if r["alpha"] == alpha]
            ys = [r["PSNR_dB"] for r in sub if r["alpha"] == alpha]
            plt.plot(xs, ys, marker="o", label=f"alpha={alpha}")
        plt.xlabel("mu")
        plt.ylabel("PSNR (dB)")
        plt.title(f"{name} rate-distortion")
        plt.legend()
        plt.savefig(f"{name}_rd.png", dpi=200)
        plt.close()


def plot_bias(bias_rows):
    for name in sorted(set(r["signal"] for r in bias_rows)):
        plt.figure()
        sub = [r for r in bias_rows if r["signal"] == name]
        xs = [r["alpha_over_mu"] for r in sub]
        ys = [r["max_abs_e"] for r in sub]
        plt.plot(xs, ys, marker="o")
        plt.xlabel("alpha/mu")
        plt.ylabel("max |error|")
        plt.title(f"{name} bias vs alpha/mu")
        plt.savefig(f"{name}_bias_vs_alpha_over_mu.png", dpi=200)
        plt.close()


if __name__ == "__main__":
    rd_rows, bias_rows = sweep()
    write_csv(
        "cmc_rd.csv",
        rd_rows,
        ["signal", "n", "tau", "max_err", "alpha", "mu", "K", "PSNR_dB"],
    )
    write_csv(
        "cmc_bias.csv",
        bias_rows,
        [
            "signal",
            "n",
            "tau",
            "max_err",
            "alpha",
            "mu",
            "alpha_over_mu",
            "K",
            "PSNR_dB",
            "max_abs_e",
        ],
    )
    plot_rd(rd_rows)
    plot_bias(bias_rows)
