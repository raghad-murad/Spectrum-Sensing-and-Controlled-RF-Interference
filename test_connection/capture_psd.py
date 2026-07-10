"""
capture_psd.py
==============
Component 1 (basic): capture ONE snapshot at a single center frequency and
plot its Power Spectral Density (PSD).

This is the simplest useful sensing script. It shows the 2 MHz of spectrum
centered on whatever frequency you pick. Great for a first look and for
watching the interference signal later.

Usage examples:
    # Look at the middle of the 2.4 GHz ISM band
    python sensing/capture_psd.py --freq 2437e6

    # Look at a GSM 900 downlink carrier region
    python sensing/capture_psd.py --freq 947e6

    # Fixed (manual) gain so power levels are comparable between runs
    python sensing/capture_psd.py --freq 2437e6 --gain manual --gain-db 40

Run from the project ROOT folder (ENCS5323_Project), not from inside sensing/.
"""

import os
import sys
import argparse
import numpy as np
import matplotlib.pyplot as plt
from scipy import signal

# make sure we can import config.py from the project root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

try:
    import adi
except ImportError:
    print("ERROR: pyadi-iio not installed -> python -m pip install pyadi-iio pylibiio")
    sys.exit(1)


def capture(sdr, center_freq, n_captures=10):
    """Capture several buffers and average their PSDs to reduce noise."""
    sdr.rx_lo = int(center_freq)
    # throw away the first buffer (settling after retune)
    sdr.rx()

    fs = float(sdr.sample_rate)
    psd_accum = None
    freqs = None
    for _ in range(n_captures):
        x = np.asarray(sdr.rx())
        f, pxx = signal.welch(
            x,
            fs=fs,
            window="hann",
            nperseg=4096,
            return_onesided=False,   # complex data -> two-sided spectrum
            scaling="density",
        )
        f = np.fft.fftshift(f)
        pxx = np.fft.fftshift(pxx)
        psd_accum = pxx if psd_accum is None else psd_accum + pxx
        freqs = f

    psd_avg = psd_accum / n_captures
    # convert to dB, and shift the frequency axis to absolute RF frequency
    psd_db = 10 * np.log10(psd_avg + 1e-20)
    rf_freqs = (freqs + center_freq) / 1e6   # MHz
    return rf_freqs, psd_db


def main():
    p = argparse.ArgumentParser(description="Capture and plot a single-band PSD.")
    p.add_argument("--freq", type=float, required=True,
                   help="Center frequency in Hz, e.g. 2437e6")
    p.add_argument("--rate", type=float, default=config.DEFAULT_SAMPLE_RATE,
                   help="Sample rate in Hz (= visible bandwidth). Default 2e6")
    p.add_argument("--avg", type=int, default=10,
                   help="Number of buffers to average. Default 10")
    p.add_argument("--gain", choices=["slow_attack", "manual"],
                   default=config.DEFAULT_GAIN_MODE)
    p.add_argument("--gain-db", type=float, default=config.DEFAULT_MANUAL_GAIN_DB)
    p.add_argument("--save", action="store_true",
                   help="Save the figure into the figures/ folder")
    args = p.parse_args()

    print(f"Connecting to Pluto at {config.PLUTO_URI} ...")
    sdr = adi.Pluto(config.PLUTO_URI)
    sdr.sample_rate = int(args.rate)
    sdr.rx_rf_bandwidth = int(args.rate)
    sdr.rx_buffer_size = config.DEFAULT_RX_BUFFER_SIZE
    sdr.gain_control_mode_chan0 = args.gain
    if args.gain == "manual":
        sdr.rx_hardwaregain_chan0 = float(args.gain_db)

    print(f"Capturing at {args.freq/1e6:.3f} MHz, "
          f"{args.rate/1e6:.1f} MHz span, averaging {args.avg} buffers ...")
    rf_freqs, psd_db = capture(sdr, args.freq, args.avg)

    # --- plot ---------------------------------------------------------------
    plt.figure(figsize=(10, 5))
    plt.plot(rf_freqs, psd_db, linewidth=0.8)
    plt.xlabel("Frequency (MHz)")
    plt.ylabel("PSD (dB/Hz, relative)")
    plt.title(f"Power Spectral Density @ {args.freq/1e6:.1f} MHz "
              f"(span {args.rate/1e6:.0f} MHz)")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()

    if args.save:
        os.makedirs(config.FIGURES_DIR, exist_ok=True)
        fname = os.path.join(config.FIGURES_DIR,
                             f"psd_{int(args.freq/1e6)}MHz.png")
        plt.savefig(fname, dpi=150)
        print(f"Saved figure -> {fname}")

    plt.show()


if __name__ == "__main__":
    main()