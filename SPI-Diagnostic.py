import json
import time
import spidev

TEST_NAME = "SPI Raw Diagnostic"

# Do NOT include [0x00] patterns here.
# If MISO is pulled down and disconnected, received data should become all 0s,
# which should fail against these patterns.
TEST_PATTERNS = [
    [0xFF] * 8,
    [0x55, 0xAA] * 4,
    [0x12, 0x34, 0xC3, 0x3C] * 2,
    [0x5A, 0xA5, 0x0F, 0xF0] * 2
]


def pass_fail(value):
    return "PASS" if value else "FAIL"


def run_raw_spi_test(device_number):
    """
    Tests raw MOSI/MISO loopback on /dev/spidev0.0 or /dev/spidev0.1.
    device_number = 0 uses CE0
    device_number = 1 uses CE1
    """

    spi = None

    device_name = f"/dev/spidev0.{device_number}"

    result = {
        "device": device_name,
        "patterns": [],
        "data_pass": False,
        "all_received_zero": False,
        "error": None
    }

    try:
        spi = spidev.SpiDev()
        spi.open(0, device_number)

        spi.max_speed_hz = 1000
        spi.mode = 0

        print()
        print(f"Testing {device_name}")
        print("--------------------------------")

        all_patterns_passed = True
        all_received_zero = True

        for pattern in TEST_PATTERNS:
            # Keep a protected copy of what we intended to send.
            sent = pattern.copy()

            # Send a separate copy so the displayed sent value cannot be changed.
            tx_buffer = sent.copy()

            time.sleep(0.1)
            received = spi.xfer2(tx_buffer)

            match = received == sent

            if any(byte != 0 for byte in received):
                all_received_zero = False

            print(f"Sent:     {sent}")
            print(f"Received: {received}")
            print(f"Match:    {match}")
            print()

            result["patterns"].append({
                "sent": sent,
                "received": received,
                "match": match
            })

            if not match:
                all_patterns_passed = False

        result["data_pass"] = all_patterns_passed
        result["all_received_zero"] = all_received_zero

        if all_patterns_passed:
            print(f"{device_name} MOSI/MISO loopback: PASS")
        elif all_received_zero:
            print(f"{device_name} MOSI/MISO loopback: FAIL - MISO stayed LOW, likely no loopback data received")
        else:
            print(f"{device_name} MOSI/MISO loopback: FAIL - received data did not match sent data")

        return result

    except Exception as e:
        result["error"] = str(e)
        print()
        print(f"Testing {device_name}")
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
    elif ce0_result["data_pass"]:
        details.append("CE0 raw MOSI/MISO PASS")
    elif ce0_result["all_received_zero"]:
        details.append("CE0 raw MOSI/MISO FAIL, received all 0s")
    else:
        details.append("CE0 raw MOSI/MISO FAIL, received data mismatch")

    if ce1_result["error"]:
        details.append(f"CE1 ERROR: {ce1_result['error']}")
    elif ce1_result["data_pass"]:
        details.append("CE1 raw MOSI/MISO PASS")
    elif ce1_result["all_received_zero"]:
        details.append("CE1 raw MOSI/MISO FAIL, received all 0s")
    else:
        details.append("CE1 raw MOSI/MISO FAIL, received data mismatch")

    return "; ".join(details)


def main():
    print("SPI RAW DIAGNOSTIC")
    print("==================")
    print("Required wiring:")
    print("MOSI GPIO10, physical pin 19 -> MISO GPIO9, physical pin 21")
    print("MISO GPIO9, physical pin 21 -> 10k resistor -> GND")
    print()
    print("Expected behavior:")
    print("Connected:    Sent data should match received data")
    print("Disconnected: Sent data should stay nonzero, received data should become all 0s")
    print()

    final_result = {
        "name": TEST_NAME,
        "status": "ERROR",
        "details": "Diagnostic did not complete."
    }

    try:
        ce0_result = run_raw_spi_test(0)
        ce1_result = run_raw_spi_test(1)

        details = build_details(ce0_result, ce1_result)

        ce0_pass = ce0_result["data_pass"] and ce0_result["error"] is None
        ce1_pass = ce1_result["data_pass"] and ce1_result["error"] is None

        print()
        print("FINAL RESULT")
        print("============")
        print(details)

        if ce0_pass and ce1_pass:
            final_result = {
                "name": TEST_NAME,
                "status": "PASS",
                "details": details
            }
        else:
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

    # Last line is JSON so the GUI can read it if needed.
    print(json.dumps(final_result))


if __name__ == "__main__":
    main()
