"""
waterfall.py
Component 1: Temporal variability / waterfall spectrum display.

This script captures repeated PSD rows at a fixed center frequency and saves:
    figures/waterfall_<freq>MHz.png
    data/waterfall_<freq>MHz.npy
"""

import os
import sys
import time
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


def one_row(sdr, fs, nperseg=1024):
    """
    Capture one buffer and compute one PSD row.
    """
    x = np.asarray(sdr.rx())

    f, pxx = signal.welch(
        x,
        fs=fs,
        window="hann",
        nperseg=nperseg,
        return_onesided=False,
        scaling="density",
    )

    f = np.fft.fftshift(f)
    pxx = np.fft.fftshift(pxx)

    psd_db = 10 * np.log10(pxx + 1e-20)

    return f, psd_db


def run_waterfall(
    uri=config.PLUTO_URI,
    freq=2437e6,
    rate=config.DEFAULT_SAMPLE_RATE,
    duration=10.0,
    interval=0.1,
    gain=config.DEFAULT_GAIN_MODE,
    gain_db=config.DEFAULT_MANUAL_GAIN_DB,
    live=False,
):
    """
    Callable function used by main.py and by command line.
    """
    print(f"Connecting to Pluto at {uri} ...")

    sdr, used_uri = connect_pluto(uri)
    sdr.sample_rate = int(rate)
    sdr.rx_rf_bandwidth = int(rate)
    sdr.rx_lo = int(freq)
    sdr.rx_buffer_size = 2**16
    sdr.gain_control_mode_chan0 = gain

    if gain == "manual":
        sdr.rx_hardwaregain_chan0 = float(gain_db)

    sdr.rx()  # discard first buffer after tuning

    f_off, _ = one_row(sdr, float(rate))
    rf_mhz = (f_off + freq) / 1e6

    n_rows = max(1, int(duration / interval))

    print(
        f"Recording {duration:.1f} seconds at {freq / 1e6:.1f} MHz "
        f"({n_rows} rows, span {rate / 1e6:.1f} MHz) ..."
    )

    rows = []

    if live:
        plt.ion()
        fig, ax = plt.subplots(figsize=(11, 6))

    t0 = time.time()

    for i in range(n_rows):
        _, psd_db = one_row(sdr, float(rate))
        rows.append(psd_db)

        if live and (i % 3 == 0 or i == n_rows - 1):
            ax.clear()
            data = np.array(rows)

            ax.imshow(
                data,
                aspect="auto",
                origin="upper",
                extent=[rf_mhz[0], rf_mhz[-1], i * interval, 0],
            )

            ax.set_xlabel("Frequency (MHz)")
            ax.set_ylabel("Time (s ago)")
            ax.set_title(f"Live Waterfall @ {freq / 1e6:.1f} MHz")
            plt.pause(0.001)

        target = t0 + (i + 1) * interval
        sleep_time = target - time.time()

        if sleep_time > 0:
            time.sleep(sleep_time)

    data = np.array(rows)

    print(f"Captured {len(rows)} rows in {time.time() - t0:.1f} seconds.")

    if live:
        plt.ioff()
        plt.close(fig)

    fig, (ax_wf, ax_avg) = plt.subplots(
        2,
        1,
        figsize=(11, 8),
        sharex=True,
        gridspec_kw={"height_ratios": [3, 1]},
    )

    im = ax_wf.imshow(
        data,
        aspect="auto",
        origin="upper",
        extent=[rf_mhz[0], rf_mhz[-1], duration, 0],
    )

    ax_wf.set_ylabel("Time (seconds)")
    ax_wf.set_title(
        f"Spectrum Waterfall @ {freq / 1e6:.1f} MHz "
        f"(span {rate / 1e6:.1f} MHz)"
    )

    cbar = fig.colorbar(im, ax=ax_wf, pad=0.01)
    cbar.set_label("Power (dB)")

    avg = data.mean(axis=0)
    peak = data.max(axis=0)

    ax_avg.plot(rf_mhz, avg, linewidth=0.8, label="Average PSD")
    ax_avg.plot(rf_mhz, peak, linewidth=0.8, alpha=0.6, label="Peak Hold")

    ax_avg.set_xlabel("Frequency (MHz)")
    ax_avg.set_ylabel("PSD (dB)")
    ax_avg.grid(True, alpha=0.3)
    ax_avg.legend(fontsize=8, loc="upper right")

    plt.tight_layout()

    os.makedirs(config.SENSING_FIGURES_DIR, exist_ok=True)
    os.makedirs(config.SENSING_DATA_DIR, exist_ok=True)

    fig_path = os.path.join(
        config.SENSING_FIGURES_DIR,
        f"waterfall_{int(freq / 1e6)}MHz.png",
    )

    data_path = os.path.join(
        config.SENSING_DATA_DIR,
        f"waterfall_{int(freq / 1e6)}MHz.npy",
    )

    plt.savefig(fig_path, dpi=150)
    np.save(data_path, data)

    print(f"Saved figure -> {fig_path}")
    print(f"Saved data -> {data_path}")

    plt.show()

    return data


def main():
    parser = argparse.ArgumentParser(description="Waterfall / temporal spectrum capture.")

    parser.add_argument("--uri", default=config.PLUTO_URI, help="Pluto URI, e.g. ip:192.168.2.1")

    parser.add_argument("--freq", type=float, required=True, help="Center frequency in Hz")
    parser.add_argument("--rate", type=float, default=config.DEFAULT_SAMPLE_RATE)
    parser.add_argument("--duration", type=float, default=10.0)
    parser.add_argument("--interval", type=float, default=0.1)

    parser.add_argument("--gain", choices=["slow_attack", "manual"], default=config.DEFAULT_GAIN_MODE)
    parser.add_argument("--gain-db", type=float, default=config.DEFAULT_MANUAL_GAIN_DB)

    parser.add_argument("--live", action="store_true", help="Show live waterfall while recording")

    args = parser.parse_args()

    run_waterfall(
        uri=args.uri,
        freq=args.freq,
        rate=args.rate,
        duration=args.duration,
        interval=args.interval,
        gain=args.gain,
        gain_db=args.gain_db,
        live=args.live,
    )


if __name__ == "__main__":
    main()