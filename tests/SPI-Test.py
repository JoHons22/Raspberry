import time
import json
import subprocess
from pathlib import Path

import spidev
from gpiozero import DigitalInputDevice


TEST_NAME = "SPI Test"

# Do not use an all-zero pattern.
# If MISO is disconnected or held low, received data may become all zeros.
TEST_PATTERNS = [
    [0xFF] * 8,
    [0x55, 0xAA] * 4,
    [0x12, 0x34, 0xC3, 0x3C] * 2,
    [0x5A, 0xA5, 0x0F, 0xF0] * 2
]

SPI_SETUPS = [
    {
        "name": "SPI Test 1",
        "bus": 0,
        "devices": [
            {
                "device": 0,
                "ce_name": "CE0",
                "ce_pin": 8,
                "ce_monitor": 6
            },
            {
                "device": 1,
                "ce_name": "CE1",
                "ce_pin": 7,
                "ce_monitor": 13
            }
        ],
        "required_device_files": [
            "/dev/spidev0.0",
            "/dev/spidev0.1"
        ],
        "hardware_pins": [7, 8, 9, 10, 11],
        "monitor_pins": [5, 6, 13],
        "sclk_pin": 11,
        "sclk_monitor": 5,
        "mosi_pin": 10,
        "miso_pin": 9,
        "wiring": [
            "GPIO7  CE1  -> GPIO13 monitor",
            "GPIO8  CE0  -> GPIO6 monitor",
            "GPIO9  MISO -> GPIO10 MOSI loopback",
            "GPIO11 SCLK -> GPIO5 monitor"
        ]
    },
    {
        "name": "SPI Test 2",
        "bus": 1,
        "devices": [
            {
                "device": 0,
                "ce_name": "CE0",
                "ce_pin": 18,
                "ce_monitor": 22
            },
            {
                "device": 1,
                "ce_name": "CE1",
                "ce_pin": 17,
                "ce_monitor": 23
            },
            {
                "device": 2,
                "ce_name": "CE2",
                "ce_pin": 16,
                "ce_monitor": 24
            }
        ],
        "required_device_files": [
            "/dev/spidev1.0",
            "/dev/spidev1.1",
            "/dev/spidev1.2"
        ],
        "hardware_pins": [16, 17, 18, 19, 20, 21],
        "monitor_pins": [12, 22, 23, 24],
        "sclk_pin": 21,
        "sclk_monitor": 12,
        "mosi_pin": 20,
        "miso_pin": 19,
        "wiring": [
            "GPIO16 CE2  -> GPIO24 monitor",
            "GPIO17 CE1  -> GPIO23 monitor",
            "GPIO18 CE0  -> GPIO22 monitor",
            "GPIO19 MISO -> GPIO20 MOSI loopback",
            "GPIO21 SCLK -> GPIO12 monitor"
        ]
    }
]


def run_command(command, timeout=5):
    try:
        completed = subprocess.run(
            command,
            text=True,
            capture_output=True,
            timeout=timeout
        )
        return completed.returncode, completed.stdout.strip(), completed.stderr.strip()
    except Exception as e:
        return 1, "", str(e)


def check_required_device_files(setup):
    """
    Checks that the Linux SPI device files exist before testing.
    SPI0 should provide /dev/spidev0.0 and /dev/spidev0.1.
    SPI1 with 3 chip-selects should provide /dev/spidev1.0, /dev/spidev1.1, and /dev/spidev1.2.
    """

    missing = []

    for device_file in setup["required_device_files"]:
        if not Path(device_file).exists():
            missing.append(device_file)

    return missing


def print_gpio_configuration(setup):
    """
    Prints GPIO configuration information if raspi-gpio is installed.
    This helps verify that the SPI pins are configured for hardware SPI.
    """

    pins = setup["hardware_pins"]

    command = ["raspi-gpio", "get"] + [str(pin) for pin in pins]
    code, stdout, stderr = run_command(command)

    print()
    print(f"{setup['name']} GPIO configuration check:")
    print("------------------------------------")

    if code == 0 and stdout:
        print(stdout)
    else:
        print("Could not read GPIO configuration using raspi-gpio.")
        print("This is not always fatal, but the /dev/spidev* files must exist.")


def pass_fail(value):
    return "PASS" if value else "FAIL"


def setup_edge_monitors(setup, edge_counts):
    """
    Sets monitor GPIO pins as inputs and counts signal edges.
    """

    monitors = []

    sclk_monitor_pin = setup["sclk_monitor"]

    edge_counts["sclk"] = 0

    sclk_input = DigitalInputDevice(sclk_monitor_pin, pull_up=False)
    sclk_input.when_activated = lambda: increment_edge(edge_counts, "sclk")
    sclk_input.when_deactivated = lambda: increment_edge(edge_counts, "sclk")
    monitors.append(sclk_input)

    for device_info in setup["devices"]:
        key = device_info["ce_name"].lower()
        monitor_pin = device_info["ce_monitor"]

        edge_counts[key] = 0

        ce_input = DigitalInputDevice(monitor_pin, pull_up=False)
        ce_input.when_activated = lambda key=key: increment_edge(edge_counts, key)
        ce_input.when_deactivated = lambda key=key: increment_edge(edge_counts, key)
        monitors.append(ce_input)

    return monitors


def increment_edge(edge_counts, key):
    edge_counts[key] += 1


def close_monitors(monitors):
    for monitor in monitors:
        try:
            monitor.close()
        except Exception:
            pass


def run_spi_device_test(setup, device_info, edge_counts):
    """
    Tests one SPI chip-select device.
    Example:
    SPI0 CE0 -> /dev/spidev0.0
    SPI0 CE1 -> /dev/spidev0.1
    SPI1 CE0 -> /dev/spidev1.0
    SPI1 CE1 -> /dev/spidev1.1
    SPI1 CE2 -> /dev/spidev1.2
    """

    bus = setup["bus"]
    device = device_info["device"]
    ce_name = device_info["ce_name"]
    ce_key = ce_name.lower()

    device_path = f"/dev/spidev{bus}.{device}"

    result = {
        "setup": setup["name"],
        "device_path": device_path,
        "ce_name": ce_name,
        "data_pass": False,
        "sclk_pass": False,
        "ce_pass": False,
        "overall_pass": False,
        "all_received_zero": False,
        "details": "",
        "error": None
    }

    spi = None

    try:
        # Reset counts for this specific transfer group
        edge_counts["sclk"] = 0
        edge_counts[ce_key] = 0

        spi = spidev.SpiDev()
        spi.open(bus, device)

        # Slow speed helps Python edge monitors catch SCLK and CE activity.
        spi.max_speed_hz = 1000
        spi.mode = 0

        print()
        print(f"Testing {setup['name']} {ce_name}: {device_path}")
        print("----------------------------------------")

        all_patterns_passed = True
        all_received_zero = True

        for pattern in TEST_PATTERNS:
            sent = pattern.copy()
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

        data_pass = all_patterns_passed
        sclk_pass = edge_counts["sclk"] > 0
        ce_pass = edge_counts[ce_key] > 0

        if data_pass:
            data_message = "data loopback PASS"
        elif all_received_zero:
            data_message = "data loopback FAIL - received all zeros"
        else:
            data_message = "data loopback FAIL - received data did not match sent data"

        result["data_pass"] = data_pass
        result["sclk_pass"] = sclk_pass
        result["ce_pass"] = ce_pass
        result["overall_pass"] = data_pass and sclk_pass and ce_pass
        result["all_received_zero"] = all_received_zero
        result["details"] = (
            f"{device_path} {ce_name}: "
            f"{data_message}, "
            f"SCLK activity {pass_fail(sclk_pass)}, "
            f"{ce_name} activity {pass_fail(ce_pass)}"
        )

        print(result["details"])

        return result

    except Exception as e:
        result["error"] = str(e)
        result["details"] = f"{device_path} {ce_name}: ERROR - {e}"
        print(result["details"])
        return result

    finally:
        if spi is not None:
            try:
                spi.close()
            except Exception:
                pass


def run_spi_setup(setup):
    """
    Runs a full SPI setup.
    SPI Test 1 checks SPI0 CE0 and CE1.
    SPI Test 2 checks SPI1 CE0, CE1, and CE2.
    """

    setup_result = {
        "name": setup["name"],
        "status": "ERROR",
        "details": "",
        "device_results": []
    }

    print()
    print("=" * 60)
    print(setup["name"])
    print("=" * 60)

    print("Expected wiring:")
    for line in setup["wiring"]:
        print(f"  {line}")

    print_gpio_configuration(setup)

    missing_devices = check_required_device_files(setup)

    if missing_devices:
        details = (
            f"{setup['name']} cannot run because these SPI device files are missing: "
            f"{', '.join(missing_devices)}. "
        )

        if setup["bus"] == 0:
            details += (
                "Enable SPI0 using raspi-config: Interface Options -> SPI -> Enable."
            )
        elif setup["bus"] == 1:
            details += (
                "Enable SPI1 with 3 chip-selects in the Raspberry Pi config using "
                "dtoverlay=spi1-3cs, then reboot."
            )

        setup_result["status"] = "ERROR"
        setup_result["details"] = details

        print(details)
        return setup_result

    edge_counts = {}
    monitors = []

    try:
        monitors = setup_edge_monitors(setup, edge_counts)

        for device_info in setup["devices"]:
            device_result = run_spi_device_test(setup, device_info, edge_counts)
            setup_result["device_results"].append(device_result)

        if all(result["overall_pass"] for result in setup_result["device_results"]):
            setup_result["status"] = "PASS"
        elif any(result["error"] for result in setup_result["device_results"]):
            setup_result["status"] = "ERROR"
        else:
            setup_result["status"] = "FAIL"

        setup_result["details"] = "; ".join(
            result["details"] for result in setup_result["device_results"]
        )

        return setup_result

    except Exception as e:
        setup_result["status"] = "ERROR"
        setup_result["details"] = f"{setup['name']} ERROR - {e}"
        return setup_result

    finally:
        close_monitors(monitors)


def build_final_details(setup_results):
    details = []

    for setup_result in setup_results:
        details.append(
            f"{setup_result['name']}: {setup_result['status']} - "
            f"{setup_result['details']}"
        )

    return " | ".join(details)


def determine_final_status(setup_results):
    if any(result["status"] == "ERROR" for result in setup_results):
        return "ERROR"

    if all(result["status"] == "PASS" for result in setup_results):
        return "PASS"

    return "FAIL"


def main():
    final_result = {
        "name": TEST_NAME,
        "status": "ERROR",
        "details": "SPI test did not complete."
    }

    setup_results = []

    try:
        print("SPI FULL SETUP TEST")
        print("===================")
        print("This test checks both SPI setups.")
        print("GPIO numbering mode: BCM")
        print()

        for setup in SPI_SETUPS:
            setup_result = run_spi_setup(setup)
            setup_results.append(setup_result)

        final_result = {
            "name": TEST_NAME,
            "status": determine_final_status(setup_results),
            "details": build_final_details(setup_results)
        }

    except Exception as e:
        final_result = {
            "name": TEST_NAME,
            "status": "ERROR",
            "details": str(e)
        }

    print()
    print("FINAL RESULT")
    print("============")
    print(final_result["details"])

    # The main GUI reads the final printed line as JSON.
    print(json.dumps(final_result))


if __name__ == "__main__":
    main()
