"""
iperf_measure.py
Component 2 (measurement, alternative to ping): measure Wi-Fi THROUGHPUT
using iperf3 instead of ping latency.

Why: a single ping packet per second can slip through the gaps between jammer
bursts and show little or no effect, especially on modern routers with good
interference handling. A continuous data stream (iperf3) is far more sensitive
to interference because it needs the channel to be clear continuously to
sustain high throughput -- any jamming immediately shows up as a drop in
Mbit/s and a rise in retransmissions.

*** SETUP REQUIRED (one-time) ***
1. Install iperf3 on BOTH machines:
     Windows : download iperf3.exe from https://iperf.fr/iperf-download.php
               (or `choco install iperf3`), put it on PATH.
     Linux   : sudo apt install iperf3
     macOS   : brew install iperf3

2. On one machine (can be your router if it supports it, or any second
   laptop/phone on the same Wi-Fi) run the SERVER:
     iperf3 -s

3. On the laptop under test (the "victim" whose Wi-Fi you are jamming) run
   this script as the CLIENT, pointing --target at the server's IP.

Callable function used by main.py and by command line:
    run_iperf(target, duration, label, reverse)
"""

import os
import sys
import csv
import json
import argparse
import subprocess
import shutil

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


def check_iperf3_available():
    """Return True if the iperf3 binary is reachable on PATH."""
    return shutil.which("iperf3") is not None


"""
measure_link.py
Component 2 (measurement): measure Wi-Fi link latency / packet loss / jitter,
so you can quantify how the jammer degrades a link you own.

Run this on the VICTIM device (a phone/laptop on YOUR Wi-Fi). It does not use
the Pluto at all -- it just pings your router.

Callable function used by main.py and by command line:
    run_measure(target, duration, interval, label)
"""

import os
import sys
import csv
import time
import argparse
import subprocess
import platform
import re
import numpy as np

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


def ping_once(target, timeout_ms=1000):
    """Send a single ping. Return round-trip time in ms, or None on loss."""
    system = platform.system().lower()
    if system == "windows":
        cmd = ["ping", "-n", "1", "-w", str(timeout_ms), target]
    else:
        cmd = ["ping", "-c", "1", "-W", str(max(1, timeout_ms // 1000)), target]

    try:
        out = subprocess.run(cmd, capture_output=True, text=True,
                             timeout=timeout_ms / 1000 + 2)
        text = out.stdout.lower()
        # windows "time<1ms" means sub-millisecond; check before the regex
        if "time<1ms" in text.replace(" ", ""):
            return 0.5
        # windows "time=12ms" / linux "time=12.3 ms"
        m = re.search(r"time[=<]\s*([\d.]+)\s*ms", text)
        if m:
            return float(m.group(1))
        return None
    except Exception:
        return None


def measure(target, duration, interval=0.2):
    """Ping repeatedly for `duration` seconds. Return list of (t, rtt_or_None)."""
    samples = []
    t0 = time.time()
    n = 0
    while time.time() - t0 < duration:
        t = time.time() - t0
        rtt = ping_once(target)
        samples.append((t, rtt))
        n += 1
        status = f"{rtt:.1f} ms" if rtt is not None else "LOST"
        print(f"\r  [{t:5.1f}s] ping {n:4d}: {status:>10}   ",
              end="", flush=True)
        nxt = t0 + n * interval
        s = nxt - time.time()
        if s > 0:
            time.sleep(s)
    print()
    return samples


def summarize(samples):
    rtts = [r for _, r in samples if r is not None]
    total = len(samples)
    lost = total - len(rtts)
    return {
        "n_pings": total,
        "n_lost": lost,
        "loss_pct": 100.0 * lost / total if total else 0.0,
        "rtt_mean_ms": float(np.mean(rtts)) if rtts else float("nan"),
        "rtt_median_ms": float(np.median(rtts)) if rtts else float("nan"),
        "rtt_max_ms": float(np.max(rtts)) if rtts else float("nan"),
        "rtt_min_ms": float(np.min(rtts)) if rtts else float("nan"),
        "jitter_ms": float(np.std(rtts)) if rtts else float("nan"),
    }


def run_measure(target, duration=30, interval=0.2, label="run"):
    """
    Callable function used by main.py and by command line.
    Pings `target` for `duration` seconds and saves results under `label`.
    """
    print("=" * 60)
    print(f"  LINK MEASUREMENT — '{label}'")
    print(f"  target={target}  duration={duration:.0f}s")
    print("=" * 60)

    samples = measure(target, duration, interval)
    stats = summarize(samples)

    print("\nResults:")
    print(f"  pings sent   : {stats['n_pings']}")
    print(f"  packet loss  : {stats['loss_pct']:.1f}%  ({stats['n_lost']} lost)")
    print(f"  RTT mean     : {stats['rtt_mean_ms']:.2f} ms")
    print(f"  RTT median   : {stats['rtt_median_ms']:.2f} ms")
    print(f"  RTT max      : {stats['rtt_max_ms']:.2f} ms")
    print(f"  jitter (std) : {stats['jitter_ms']:.2f} ms")

    os.makedirs(config.INTERFERENCE_DATA_DIR, exist_ok=True)
    raw = os.path.join(config.INTERFERENCE_DATA_DIR, f"link_{label}.csv")
    with open(raw, "w", newline="") as fp:
        w = csv.writer(fp)
        w.writerow(["time_s", "rtt_ms"])
        for t, r in samples:
            w.writerow([f"{t:.3f}", "" if r is None else f"{r:.3f}"])
    print(f"\nSaved raw     -> {raw}")

    summ = os.path.join(config.INTERFERENCE_DATA_DIR, f"summary_{label}.csv")
    with open(summ, "w", newline="") as fp:
        w = csv.DictWriter(fp, fieldnames=list(stats.keys()))
        w.writeheader()
        w.writerow(stats)
    print(f"Saved summary -> {summ}")
    return stats


def main():
    p = argparse.ArgumentParser(description="Measure Wi-Fi link latency/loss.")
    p.add_argument("--target", required=True,
                   help="IP to ping (router gateway, e.g. 192.168.1.1)")
    p.add_argument("--duration", type=float, default=30)
    p.add_argument("--interval", type=float, default=0.2)
    p.add_argument("--label", required=True,
                   help="baseline / jammed / recovery / ...")
    args = p.parse_args()
    run_measure(target=args.target, duration=args.duration,
                interval=args.interval, label=args.label)


if __name__ == "__main__":
    main()