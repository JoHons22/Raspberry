import time
import json
import spidev
from gpiozero import DigitalInputDevice

# Monitor pins connected to SPI pins
SCLK_MONITOR = 5    # GPIO5, physical pin 29
CE0_MONITOR = 6     # GPIO6, physical pin 31
CE1_MONITOR = 13    # GPIO13, physical pin 33

# Longer test pattern makes false passes less likely
TEST_DATA = [
    0x55, 0xAA, 0xFF, 0x00,
    0x12, 0x34, 0xC3, 0x3C,
    0x0F, 0xF0, 0x5A, 0xA5
]

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


def pass_fail(value):
    return "PASS" if value else "FAIL"


def run_spi_test(device_number, ce_name):
    """
    device_number 0 tests CE0 using /dev/spidev0.0
    device_number 1 tests CE1 using /dev/spidev0.1
    """

    reset_counts()

    spi = None

    result = {
        "device": f"/dev/spidev0.{device_number}",
        "ce_name": ce_name.upper(),
        "sent": TEST_DATA,
        "received": [],
        "data_pass": False,
        "sclk_pass": False,
        "ce_pass": False,
        "overall_pass": False,
        "error": None
    }

    try:
        spi = spidev.SpiDev()
        spi.open(0, device_number)

        # Higher speed makes floating/crosstalk false loopback less likely.
        # If your edge monitor misses SCLK, lower this to 1000.
        spi.max_speed_hz = 50000
        spi.mode = 0

        time.sleep(0.1)

        received = spi.xfer2(TEST_DATA)

        time.sleep(0.1)

        data_pass = received == TEST_DATA
        sclk_pass = edge_count["sclk"] > 0
        ce_pass = edge_count[ce_name] > 0

        result["received"] = received
        result["data_pass"] = data_pass
        result["sclk_pass"] = sclk_pass
        result["ce_pass"] = ce_pass
        result["overall_pass"] = data_pass and sclk_pass and ce_pass

        print()
        print(f"SPI device /dev/spidev0.{device_number}")
        print("--------------------------------")
        print(f"Sent:     {TEST_DATA}")
        print(f"Received: {received}")
        print(f"MOSI/MISO loopback: {pass_fail(data_pass)}")
        print(f"SCLK activity:      {pass_fail(sclk_pass)}")
        print(f"{ce_name.upper()} activity:       {pass_fail(ce_pass)}")

        return result

    except Exception as e:
        result["error"] = str(e)

        print()
        print(f"SPI device /dev/spidev0.{device_number}")
        print("--------------------------------")
        print(f"ERROR: {e}")

        return result

    finally:
        if spi is not None:
            spi.close()


def build_details(ce0_result, ce1_result):
    details = []

    details.append(
        f"CE0 data {pass_fail(ce0_result['data_pass'])}, "
        f"SCLK {pass_fail(ce0_result['sclk_pass'])}, "
        f"CE0 activity {pass_fail(ce0_result['ce_pass'])}"
    )

    details.append(
        f"CE1 data {pass_fail(ce1_result['data_pass'])}, "
        f"SCLK {pass_fail(ce1_result['sclk_pass'])}, "
        f"CE1 activity {pass_fail(ce1_result['ce_pass'])}"
    )

    if ce0_result["error"]:
        details.append(f"CE0 error: {ce0_result['error']}")

    if ce1_result["error"]:
        details.append(f"CE1 error: {ce1_result['error']}")

    return "; ".join(details)


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
        print("Recommended: 10k pull-down resistor from MISO GPIO9 pin 21 to GND")

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

        ce0_pass = ce0_result["overall_pass"]
        ce1_pass = ce1_result["overall_pass"]

        details = build_details(ce0_result, ce1_result)

        print()
        print("FINAL RESULT")
        print("============")
        print(details)

        if ce0_pass and ce1_pass:
            print("SPI TEST: PASS")
            result = {
                "name": test_name,
                "status": "PASS",
                "details": details
            }
        else:
            print("SPI TEST: FAIL")
            result = {
                "name": test_name,
                "status": "FAIL",
                "details": details
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
