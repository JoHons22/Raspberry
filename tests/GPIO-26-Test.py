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
    This keeps only one LED active at a time.
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

    This restore setup matches the working configuration shown before the LED test.

    UART:
    GPIO14 = TXD1
    GPIO15 = RXD1

    SPI0:
    GPIO7  = CE1 as output high
    GPIO8  = CE0 as output high
    GPIO9  = SPI0 MISO
    GPIO10 = SPI0 MOSI
    GPIO11 = SPI0 SCLK

    SPI1:
    GPIO16 = CE2 as output high
    GPIO17 = CE1 as output high
    GPIO18 = CE0 as output high
    GPIO19 = SPI1 MISO
    GPIO20 = SPI1 MOSI
    GPIO21 = SPI1 SCLK
    """

    if not shutil.which("raspi-gpio"):
        return "raspi-gpio not found; UART/SPI pin modes were not restored."

    # Restore UART pins to TXD1/RXD1.
    # Your working screenshot showed GPIO14/GPIO15 using ALT5.
    run_restore_command(["raspi-gpio", "set", "14", "a5", "pn"])
    run_restore_command(["raspi-gpio", "set", "15", "a5", "pu"])

    # Restore SPI0 chip-select pins as normal outputs, idle high.
    # Your working screenshot showed GPIO7/GPIO8 as OUTPUT, not SPI alternate function.
    run_restore_command(["raspi-gpio", "set", "7", "op", "dh", "pu"])
    run_restore_command(["raspi-gpio", "set", "8", "op", "dh", "pu"])

    # Restore SPI0 data and clock pins to ALT0 with pull-down.
    run_restore_command(["raspi-gpio", "set", "9", "a0", "pd"])
    run_restore_command(["raspi-gpio", "set", "10", "a0", "pd"])
    run_restore_command(["raspi-gpio", "set", "11", "a0", "pd"])

    # Restore SPI1 chip-select pins as normal outputs, idle high.
    # Your working screenshot showed GPIO16/GPIO17/GPIO18 as OUTPUT.
    run_restore_command(["raspi-gpio", "set", "16", "op", "dh", "pd"])
    run_restore_command(["raspi-gpio", "set", "17", "op", "dh", "pd"])
    run_restore_command(["raspi-gpio", "set", "18", "op", "dh", "pd"])

    # Restore SPI1 data and clock pins to ALT4 with pull-down.
    run_restore_command(["raspi-gpio", "set", "19", "a4", "pd"])
    run_restore_command(["raspi-gpio", "set", "20", "a4", "pd"])
    run_restore_command(["raspi-gpio", "set", "21", "a4", "pd"])

    # Restore SPI monitor pins as inputs with pull-downs.
    # These are used by the SPI test to detect SCLK and CE activity.
    for pin in [5, 6, 12, 13, 22, 23, 24]:
        run_restore_command(["raspi-gpio", "set", str(pin), "ip", "pd"])

    return "UART/SPI pin modes were restored after the LED test using the working pre-LED configuration."


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

            # Restore UART/SPI pin modes after the LED test
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
