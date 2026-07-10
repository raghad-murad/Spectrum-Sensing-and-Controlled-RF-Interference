"""
config.py
Central configuration for ENCS5323 spectrum sensing project.
"""

# Pluto default URI over USB Ethernet
PLUTO_URI = "ip:192.168.2.1"

# Radio defaults
DEFAULT_SAMPLE_RATE = 2_000_000
DEFAULT_RX_BUFFER_SIZE = 2**18

DEFAULT_GAIN_MODE = "slow_attack"   # or "manual"
DEFAULT_MANUAL_GAIN_DB = 40

# Frequency bands
BANDS = {
    "GSM900_DL": {
        "name": "GSM 900 Downlink",
        "start": 935_000_000,
        "stop": 960_000_000,
        "note": "Base station -> phone carriers",
    },
    "GSM1800_DL": {
        "name": "GSM 1800 Downlink",
        "start": 1_805_000_000,
        "stop": 1_880_000_000,
        "note": "DCS 1800 downlink",
    },
    "WIFI_CH1": {
        "name": "Wi-Fi Channel 1 Area",
        "start": 2_401_000_000,
        "stop": 2_423_000_000,
        "note": "Around Wi-Fi channel 1 center frequency 2412 MHz",
    },
    "WIFI_CH6": {
        "name": "Wi-Fi Channel 6 Area",
        "start": 2_426_000_000,
        "stop": 2_448_000_000,
        "note": "Around Wi-Fi channel 6 center frequency 2437 MHz",
    },
        "WIFI_CH11": {
        "name": "Wi-Fi Channel 11 Area",
        "start": 2_452_000_000,
        "stop": 2_472_000_000,
        "note": "Around Wi-Fi channel 11 center frequency 2462 MHz",
    },
}

DATA_DIR = "data"
FIGURES_DIR = "figures_sensing"