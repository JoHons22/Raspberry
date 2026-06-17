import time
import json
import spidev
from gpiozero import DigitalInputDevice

# Monitor pins connected to SPI pins
SCLK_MONITOR = 5    # GPIO5, physical pin 29
CE0_MONITOR = 6     # GPIO6, physical pin 31
CE1_MONITOR = 13    # GPIO13, physical pin 33

TEST_DATA = [0x55, 0xAA, 0xFF, 0x00, 0x12, 0x34]

edge_count = {
    "sclk": 0,
    "ce0": 0,
    "ce1": 0
}


def count_edge(name):
    def handler():
        edge_count[name] += 1
    return handler


def reset_counts():
    edge_count["sclk"] = 0
    edge_count["ce0"] = 0
    edge_count["ce1"] = 0


def run_spi_test(device_number, ce_name):
    """
    device_number 0 tests CE0 using /dev/spidev0.0
    device_number 1 tests CE1 using /dev/spidev0.1
    """

    reset_counts()

    spi = None

    try:
        spi = spidev.SpiDev()
        spi.open(0, device_number)

        # Slow speed makes it easier for Python to detect pin changes
        spi.max_speed_hz = 1000
        spi.mode = 0

        time.sleep(0.1)

        received = spi.xfer2(TEST_DATA)

        time.sleep(0.1)

        print()
        print(f"SPI device /dev/spidev0.{device_number}")
        print("--------------------------------")
        print(f"Sent:     {TEST_DATA}")
        print(f"Received: {received}")

        data_pass = received == TEST_DATA
        sclk_pass = edge_count["sclk"] > 0
        ce_pass = edge_count[ce_name] > 0

        if data_pass:
            print("MOSI/MISO loopback: PASS")
        else:
            print("MOSI/MISO loopback: FAIL")

        if sclk_pass:
            print("SCLK activity: PASS")
        else:
            print("SCLK activity: FAIL")

        if ce_pass:
            print(f"{ce_name.upper()} activity: PASS")
        else:
            print(f"{ce_name.upper()} activity: FAIL")

        return {
            "device": f"/dev/spidev0.{device_number}",
            "ce_name": ce_name.upper(),
            "received": received,
            "data_pass": data_pass,
            "sclk_pass": sclk_pass,
            "ce_pass": ce_pass,
            "overall_pass": data_pass and sclk_pass and ce_pass
        }

    finally:
        if spi is not None:
            spi.close()


def main():
    test_name = "SPI Test"

    sclk_input = None
    ce0_input = None
    ce1_input = None

    result = {
        "name": test_name,
        "status": "ERROR",
        "details": "SPI test did not complete."
    }

    try:
        print("SPI ALL-PIN TEST")
        print("================")
        print("Required wiring:")
        print("MOSI GPIO10 pin 19 -> MISO GPIO9 pin 21")
        print("SCLK GPIO11 pin 23 -> GPIO5 pin 29")
        print("CE0  GPIO8  pin 24 -> GPIO6 pin 31")
        print("CE1  GPIO7  pin 26 -> GPIO13 pin 33")

        # Set up input monitors
        sclk_input = DigitalInputDevice(SCLK_MONITOR, pull_up=False)
        ce0_input = DigitalInputDevice(CE0_MONITOR, pull_up=False)
        ce1_input = DigitalInputDevice(CE1_MONITOR, pull_up=False)

        # Count both rising and falling edges
        sclk_input.when_activated = count_edge("sclk")
        sclk_input.when_deactivated = count_edge("sclk")

        ce0_input.when_activated = count_edge("ce0")
        ce0_input.when_deactivated = count_edge("ce0")

        ce1_input.when_activated = count_edge("ce1")
        ce1_input.when_deactivated = count_edge("ce1")

        ce0_result = run_spi_test(0, "ce0")
        ce1_result = run_spi_test(1, "ce1")

        print()
        print("FINAL RESULT")
        print("============")

        if ce0_result["overall_pass"] and ce1_result["overall_pass"]:
            print("SPI TEST: PASS")

            result = {
                "name": test_name,
                "status": "PASS",
                "details": (
                    "SPI loopback passed for CE0 and CE1. "
                    "MOSI/MISO data matched, SCLK activity detected, and chip select activity detected."
                )
            }

        else:
            print("SPI TEST: FAIL")

            fail_reasons = []

            if not ce0_result["data_pass"]:
                fail_reasons.append("CE0 MOSI/MISO loopback failed")
            if not ce0_result["sclk_pass"]:
                fail_reasons.append("CE0 test did not detect SCLK activity")
            if not ce0_result["ce_pass"]:
                fail_reasons.append("CE0 activity not detected")

            if not ce1_result["data_pass"]:
                fail_reasons.append("CE1 MOSI/MISO loopback failed")
            if not ce1_result["sclk_pass"]:
                fail_reasons.append("CE1 test did not detect SCLK activity")
            if not ce1_result["ce_pass"]:
                fail_reasons.append("CE1 activity not detected")

            result = {
                "name": test_name,
                "status": "FAIL",
                "details": "; ".join(fail_reasons)
            }

    except Exception as e:
        result = {
            "name": test_name,
            "status": "ERROR",
            "details": str(e)
        }

    finally:
        if sclk_input is not None:
            sclk_input.close()
        if ce0_input is not None:
            ce0_input.close()
        if ce1_input is not None:
            ce1_input.close()

        # The GUI reads the last printed line as JSON.
        print(json.dumps(result))


if __name__ == "__main__":
    main()
