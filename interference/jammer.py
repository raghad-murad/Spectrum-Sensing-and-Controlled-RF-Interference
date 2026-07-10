"""
jammer.py
Component 2: controlled interference generator (Pluto TX).

Callable function used by main.py and by command line:
    run_jammer(uri, freq, kind, bw, rate, gain, duration)

*** SAFETY ***
Transmit only toward YOUR OWN router/device, indoors, at low power, for a short
time (default 30 s, capped at 60 s). Start at low gain (e.g. -30 dB) and raise
it slowly only if needed. Never affect equipment you do not own.
"""

import os
import sys
import time
import argparse
import numpy as np

from pluto_utils import connect_pluto

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

# hard safety caps
MAX_DURATION_S = 60
DEFAULT_TX_GAIN_DB = -30      # start quiet


def make_waveform(kind, fs, bw, n=2**16):
    """Return a complex baseband interference waveform (int16-scale)."""
    t = np.arange(n) / fs

    if kind == "tone":
        # single carrier exactly at the LO frequency (narrowband jammer)
        x = np.exp(2j * np.pi * 0.0 * t)

    elif kind == "noise":
        # band-limited complex Gaussian noise (broadband jammer)
        x = (np.random.randn(n) + 1j * np.random.randn(n))
        X = np.fft.fftshift(np.fft.fft(x))
        freqs = np.fft.fftshift(np.fft.fftfreq(n, 1 / fs))
        X[np.abs(freqs) > bw / 2] = 0
        x = np.fft.ifft(np.fft.ifftshift(X))

    elif kind == "sweep":
        # linear chirp across +/- bw/2 (swept jammer)
        k = bw / t[-1]
        inst_f = -bw / 2 + k * t
        phase = 2 * np.pi * np.cumsum(inst_f) / fs
        x = np.exp(1j * phase)

    else:
        raise ValueError(f"unknown waveform type: {kind}")

    x = x / np.max(np.abs(x)) * 0.9
    return (x * (2**14)).astype(np.complex64)


def run_jammer(
    uri=config.PLUTO_URI,
    freq=2412e6,
    kind="noise",
    bw=None,
    rate=20e6,
    gain=DEFAULT_TX_GAIN_DB,
    duration=30,
    skip_confirm=False,
):
    """
    Callable function used by main.py and by command line.
    Transmits a controlled interference signal, then releases the channel.
    """
    # ---- safety clamps -----------------------------------------------------
    duration = min(duration, MAX_DURATION_S)
    if gain > 0:
        print("[safety] TX gain must be <= 0 dB. Clamping to 0.")
        gain = 0.0
    if bw is None:
        bw = rate

    print("=" * 60)
    print("  INTERFERENCE TRANSMISSION")
    print("=" * 60)
    print(f"  Center freq : {freq/1e6:.1f} MHz")
    print(f"  Waveform    : {kind}")
    print(f"  Bandwidth   : {bw/1e6:.1f} MHz")
    print(f"  TX gain     : {gain:.0f} dB")
    print(f"  Duration    : {duration:.0f} s")
    print("=" * 60)
    print("  SAFETY: only your own device, indoors, low power, short time.")

    if not skip_confirm:
        ans = input("  Type 'yes' to start transmitting: ").strip().lower()
        if ans != "yes":
            print("Aborted.")
            return

    print(f"\nConnecting to Pluto at {uri} ...")
    sdr, used_uri = connect_pluto(uri)
    sdr.sample_rate = int(rate)
    sdr.tx_rf_bandwidth = int(rate)
    sdr.tx_lo = int(freq)
    sdr.tx_hardwaregain_chan0 = float(gain)

    wave = make_waveform(kind, float(rate), bw)

    # cyclic buffer => Pluto repeats the waveform continuously with no gaps
    sdr.tx_cyclic_buffer = True
    sdr.tx(wave)

    print(f"\n*** TRANSMITTING for {duration:.0f} s ... ***")
    try:
        t0 = time.time()
        while time.time() - t0 < duration:
            remaining = duration - (time.time() - t0)
            print(f"\r  transmitting... {remaining:4.1f} s left ",
                  end="", flush=True)
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n  interrupted by user.")
    finally:
        sdr.tx_destroy_buffer()
        print("\n\n*** TRANSMISSION STOPPED. Channel released. ***")


def main():
    p = argparse.ArgumentParser(description="Controlled ISM interference generator.")
    p.add_argument("--uri", default=config.PLUTO_URI)
    p.add_argument("--freq", type=float, required=True,
                   help="Center frequency in Hz, e.g. 2412e6")
    p.add_argument("--type", dest="kind",
                   choices=["noise", "tone", "sweep"], default="noise")
    p.add_argument("--bw", type=float, default=None)
    p.add_argument("--rate", type=float, default=20e6)
    p.add_argument("--gain", type=float, default=DEFAULT_TX_GAIN_DB)
    p.add_argument("--duration", type=float, default=30)
    args = p.parse_args()
    run_jammer(uri=args.uri, freq=args.freq, kind=args.kind, bw=args.bw,
               rate=args.rate, gain=args.gain, duration=args.duration)


if __name__ == "__main__":
    main()