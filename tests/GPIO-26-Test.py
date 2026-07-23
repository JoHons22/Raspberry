import RPi.GPIO as GPIO
import time
import json

TEST_NAME = "GPIO 26-Pin LED Test"

# True = GPIO HIGH turns LED on
# False = GPIO LOW turns LED on
ACTIVE_HIGH = True

ON_STATE = GPIO.HIGH if ACTIVE_HIGH else GPIO.LOW
OFF_STATE = GPIO.LOW if ACTIVE_HIGH else GPIO.HIGH

SEGMENT_HOLD_TIME = 0.5

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
    for pin in pins:
        GPIO.output(pin, OFF_STATE)


def main():
    result = {
        "name": TEST_NAME,
        "status": "ERROR",
        "details": "GPIO test did not complete."
    }

    all_pins = get_all_pins()
    tested_pins = []

    try:
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

        # Configure all LED pins as outputs and start with all LEDs off
        for pin in all_pins:
            GPIO.setup(pin, GPIO.OUT)
            GPIO.output(pin, OFF_STATE)

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
                # Make sure only one LED is on at a time
                turn_all_off(all_pins)

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
        except Exception:
            pass

        # The GUI reads the final printed line as JSON.
        print(json.dumps(result))


if __name__ == "__main__":
    main()
