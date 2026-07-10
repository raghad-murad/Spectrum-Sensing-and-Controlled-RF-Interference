"""
pluto_utils.py
Utility functions for connecting to ADALM-Pluto SDR.

This file tries multiple Pluto URIs automatically:
1. The URI provided by the user or config.py
2. The USB URI detected from: iio_info -s
3. The default IP URI: ip:192.168.2.1
4. Some common USB fallback URIs

It returns:
    sdr, used_uri
"""

import subprocess
import re

try:
    import adi
except ImportError:
    print("ERROR: pyadi-iio is not installed.")
    print("Install it using:")
    print("    python -m pip install pyadi-iio pylibiio")
    raise


def detect_pluto_uri():
    """
    Detect the current Pluto USB URI using:
        iio_info -s

    Example output may contain:
        [usb:1.4.5]
        [usb:1.151.5]

    Returns:
        detected URI as string, or None if not found.
    """
    try:
        result = subprocess.run(
            ["iio_info", "-s"],
            capture_output=True,
            text=True,
            timeout=10
        )

        output = result.stdout + result.stderr

        match = re.search(r"\[(usb:[^\]]+)\]", output)

        if match:
            detected_uri = match.group(1)
            print(f"[OK] Detected Pluto URI from iio_info: {detected_uri}")
            return detected_uri

        print("[WARN] No USB Pluto URI found in iio_info output.")
        return None

    except FileNotFoundError:
        print("[WARN] iio_info command not found.")
        print("       Make sure libiio is installed and added to PATH.")
        return None

    except Exception as error:
        print(f"[WARN] Could not run iio_info -s: {error}")
        return None


def connect_pluto(preferred_uri=None):
    """
    Try to connect to ADALM-Pluto using several possible URIs.

    Args:
        preferred_uri:
            URI entered by the user or taken from config.py.
            Examples:
                ip:192.168.2.1
                usb:1.4.5

    Returns:
        sdr:
            adi.Pluto object
        used_uri:
            URI that successfully connected

    Raises:
        RuntimeError if all connection attempts fail.
    """

    possible_uris = []

    if preferred_uri:
        possible_uris.append(preferred_uri)

    detected_uri = detect_pluto_uri()

    if detected_uri:
        possible_uris.append(detected_uri)

    possible_uris.extend([
        "ip:192.168.2.1",
        "usb:1.4.5",
        "usb:1.151.5",
    ])

    # Remove duplicates while keeping order
    unique_uris = []

    for uri in possible_uris:
        if uri not in unique_uris:
            unique_uris.append(uri)

    last_error = None

    for uri in unique_uris:
        try:
            print(f"[INFO] Trying Pluto URI: {uri}")
            sdr = adi.Pluto(uri)
            print(f"[OK] Connected to Pluto using URI: {uri}")
            return sdr, uri

        except Exception as error:
            print(f"[WARN] Failed to connect using {uri}")
            last_error = error

    raise RuntimeError(
        "\nCould not connect to ADALM-Pluto.\n\n"
        "Try these steps:\n"
        "1. Make sure Pluto is connected by USB.\n"
        "2. Wait 10 seconds after plugging it in.\n"
        "3. Run this command in CMD or PowerShell:\n"
        "       iio_info -s\n"
        "4. Check the detected URI, for example usb:1.4.5\n"
        "5. Use that URI inside the program.\n\n"
        f"Last error: {last_error}"
    )