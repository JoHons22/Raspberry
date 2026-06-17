import time
import json
import spidev
from gpiozero import DigitalInputDevice

TEST_NAME = "SPI Test"

# Monitor pins connected to SPI pins
SCLK_MONITOR = 5    # GPIO5, physical pin 29
CE0_MONITOR = 6     # GPIO6, physical pin 31
CE1_MONITOR = 13    # GPIO13, physical pin 33

# Do NOT include an all-zero pattern.
# If MISO is pulled down and disconnected, received data will be all 0s.
TEST_PATTERNS = [
    [0xFF] * 8,
    [0x55, 0xAA] * 4,
    [0x12, 0x34, 0xC3, 0x3C] * 2,
    [0x5A, 0xA5, 0x0F, 0xF0] * 2
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
    device_name = f"/dev/spidev0.{device_number}"

    result = {
        "device": device_name,
        "ce_name": ce_name.upper(),
        "data_pass": False,
        "sclk_pass": False,
        "ce_pass": False,
        "overall_pass": False,
        "all_received_zero": False,
        "data_message": "Not tested",
        "patterns": [],
        "error": None
    }

    try:
        spi = spidev.SpiDev()
        spi.open(0, device_number)

        # Slow speed helps the Python edge monitors catch SCLK and CE changes
        spi.max_speed_hz = 1000
        spi.mode = 0

        print()
        print(f"SPI device {device_name}")
        print("--------------------------------")

        all_patterns_passed = True
        all_received_zero = True

        for pattern in TEST_PATTERNS:
            # Protected copy of intended sent data
            sent = pattern.copy()

            # Separate transmit buffer
            tx_buffer = sent.copy()

            time.sleep(0.1)
            received = spi.xfer2(tx_buffer)
            time.sleep(0.1)

            match = received == sent

            if any(byte != 0 for byte in received):
                all_received_zero = False

            if not match:
                all_patterns_passed = False

            print(f"Sent:     {sent}")
            print(f"Received: {received}")
            print(f"Match:    {match}")
            print()

            result["patterns"].append({
                "sent": sent,
                "received": received,
                "match": match
            })

        sclk_pass = edge_count["sclk"] > 0
        ce_pass = edge_count[ce_name] > 0

        if all_patterns_passed:
            data_pass = True
            data_message = "PASS"
        elif all_received_zero:
            data_pass = False
            data_message = "FAIL - MISO stayed LOW. No loopback data received."
        else:
            data_pass = False
            data_message = "FAIL - received data did not match sent data."

        result["data_pass"] = data_pass
        result["sclk_pass"] = sclk_pass
        result["ce_pass"] = ce_pass
        result["overall_pass"] = data_pass and sclk_pass and ce_pass
        result["all_received_zero"] = all_received_zero
        result["data_message"] = data_message

        print(f"MOSI/MISO loopback: {data_message}")
        print(f"SCLK activity:      {pass_fail(sclk_pass)}")
        print(f"{ce_name.upper()} activity:       {pass_fail(ce_pass)}")

        return result

    except Exception as e:
        result["error"] = str(e)

        print()
        print(f"SPI device {device_name}")
        print("--------------------------------")
        print(f"ERROR: {e}")

        return result

    finally:
        if spi is not None:
            spi.close()


def build_details(ce0_result, ce1_result):
    details = []

    if ce0_result["error"]:
        details.append(f"CE0 ERROR: {ce0_result['error']}")
    else:
        details.append(
            f"CE0 data {pass_fail(ce0_result['data_pass'])} "
            f"({ce0_result['data_message']}), "
            f"SCLK {pass_fail(ce0_result['sclk_pass'])}, "
            f"CE0 activity {pass_fail(ce0_result['ce_pass'])}"
        )

    if ce1_result["error"]:
        details.append(f"CE1 ERROR: {ce1_result['error']}")
    else:
        details.append(
            f"CE1 data {pass_fail(ce1_result['data_pass'])} "
            f"({ce1_result['data_message']}), "
            f"SCLK {pass_fail(ce1_result['sclk_pass'])}, "
            f"CE1 activity {pass_fail(ce1_result['ce_pass'])}"
        )

    return "; ".join(details)


def main():
    sclk_input = None
    ce0_input = None
    ce1_input = None

    final_result = {
        "name": TEST_NAME,
        "status": "ERROR",
        "details": "SPI test did not complete."
    }

    try:
        print("SPI ALL-PIN TEST")
        print("================")
        print("Required wiring:")
        print("MOSI GPIO10, physical pin 19 -> MISO GPIO9, physical pin 21")
        print("MISO GPIO9, physical pin 21 -> 10k resistor -> GND")
        print("SCLK GPIO11, physical pin 23 -> GPIO5, physical pin 29")
        print("CE0  GPIO8,  physical pin 24 -> GPIO6, physical pin 31")
        print("CE1  GPIO7,  physical pin 26 -> GPIO13, physical pin 33")
        print()

        # Set up monitor inputs
        sclk_input = DigitalInputDevice(SCLK_MONITOR, pull_up=False)
        ce0_input = DigitalInputDevice(CE0_MONITOR, pull_up=False)
        ce1_input = DigitalInputDevice(CE1_MONITOR, pull_up=False)

        # Count rising and falling edges
        sclk_input.when_activated = count_edge("sclk")
        sclk_input.when_deactivated = count_edge("sclk")

        ce0_input.when_activated = count_edge("ce0")
        ce0_input.when_deactivated = count_edge("ce0")

        ce1_input.when_activated = count_edge("ce1")
        ce1_input.when_deactivated = count_edge("ce1")

        ce0_result = run_spi_test(0, "ce0")
        ce1_result = run_spi_test(1, "ce1")

        details = build_details(ce0_result, ce1_result)

        print()
        print("FINAL RESULT")
        print("============")
        print(details)

        if ce0_result["overall_pass"] and ce1_result["overall_pass"]:
            print("SPI TEST: PASS")
            final_result = {
                "name": TEST_NAME,
                "status": "PASS",
                "details": details
            }
        else:
            print("SPI TEST: FAIL")
            final_result = {
                "name": TEST_NAME,
                "status": "FAIL",
                "details": details
            }

    except Exception as e:
        final_result = {
            "name": TEST_NAME,
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

        # The GUI reads the final printed line as JSON.
        print(json.dumps(final_result))


if __name__ == "__main__":
    main()
