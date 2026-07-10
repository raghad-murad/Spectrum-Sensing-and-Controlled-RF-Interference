"""
wideband_scan.py
Component 1: Wideband spectrum sensing using ADALM-PLUTO SDR.

This script scans a frequency band, computes a stitched PSD, detects occupied
channels, and saves:
    figures/scan_<LABEL>.png
    data/scan_<LABEL>.csv
    data/channels_<LABEL>.csv
"""

import os
import sys
import csv
import argparse
import numpy as np
import matplotlib.pyplot as plt
from scipy import signal
from pluto_utils import connect_pluto

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

try:
    import adi
except ImportError:
    print("ERROR: pyadi-iio not installed.")
    print("Install using: python -m pip install pyadi-iio pylibiio")
    sys.exit(1)


def scan_band(sdr, f_start, f_stop, fs, avg=8, overlap=0.25):
    """
    Sweep the LO across the band and stitch PSD measurements together.
    """
    step = fs * (1.0 - overlap)
    centers = np.arange(f_start + fs / 2, f_stop + fs / 2, step)

    all_freqs = []
    all_psd = []

    keep_frac = 0.8

    print(
        f"Scanning {f_start / 1e6:.1f} - {f_stop / 1e6:.1f} MHz "
        f"in {len(centers)} tiles ..."
    )

    for i, fc in enumerate(centers):
        sdr.rx_lo = int(fc)
        sdr.rx()  # discard first buffer after tuning

        psd_accum = None

        for _ in range(avg):
            x = np.asarray(sdr.rx())

            f, pxx = signal.welch(
                x,
                fs=fs,
                window="hann",
                nperseg=1024,
                return_onesided=False,
                scaling="density",
            )

            f = np.fft.fftshift(f)
            pxx = np.fft.fftshift(pxx)

            if psd_accum is None:
                psd_accum = pxx
            else:
                psd_accum += pxx

        psd_avg = psd_accum / avg
        psd_db = 10 * np.log10(psd_avg + 1e-20)

        rf = f + fc

        n = len(rf)
        lo = int(n * (1 - keep_frac) / 2)
        hi = int(n * (1 + keep_frac) / 2)

        all_freqs.append(rf[lo:hi])
        all_psd.append(psd_db[lo:hi])

        print(f"  tile {i + 1}/{len(centers)} @ {fc / 1e6:.2f} MHz")

    freqs = np.concatenate(all_freqs)
    psd = np.concatenate(all_psd)

    order = np.argsort(freqs)
    freqs = freqs[order]
    psd = psd[order]

    grid_lo = max(f_start, freqs[0])
    grid_hi = min(f_stop, freqs[-1])
    grid = np.arange(grid_lo, grid_hi, fs / 2048)

    psd_grid = np.interp(grid, freqs, psd)

    return grid, psd_grid


def detect_channels(freqs, psd_db, threshold_db=6.0, min_width_hz=200e3):
    """
    Detect occupied channels using:
        occupancy threshold = noise floor + threshold_db
    """
    noise_floor = np.median(psd_db)
    occupancy_threshold = noise_floor + threshold_db

    mask = psd_db > occupancy_threshold

    channels = []
    df = freqs[1] - freqs[0]

    i = 0
    n = len(mask)

    while i < n:
        if mask[i]:
            j = i

            while j < n and mask[j]:
                j += 1

            width = (j - i) * df

            if width >= min_width_hz:
                seg = psd_db[i:j]
                peak_local = int(np.argmax(seg))
                peak_idx = i + peak_local

                channels.append(
                    {
                        "f_start_MHz": freqs[i] / 1e6,
                        "f_stop_MHz": freqs[j - 1] / 1e6,
                        "center_MHz": (freqs[i] + freqs[j - 1]) / 2 / 1e6,
                        "width_MHz": width / 1e6,
                        "peak_MHz": freqs[peak_idx] / 1e6,
                        "peak_dB": float(psd_db[peak_idx]),
                        "above_floor_dB": float(psd_db[peak_idx] - noise_floor),
                    }
                )

            i = j
        else:
            i += 1

    return noise_floor, occupancy_threshold, channels


def plot_and_save(
    freqs,
    psd_db,
    noise_floor,
    occupancy_threshold,
    channels,
    label,
    band_name,
):
    """
    Plot:
        1. Measured PSD
        2. Noise Floor
        3. Occupancy Threshold
        4. Detected occupied regions
    """
    os.makedirs(config.SENSING_FIGURES_DIR, exist_ok=True)
    os.makedirs(config.SENSING_DATA_DIR, exist_ok=True)

    plt.figure(figsize=(12, 6))

    plt.plot(
        freqs / 1e6,
        psd_db,
        linewidth=0.7,
        label="Measured PSD",
    )

    plt.axhline(
        noise_floor,
        linestyle="--",
        linewidth=1,
        label=f"Noise Floor = {noise_floor:.1f} dB",
    )

    plt.axhline(
        occupancy_threshold,
        linestyle=":",
        linewidth=1.2,
        label=f"Occupancy Threshold = {occupancy_threshold:.1f} dB",
    )

    for ch in channels:
        plt.axvspan(
            ch["f_start_MHz"],
            ch["f_stop_MHz"],
            alpha=0.15,
        )

        plt.text(
            ch["center_MHz"],
            ch["peak_dB"] + 1,
            f"{ch['center_MHz']:.1f} MHz",
            ha="center",
            fontsize=7,
        )

    plt.xlabel("Frequency (MHz)")
    plt.ylabel("PSD (dB/Hz, relative)")
    plt.title(
        f"Spectrum Scan — {band_name}\n"
        f"{len(channels)} occupied channel(s) detected"
    )
    plt.grid(True, alpha=0.3)
    plt.legend(loc="upper right", fontsize=8)
    plt.tight_layout()

    fig_path = os.path.join(config.SENSING_FIGURES_DIR, f"scan_{label}.png")
    plt.savefig(fig_path, dpi=150)
    print(f"\nSaved plot -> {fig_path}")

    psd_csv = os.path.join(config.SENSING_DATA_DIR, f"scan_{label}.csv")

    with open(psd_csv, "w", newline="") as fp:
        writer = csv.writer(fp)
        writer.writerow(["frequency_MHz", "psd_dB"])

        for fr, p in zip(freqs, psd_db):
            writer.writerow([f"{fr / 1e6:.4f}", f"{p:.2f}"])

    print(f"Saved PSD -> {psd_csv}")

    channels_csv = os.path.join(config.SENSING_DATA_DIR, f"channels_{label}.csv")

    with open(channels_csv, "w", newline="") as fp:
        fields = [
            "center_MHz",
            "f_start_MHz",
            "f_stop_MHz",
            "width_MHz",
            "peak_MHz",
            "peak_dB",
            "above_floor_dB",
        ]

        writer = csv.DictWriter(fp, fieldnames=fields)
        writer.writeheader()

        for ch in channels:
            writer.writerow({k: round(ch[k], 3) for k in fields})

    print(f"Saved channel table -> {channels_csv}")

    print("\nDetected occupied channels:")
    print(f"{'center MHz':>12} {'width MHz':>12} {'peak dB':>10} {'above floor':>14}")

    for ch in channels:
        print(
            f"{ch['center_MHz']:>12.2f} "
            f"{ch['width_MHz']:>12.2f} "
            f"{ch['peak_dB']:>10.1f} "
            f"{ch['above_floor_dB']:>14.1f}"
        )

    plt.show()


def run_scan(
    uri=config.PLUTO_URI,
    band=None,
    start=None,
    stop=None,
    label=None,
    rate=config.DEFAULT_SAMPLE_RATE,
    avg=8,
    gain=config.DEFAULT_GAIN_MODE,
    gain_db=config.DEFAULT_MANUAL_GAIN_DB,
    threshold=6.0,
):
    """
    Callable function used by main.py and by command line.
    """
    if band is not None:
        selected_band = config.BANDS[band]
        f_start = selected_band["start"]
        f_stop = selected_band["stop"]
        output_label = band
        band_name = selected_band["name"]

    elif start is not None and stop is not None:
        f_start = start
        f_stop = stop
        output_label = label or f"{int(f_start / 1e6)}_{int(f_stop / 1e6)}"
        band_name = f"{f_start / 1e6:.0f}-{f_stop / 1e6:.0f} MHz"

    else:
        raise ValueError("Give either band or start/stop range.")

    print(f"Connecting to Pluto at {uri} ...")

    sdr, used_uri = connect_pluto(uri)
    sdr.sample_rate = int(rate)
    sdr.rx_rf_bandwidth = int(rate)
    sdr.rx_buffer_size = config.DEFAULT_RX_BUFFER_SIZE
    sdr.gain_control_mode_chan0 = gain

    if gain == "manual":
        sdr.rx_hardwaregain_chan0 = float(gain_db)

    freqs, psd_db = scan_band(
        sdr=sdr,
        f_start=f_start,
        f_stop=f_stop,
        fs=float(rate),
        avg=avg,
    )

    noise_floor, occupancy_threshold, channels = detect_channels(
        freqs=freqs,
        psd_db=psd_db,
        threshold_db=threshold,
    )

    plot_and_save(
        freqs=freqs,
        psd_db=psd_db,
        noise_floor=noise_floor,
        occupancy_threshold=occupancy_threshold,
        channels=channels,
        label=output_label,
        band_name=band_name,
    )

    return freqs, psd_db, channels


def main():
    parser = argparse.ArgumentParser(description="Wideband spectrum scanner.")

    parser.add_argument("--uri", default=config.PLUTO_URI, help="Pluto URI, e.g. ip:192.168.2.1")

    parser.add_argument("--band", choices=list(config.BANDS.keys()), help="Named band from config.py")
    parser.add_argument("--start", type=float, help="Custom start frequency in Hz")
    parser.add_argument("--stop", type=float, help="Custom stop frequency in Hz")
    parser.add_argument("--label", type=str, help="Output label for custom scan")

    parser.add_argument("--rate", type=float, default=config.DEFAULT_SAMPLE_RATE)
    parser.add_argument("--avg", type=int, default=8)

    parser.add_argument("--gain", choices=["slow_attack", "manual"], default=config.DEFAULT_GAIN_MODE)
    parser.add_argument("--gain-db", type=float, default=config.DEFAULT_MANUAL_GAIN_DB)

    parser.add_argument(
        "--threshold",
        type=float,
        default=6.0,
        help="dB above noise floor to count as occupied",
    )

    args = parser.parse_args()

    run_scan(
        uri=args.uri,
        band=args.band,
        start=args.start,
        stop=args.stop,
        label=args.label,
        rate=args.rate,
        avg=args.avg,
        gain=args.gain,
        gain_db=args.gain_db,
        threshold=args.threshold,
    )


if __name__ == "__main__":
    main()