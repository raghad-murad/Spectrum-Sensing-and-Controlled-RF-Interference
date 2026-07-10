"""
plot_results.py
Component 2 (analysis): compare link measurements (baseline / jammed / recovery)
and produce a comparison plot + summary table for the report.

Callable function used by main.py and by command line:
    run_compare(labels)
"""

import os
import sys
import csv
import argparse
import numpy as np
import matplotlib.pyplot as plt

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


def load(label):
    path = os.path.join(config.INTERFERENCE_DATA_DIR, f"link_{label}.csv")
    if not os.path.exists(path):
        print(f"  WARNING: {path} not found, skipping '{label}'")
        return None
    times, rtts = [], []
    with open(path) as fp:
        r = csv.DictReader(fp)
        for row in r:
            times.append(float(row["time_s"]))
            v = row["rtt_ms"]
            rtts.append(float(v) if v != "" else np.nan)
    return np.array(times), np.array(rtts)


def stats_for(rtts):
    valid = rtts[~np.isnan(rtts)]
    total = len(rtts)
    lost = total - len(valid)
    return {
        "loss_pct": 100.0 * lost / total if total else 0.0,
        "mean": np.nanmean(rtts) if len(valid) else np.nan,
        "median": np.nanmedian(rtts) if len(valid) else np.nan,
        "max": np.nanmax(rtts) if len(valid) else np.nan,
        "jitter": np.nanstd(rtts) if len(valid) else np.nan,
    }


def run_compare(labels):
    """
    Callable function used by main.py and by command line.
    Loads data/link_<label>.csv for each label and plots a comparison.
    """
    datasets = {}
    for lbl in labels:
        d = load(lbl)
        if d is not None:
            datasets[lbl] = d

    if not datasets:
        print("No data found. Run the measurement step first.")
        return

    colors = {"baseline": "green", "jammed": "red", "recovery": "steelblue"}

    fig, (ax_time, ax_bar) = plt.subplots(
        1, 2, figsize=(14, 5), gridspec_kw={"width_ratios": [2, 1]})

    # left: RTT over time
    for lbl, (t, rtt) in datasets.items():
        c = colors.get(lbl, None)
        ax_time.plot(t, rtt, ".-", markersize=3, linewidth=0.8,
                     color=c, label=lbl, alpha=0.8)
        lost_t = t[np.isnan(rtt)]
        if len(lost_t):
            ax_time.plot(lost_t, np.zeros_like(lost_t), "x",
                         color=c, markersize=5, alpha=0.5)
    ax_time.set_xlabel("Time (s)")
    ax_time.set_ylabel("Round-trip latency (ms)")
    ax_time.set_title("Ping latency over time\n(x markers = lost packets)")
    ax_time.grid(True, alpha=0.3)
    ax_time.legend()

    # right: summary bars
    labels_present = list(datasets.keys())
    means = [stats_for(datasets[l][1])["mean"] for l in labels_present]
    losses = [stats_for(datasets[l][1])["loss_pct"] for l in labels_present]
    bar_colors = [colors.get(l, "gray") for l in labels_present]

    x = np.arange(len(labels_present))
    ax_bar.bar(x, means, color=bar_colors, alpha=0.7)
    ax_bar.set_xticks(x)
    ax_bar.set_xticklabels(labels_present, rotation=15)
    ax_bar.set_ylabel("Mean RTT (ms)")
    ax_bar.set_title("Mean latency + packet loss")
    for i, (m, loss) in enumerate(zip(means, losses)):
        txt = f"{m:.1f} ms"
        if loss > 0:
            txt += f"\n{loss:.0f}% loss"
        ax_bar.text(i, m, txt, ha="center", va="bottom", fontsize=9)
    ax_bar.grid(True, alpha=0.3, axis="y")

    plt.tight_layout()
    os.makedirs(config.INTERFERENCE_FIGURES_DIR, exist_ok=True)
    fig_path = os.path.join(config.INTERFERENCE_FIGURES_DIR, "interference_comparison.png")
    plt.savefig(fig_path, dpi=150)
    print(f"Saved plot -> {fig_path}")

    summ_path = os.path.join(config.INTERFERENCE_DATA_DIR, "interference_summary.csv")
    with open(summ_path, "w", newline="") as fp:
        w = csv.writer(fp)
        w.writerow(["label", "loss_pct", "mean_ms", "median_ms",
                    "max_ms", "jitter_ms"])
        for lbl in labels_present:
            s = stats_for(datasets[lbl][1])
            w.writerow([lbl, f"{s['loss_pct']:.1f}", f"{s['mean']:.2f}",
                        f"{s['median']:.2f}", f"{s['max']:.2f}",
                        f"{s['jitter']:.2f}"])
    print(f"Saved table -> {summ_path}")

    print("\nSummary:")
    print(f"{'label':>12} {'loss%':>7} {'mean':>8} {'median':>8} "
          f"{'max':>8} {'jitter':>8}")
    for lbl in labels_present:
        s = stats_for(datasets[lbl][1])
        print(f"{lbl:>12} {s['loss_pct']:>7.1f} {s['mean']:>8.2f} "
              f"{s['median']:>8.2f} {s['max']:>8.2f} {s['jitter']:>8.2f}")

    plt.show()


def main():
    p = argparse.ArgumentParser(description="Compare interference measurements.")
    p.add_argument("--labels", nargs="+", required=True)
    args = p.parse_args()
    run_compare(args.labels)


if __name__ == "__main__":
    main()