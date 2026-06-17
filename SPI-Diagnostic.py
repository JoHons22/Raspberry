import spidev
import time

TEST_PATTERNS = [
    [0xFF] * 8,
    [0x00] * 8,
    [0x55, 0xAA] * 4,
    [0x12, 0x34, 0xC3, 0x3C] * 2
]

spi = spidev.SpiDev()
spi.open(0, 0)
spi.max_speed_hz = 1000
spi.mode = 0

try:
    print("SPI RAW DIAGNOSTIC")
    print("==================")
    print("Test this two ways:")
    print("1. MOSI connected to MISO")
    print("2. MOSI disconnected from MISO, but MISO still pulled down with 10k to GND")
    print()

    for pattern in TEST_PATTERNS:
        received = spi.xfer2(pattern)
        print(f"Sent:     {pattern}")
        print(f"Received: {received}")
        print(f"Match:    {received == pattern}")
        print()

        time.sleep(0.2)

finally:
    spi.close()
