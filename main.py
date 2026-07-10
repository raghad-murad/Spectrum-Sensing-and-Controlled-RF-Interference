"""
main.py
Interactive menu for ENCS5323 Component 1: Spectrum Sensing.

This menu runs:
    1. Wideband PSD scan + Noise Floor + Occupancy Threshold
    2. Waterfall / temporal variability capture

Make sure you have:
    sensing/wideband_scan.py
    sensing/waterfall.py
    sensing/__init__.py
    config.py
"""

import config
from sensing.wideband_scan import run_scan
from sensing.waterfall import run_waterfall


def ask_string(prompt, default=None):
    if default is None:
        value = input(f"{prompt}: ").strip()
        return value

    value = input(f"{prompt} [{default}]: ").strip()
    return value if value else default


def ask_float(prompt, default=None):
    while True:
        try:
            if default is None:
                value = input(f"{prompt}: ").strip()
                return float(value)

            value = input(f"{prompt} [{default}]: ").strip()
            return float(value) if value else float(default)

        except ValueError:
            print("Invalid number. Try again.")


def ask_int(prompt, default=None):
    while True:
        try:
            if default is None:
                value = input(f"{prompt}: ").strip()
                return int(value)

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
        print(
            f"  {i}. {key:<12} "
            f"{band['name']} "
            f"({band['start'] / 1e6:.0f}-{band['stop'] / 1e6:.0f} MHz)"
        )

    print(f"  {len(keys) + 1}. Custom range")

    while True:
        choice = ask_int("Select band", 1)

        if 1 <= choice <= len(keys):
            return {
                "type": "named",
                "band": keys[choice - 1],
                "start": None,
                "stop": None,
                "label": None,
            }

        if choice == len(keys) + 1:
            start_mhz = ask_float("Start frequency in MHz")
            stop_mhz = ask_float("Stop frequency in MHz")
            label = ask_string("Output label", f"{int(start_mhz)}_{int(stop_mhz)}MHz")

            return {
                "type": "custom",
                "band": None,
                "start": start_mhz * 1e6,
                "stop": stop_mhz * 1e6,
                "label": label,
            }

        print("Invalid choice. Try again.")


def run_scan_menu():
    print("\n" + "=" * 60)
    print("Wideband PSD Scan")
    print("=" * 60)

    uri = ask_string("Pluto URI", config.PLUTO_URI)

    band_info = choose_band()

    rate = ask_float(
        "Sample rate in Hz. Use 2e6 for GSM, 20e6 for Wi-Fi",
        config.DEFAULT_SAMPLE_RATE,
    )

    avg = ask_int("Number of averages per tile", 20)

    gain, gain_db = choose_gain()

    threshold = ask_float(
        "Occupancy threshold above noise floor in dB",
        6.0,
    )

    print("\nStarting scan...")
    print("The plot will show:")
    print("  - Measured PSD")
    print("  - Noise Floor")
    print("  - Occupancy Threshold")
    print("  - Detected occupied channels")
    print()

    run_scan(
        uri=uri,
        band=band_info["band"],
        start=band_info["start"],
        stop=band_info["stop"],
        label=band_info["label"],
        rate=rate,
        avg=avg,
        gain=gain,
        gain_db=gain_db,
        threshold=threshold,
    )


def run_waterfall_menu():
    print("\n" + "=" * 60)
    print("Waterfall / Temporal Variability")
    print("=" * 60)

    uri = ask_string("Pluto URI", config.PLUTO_URI)

    print("\nCommon center frequencies:")
    print("  Wi-Fi Channel 1 center  = 2412 MHz")
    print("  Wi-Fi Channel 6 center  = 2437 MHz")
    print("  Wi-Fi Channel 11 center = 2462 MHz")
    print("  Example GSM area        = 946 MHz")

    freq_mhz = ask_float("Center frequency in MHz", 2437)
    freq = freq_mhz * 1e6

    rate = ask_float(
        "Sample rate in Hz. Use 20e6 for Wi-Fi waterfall",
        20e6,
    )

    duration = ask_float("Recording duration in seconds", 10.0)
    interval = ask_float("Time between rows in seconds", 0.1)

    gain, gain_db = choose_gain()

    live = ask_yes_no("Show live waterfall while recording?", True)

    print("\nStarting waterfall capture...")
    print("This will save a waterfall figure and raw matrix data.")
    print()

    run_waterfall(
        uri=uri,
        freq=freq,
        rate=rate,
        duration=duration,
        interval=interval,
        gain=gain,
        gain_db=gain_db,
        live=live,
    )


def quick_demo_menu():
    """
    Useful during the discussion session.
    Runs common experiments with minimal questions.
    """
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
        run_scan(
            uri=uri,
            band="GSM900_DL",
            rate=2e6,
            avg=8,
            gain="manual",
            gain_db=40,
            threshold=6.0,
        )

    elif choice == "2":
        run_scan(
            uri=uri,
            band="WIFI_CH6",
            rate=20e6,
            avg=8,
            gain="manual",
            gain_db=40,
            threshold=6.0,
        )

    elif choice == "3":
        run_waterfall(
            uri=uri,
            freq=2437e6,
            rate=20e6,
            duration=10.0,
            interval=0.1,
            gain="manual",
            gain_db=40,
            live=True,
        )

    elif choice == "4":
        run_scan(
            uri=uri,
            band="ISM24",
            rate=20e6,
            avg=6,
            gain="manual",
            gain_db=40,
            threshold=6.0,
        )

    else:
        print("Invalid quick demo choice.")


def print_header():
    print("\n")
    print("╔════════════════════════════════════════════════════╗")
    print("║      ENCS5323 Spectrum Sensing System              ║")
    print("║      ADALM-PLUTO SDR - Component 1                 ║")
    print("╚════════════════════════════════════════════════════╝")


def main():
    while True:
        print_header()

        print("Main Menu:")
        print("  1. Wideband PSD scan")
        print("  2. Waterfall / temporal variability")
        print("  3. Quick demo")
        print("  4. Exit")

        choice = input("\nSelect option [1/2/3/4]: ").strip()

        try:
            if choice == "1":
                run_scan_menu()

            elif choice == "2":
                run_waterfall_menu()

            elif choice == "3":
                quick_demo_menu()

            elif choice == "4":
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