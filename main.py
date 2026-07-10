"""
main.py
Interactive menu for the ENCS5323 project.

Covers BOTH components:
    Component 1 - Spectrum Sensing
        1. Wideband PSD scan (+ noise floor + occupancy detection)
        2. Waterfall / temporal variability
    Component 2 - Controlled Interference
        3. Transmit interference (jammer)      [TX laptop]
        4. Measure link (ping/loss/jitter)     [victim device]
        5. Compare results (baseline/jammed/recovery)
    Extras
        6. Quick demo
        7. Exit

Required files:
    config.py
    pluto_utils.py
    sensing/wideband_scan.py      (run_scan)
    sensing/waterfall.py          (run_waterfall)
    sensing/__init__.py
    interference/jammer.py        (run_jammer)
    interference/measure_link.py  (run_measure)
    interference/plot_results.py  (run_compare)
    interference/__init__.py
"""

import config
from sensing.wideband_scan import run_scan
from sensing.waterfall import run_waterfall
from interference.jammer import run_jammer
from interference.measure_link import run_measure
from interference.plot_results import run_compare


# ---------------------------------------------------------------------------
# small input helpers (same style as before)
# ---------------------------------------------------------------------------
def ask_string(prompt, default=None):
    if default is None:
        return input(f"{prompt}: ").strip()
    value = input(f"{prompt} [{default}]: ").strip()
    return value if value else default


def ask_float(prompt, default=None):
    while True:
        try:
            if default is None:
                return float(input(f"{prompt}: ").strip())
            value = input(f"{prompt} [{default}]: ").strip()
            return float(value) if value else float(default)
        except ValueError:
            print("Invalid number. Try again.")


def ask_int(prompt, default=None):
    while True:
        try:
            if default is None:
                return int(input(f"{prompt}: ").strip())
            value = input(f"{prompt} [{default}]: ").strip()
            return int(value) if value else int(default)
        except ValueError:
            print("Invalid integer. Try again.")


def ask_yes_no(prompt, default=False):
    default_text = "y" if default else "n"
    value = input(f"{prompt} [y/n, default {default_text}]: ").strip().lower()
    if not value:
        return default
    return value in ["y", "yes"]


def choose_gain():
    print("\nGain mode:")
    print("  1. slow_attack  Auto gain, good for exploration")
    print("  2. manual       Fixed gain, better for comparing measurements")
    choice = input("Select gain mode [1/2, default 1]: ").strip()
    if choice == "2":
        gain_db = ask_float("Manual gain in dB", config.DEFAULT_MANUAL_GAIN_DB)
        return "manual", gain_db
    return "slow_attack", config.DEFAULT_MANUAL_GAIN_DB


def choose_band():
    print("\nAvailable bands:")
    keys = list(config.BANDS.keys())
    for i, key in enumerate(keys, start=1):
        band = config.BANDS[key]
        print(f"  {i}. {key:<12} {band['name']} "
              f"({band['start']/1e6:.0f}-{band['stop']/1e6:.0f} MHz)")
    print(f"  {len(keys) + 1}. Custom range")

    while True:
        choice = ask_int("Select band", 1)
        if 1 <= choice <= len(keys):
            return {"type": "named", "band": keys[choice - 1],
                    "start": None, "stop": None, "label": None}
        if choice == len(keys) + 1:
            start_mhz = ask_float("Start frequency in MHz")
            stop_mhz = ask_float("Stop frequency in MHz")
            label = ask_string("Output label",
                               f"{int(start_mhz)}_{int(stop_mhz)}MHz")
            return {"type": "custom", "band": None,
                    "start": start_mhz * 1e6, "stop": stop_mhz * 1e6,
                    "label": label}
        print("Invalid choice. Try again.")


# common Wi-Fi channel center frequencies (for the jammer menu)
WIFI_CHANNELS = {
    "1": 2412e6, "6": 2437e6, "11": 2462e6,
}


# ---------------------------------------------------------------------------
# Component 1 menus
# ---------------------------------------------------------------------------
def run_scan_menu():
    print("\n" + "=" * 60)
    print("Wideband PSD Scan")
    print("=" * 60)
    uri = ask_string("Pluto URI", config.PLUTO_URI)
    sel = choose_band()
    rate = ask_float("Sample rate in Hz (visible BW)", config.DEFAULT_SAMPLE_RATE)
    avg = ask_int("Buffers to average", 8)
    gain, gain_db = choose_gain()
    threshold = ask_float("Occupancy threshold in dB above noise floor", 6.0)

    run_scan(uri=uri, band=sel["band"], start=sel["start"], stop=sel["stop"],
             label=sel["label"], rate=rate, avg=avg, gain=gain,
             gain_db=gain_db, threshold=threshold)


def run_waterfall_menu():
    print("\n" + "=" * 60)
    print("Waterfall / Temporal Variability")
    print("=" * 60)
    uri = ask_string("Pluto URI", config.PLUTO_URI)
    freq = ask_float("Center frequency in MHz", 2437) * 1e6
    rate = ask_float("Sample rate in Hz (visible BW)", 20e6)
    duration = ask_float("Duration in seconds", 10)
    interval = ask_float("Seconds between rows", 0.1)
    gain, gain_db = choose_gain()
    live = ask_yes_no("Show live while recording?", True)

    run_waterfall(uri=uri, freq=freq, rate=rate, duration=duration,
                  interval=interval, gain=gain, gain_db=gain_db, live=live)


# ---------------------------------------------------------------------------
# Component 2 menus
# ---------------------------------------------------------------------------
def run_jammer_menu():
    print("\n" + "=" * 60)
    print("Interference Transmitter (JAMMER)")
    print("=" * 60)
    print("  SAFETY: only your own router/device, indoors, low power, short time.")
    uri = ask_string("Pluto URI (transmitter)", config.PLUTO_URI)

    print("\nTarget Wi-Fi channel:")
    print("  1 -> 2412 MHz | 6 -> 2437 MHz | 11 -> 2462 MHz | or type 'custom'")
    ch = ask_string("Channel (1/6/11/custom)", "1")
    if ch in WIFI_CHANNELS:
        freq = WIFI_CHANNELS[ch]
    else:
        freq = ask_float("Center frequency in MHz", 2412) * 1e6

    print("\nWaveform type:")
    print("  1. noise  (broadband, most realistic)")
    print("  2. tone   (narrowband CW)")
    print("  3. sweep  (chirp across the channel)")
    tchoice = input("Select [1/2/3, default 1]: ").strip()
    kind = {"2": "tone", "3": "sweep"}.get(tchoice, "noise")

    rate = ask_float("TX sample rate in Hz (= max BW)", 20e6)
    bw_mhz = ask_float("Interference bandwidth in MHz (0 = full rate)", 0)
    bw = None if bw_mhz == 0 else bw_mhz * 1e6
    gain = ask_float("TX gain in dB (<=0, start low e.g. -30)", -30)
    duration = ask_float("Duration in seconds (max 60)", 30)

    run_jammer(uri=uri, freq=freq, kind=kind, bw=bw, rate=rate,
               gain=gain, duration=duration)


def run_measure_menu():
    print("\n" + "=" * 60)
    print("Link Measurement (run on the VICTIM device)")
    print("=" * 60)
    print("  Tip: find your router IP with `ipconfig` -> Default Gateway.")
    target = ask_string("Target IP to ping", "192.168.1.1")
    duration = ask_float("Duration in seconds", 30)
    interval = ask_float("Seconds between pings", 0.2)
    print("\nLabel this run:")
    print("  common labels: baseline / jammed / recovery")
    label = ask_string("Label", "baseline")

    run_measure(target=target, duration=duration,
                interval=interval, label=label)


def run_compare_menu():
    print("\n" + "=" * 60)
    print("Compare Interference Results")
    print("=" * 60)
    print("  Enter the labels you measured, separated by spaces.")
    raw = ask_string("Labels", "baseline jammed recovery")
    labels = raw.split()
    run_compare(labels)


# ---------------------------------------------------------------------------
# Quick demo
# ---------------------------------------------------------------------------
def quick_demo_menu():
    print("\n" + "=" * 60)
    print("Quick Demo")
    print("=" * 60)
    uri = ask_string("Pluto URI", config.PLUTO_URI)

    print("\nQuick options:")
    print("  1. GSM 900 downlink scan")
    print("  2. Wi-Fi Channel 6 PSD scan")
    print("  3. Wi-Fi Channel 6 waterfall")
    print("  4. Full 2.4 GHz ISM scan")
    choice = input("Select quick demo [1/2/3/4]: ").strip()

    if choice == "1":
        run_scan(uri=uri, band="GSM900_DL", rate=2e6, avg=8,
                 gain="manual", gain_db=40, threshold=6.0)
    elif choice == "2":
        run_scan(uri=uri, band="WIFI_CH6", rate=20e6, avg=8,
                 gain="manual", gain_db=40, threshold=6.0)
    elif choice == "3":
        run_waterfall(uri=uri, freq=2437e6, rate=20e6, duration=10.0,
                      interval=0.1, gain="manual", gain_db=40, live=True)
    elif choice == "4":
        run_scan(uri=uri, band="ISM24", rate=20e6, avg=6,
                 gain="manual", gain_db=40, threshold=6.0)
    else:
        print("Invalid quick demo choice.")


# ---------------------------------------------------------------------------
# main loop
# ---------------------------------------------------------------------------
def print_header():
    print("\n")
    print("╔════════════════════════════════════════════════════╗")
    print("║   ENCS5323 - Spectrum Sensing & RF Interference    ║")
    print("║   ADALM-PLUTO SDR                                  ║")
    print("╚════════════════════════════════════════════════════╝")


def main():
    while True:
        print_header()
        print("Main Menu:")
        print("  \nComponent 1: Spectrum Sensing")
        print("  1. Wideband PSD scan")
        print("  2. Waterfall / temporal variability")
        print("  \nComponent 2: Controlled Interference")
        print("  3. Transmit interference (jammer)   [TX laptop]")
        print("  4. Measure link (ping/loss/jitter)  [victim device]")
        print("  5. Compare results (baseline/jammed/recovery)")
        print("  \nExtras")
        print("  6. Quick demo")
        print("  7. Exit")

        choice = input("\nSelect option [1-7]: ").strip()

        try:
            if choice == "1":
                run_scan_menu()
            elif choice == "2":
                run_waterfall_menu()
            elif choice == "3":
                run_jammer_menu()
            elif choice == "4":
                run_measure_menu()
            elif choice == "5":
                run_compare_menu()
            elif choice == "6":
                quick_demo_menu()
            elif choice == "7":
                print("Exiting.")
                break
            else:
                print("Invalid option. Try again.")

        except KeyboardInterrupt:
            print("\nStopped by user.")
        except Exception as exc:
            print("\nERROR:")
            print(exc)

        input("\nPress Enter to return to main menu...")


if __name__ == "__main__":
    main()