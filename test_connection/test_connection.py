"""
test_connection.py
==================
Run this FIRST, before anything else, to confirm the ADALM-PLUTO is connected
and controllable from Python.

Usage:
    python test_connection.py

What it does:
    1. Opens the Pluto at the URI in config.py
    2. Prints the key radio parameters (sample rate, LO frequencies, gain)
    3. Captures one small buffer of samples and reports basic stats
    4. Tells you clearly whether everything is OK

If this passes, the sensing and interference scripts will work too.
"""

import sys
import numpy as np

try:
    import adi
except ImportError:
    print("ERROR: pyadi-iio is not installed.")
    print("Fix:  python -m pip install pyadi-iio pylibiio")
    sys.exit(1)

import config


def main():
    print("=" * 60)
    print("ADALM-PLUTO connection test")
    print("=" * 60)
    print(f"Trying to connect at: {config.PLUTO_URI}")

    # --- 1. Open the device -------------------------------------------------
    try:
        sdr = adi.Pluto(config.PLUTO_URI)
    except Exception as e:
        print("\nFAILED to open the Pluto.")
        print(f"  Reason: {e}")
        print("\nChecklist:")
        print("  - Is the Pluto plugged into USB?")
        print("  - Did it appear as a 'PlutoSDR' drive in File Explorer?")
        print("  - Try the USB URI instead (see `iio_info -s`), e.g. usb:2.1.5")
        sys.exit(1)

    print("\n[OK] Device opened.\n")

    # --- 2. Configure a known state ----------------------------------------
    sdr.sample_rate = int(config.DEFAULT_SAMPLE_RATE)
    sdr.rx_rf_bandwidth = int(config.DEFAULT_SAMPLE_RATE)
    sdr.rx_lo = 2_400_000_000            # park at 2.4 GHz for the test
    sdr.gain_control_mode_chan0 = config.DEFAULT_GAIN_MODE
    sdr.rx_buffer_size = 4096            # small buffer, just a quick grab

    # --- 3. Report parameters ----------------------------------------------
    print("Current radio configuration:")
    print(f"  Sample rate     : {sdr.sample_rate/1e6:.3f} MSPS")
    print(f"  RX LO frequency : {sdr.rx_lo/1e6:.3f} MHz")
    print(f"  RX RF bandwidth : {sdr.rx_rf_bandwidth/1e6:.3f} MHz")
    print(f"  Gain mode       : {sdr.gain_control_mode_chan0}")

    # --- 4. Capture one buffer ---------------------------------------------
    print("\nCapturing one buffer of samples...")
    try:
        samples = sdr.rx()
    except Exception as e:
        print(f"FAILED to capture samples: {e}")
        sys.exit(1)

    samples = np.asarray(samples)
    power_dbfs = 10 * np.log10(np.mean(np.abs(samples) ** 2) + 1e-12)

    print(f"  Samples captured : {len(samples)}")
    print(f"  Data type        : {samples.dtype}")
    print(f"  Mean power       : {power_dbfs:.1f} dBFS (relative to full scale)")

    print("\n" + "=" * 60)
    print("SUCCESS - the Pluto is connected and streaming.")
    print("You are ready to run the sensing scripts.")
    print("=" * 60)


if __name__ == "__main__":
    main()