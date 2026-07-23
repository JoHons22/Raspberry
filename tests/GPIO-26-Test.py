import RPi.GPIO as GPIO
import time
import json
import subprocess
import shutil

TEST_NAME = "GPIO 26-Pin LED Test"

# True = GPIO HIGH turns LED on
# False = GPIO LOW turns LED on
ACTIVE_HIGH = True

ON_STATE = GPIO.HIGH if ACTIVE_HIGH else GPIO.LOW
OFF_STATE = GPIO.LOW if ACTIVE_HIGH else GPIO.HIGH

SEGMENT_HOLD_TIME = 0.5
CLEANUP_DELAY = 0.5

# UART restore setting:
# Use "a0" if raspi-gpio showed GPIO14/GPIO15 as TXD0/RXD0 before the LED test.
# Use "a5" if raspi-gpio showed GPIO14/GPIO15 as TXD1/RXD1 before the LED test.
UART_ALT_FUNCTION = "a0"

display_map = {
    "Display 1": {
        "segment_1": 2,
        "segment_2": 3,
        "segment_3": 4,
        "segment_4": 5,
        "segment_5": 6,
        "segment_6": 7,
        "segment_7": 8,
        "segment_8": 9,
        "segment_9": 10,
        "segment_10": 11
    },
    "Display 2": {
        "segment_1": 12,
        "segment_2": 13,
        "segment_3": 14,
        "segment_4": 15,
        "segment_5": 16,
        "segment_6": 17,
        "segment_7": 18,
        "segment_8": 19,
        "segment_9": 20,
        "segment_10": 21
    },
    "Display 3": {
        "segment_1": 22,
        "segment_2": 23,
        "segment_3": 24,
        "segment_4": 25,
        "segment_5": 26,
        "segment_6": 27
    }
}


def get_all_pins():
    pins = []

    for display_segments in display_map.values():
        for pin in display_segments.values():
            pins.append(pin)

    return pins


def turn_all_off(pins):
    """
    Turns every LED output off.
    This is called before each individual LED turns on so only one LED is active.
    """
    for pin in pins:
        GPIO.output(pin, OFF_STATE)


def setup_led_pins(pins):
    """
    Configures all LED pins as normal GPIO outputs.
    """
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)

    for pin in pins:
        GPIO.setup(pin, GPIO.OUT)
        GPIO.output(pin, OFF_STATE)


def run_restore_command(command):
    """
    Runs a raspi-gpio restore command.
    Errors are ignored so the LED test can still finish normally.
    """
    try:
        subprocess.run(
            command,
            text=True,
            capture_output=True,
            timeout=3
        )
    except Exception:
        pass


def restore_uart_spi_pin_modes():
    """
    Restores UART and SPI pins after the LED test uses them as normal GPIO outputs.

    UART:
    GPIO14 = TXD
    GPIO15 = RXD

    SPI0:
    GPIO7  = CE1
    GPIO8  = CE0
    GPIO9  = MISO
    GPIO10 = MOSI
    GPIO11 = SCLK

    SPI1:
    GPIO16 = CE2
    GPIO17 = CE1
    GPIO18 = CE0
    GPIO19 = MISO
    GPIO20 = MOSI
    GPIO21 = SCLK
    """

    if not shutil.which("raspi-gpio"):
        return "raspi-gpio not found; UART/SPI pin modes were not restored."

    # Restore UART pins.
    # Change UART_ALT_FUNCTION to "a5" if your working pin check showed TXD1/RXD1.
    run_restore_command(["raspi-gpio", "set", "14", UART_ALT_FUNCTION])
    run_restore_command(["raspi-gpio", "set", "15", UART_ALT_FUNCTION])

    # Restore SPI0 pins.
    # SPI0 uses ALT0.
    for pin in [7, 8, 9, 10, 11]:
        run_restore_command(["raspi-gpio", "set", str(pin), "a0"])

    # Restore SPI1 pins.
    # SPI1 uses ALT4.
    for pin in [16, 17, 18, 19, 20, 21]:
        run_restore_command(["raspi-gpio", "set", str(pin), "a4"])

    return "UART/SPI pin modes were restored after the LED test."


def main():
    result = {
        "name": TEST_NAME,
        "status": "ERROR",
        "details": "GPIO test did not complete."
    }

    all_pins = get_all_pins()
    tested_pins = []
    restore_details = "UART/SPI pin restoration did not run."

    try:
        setup_led_pins(all_pins)

        print("GPIO 26-PIN LED TEST")
        print("====================")
        print("This test cycles GPIO 2 through GPIO 27.")
        print("Only one LED segment is turned on at a time.")
        print("The final all-LEDs-on check has been removed to reduce current draw.")
        print("Use one current-limiting resistor per LED segment.")
        print("Display 3 only uses 6 of its 10 segments.")
        print()

        print("===== STARTING GPIO TEST CYCLE =====")
        time.sleep(0.5)

        for display_name, segments in display_map.items():
            print()
            print(f"--- {display_name} ---")

            for segment_name, pin in segments.items():
                # Make sure every LED is off before turning on the next one
                turn_all_off(all_pins)
                time.sleep(0.05)

                GPIO.output(pin, ON_STATE)
                tested_pins.append(pin)

                print(f"Testing {display_name} {segment_name} on GPIO {pin}")
                time.sleep(SEGMENT_HOLD_TIME)

        print()
        print("===== END OF GPIO TEST CYCLE =====")

        # Turn everything off at the end
        turn_all_off(all_pins)

        result = {
            "name": TEST_NAME,
            "status": "WARN",
            "details": (
                f"Commanded {len(tested_pins)} GPIO pins from GPIO 2 through GPIO 27. "
                "Each LED was tested individually with only one LED on at a time. "
                "The final all-LEDs-on check was removed to reduce current draw. "
                "Manual visual confirmation is required."
            )
        }

    except Exception as e:
        result = {
            "name": TEST_NAME,
            "status": "ERROR",
            "details": str(e)
        }

    finally:
        try:
            turn_all_off(all_pins)
            GPIO.cleanup()

            # Short delay to let GPIO cleanup settle
            time.sleep(CLEANUP_DELAY)

            # Restore UART/SPI alternate functions so those tests can work again
            restore_details = restore_uart_spi_pin_modes()
            print(restore_details)

        except Exception as e:
            restore_details = f"GPIO cleanup or pin restore error: {e}"
            print(restore_details)

        result["details"] = result["details"] + f" {restore_details}"

        # The GUI reads the final printed line as JSON.
        print(json.dumps(result))


if __name__ == "__main__":
    main()
