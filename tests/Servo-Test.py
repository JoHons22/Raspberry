import json
import time
import tkinter as tk
from tkinter import messagebox
import RPi.GPIO as GPIO

TEST_NAME = "Servo PWM Test"

SERVO_FREQUENCY = 50
ANGLE_HOLD_TIME = 0.6
PAUSE_BETWEEN_ANGLES = 0.4

PWM_TESTS = [
    {
        "test_number": 1,
        "gpio": 12,
        "name": "Servo PWM Test 1 - GPIO12",
        "switch_prompt": (
            "Set the switches for Servo PWM Test 1.\n\n"
            "PWM output being tested: BCM GPIO12\n\n"
            "Placeholder switch position:\n"
            "TBD switch setting for GPIO12."
        )
    },
    {
        "test_number": 2,
        "gpio": 18,
        "name": "Servo PWM Test 2 - GPIO18",
        "switch_prompt": (
            "Set the switches for Servo PWM Test 2.\n\n"
            "PWM output being tested: BCM GPIO18\n\n"
            "Placeholder switch position:\n"
            "TBD switch setting for GPIO18."
        )
    },
    {
        "test_number": 3,
        "gpio": 13,
        "name": "Servo PWM Test 3 - GPIO13",
        "switch_prompt": (
            "Set the switches for Servo PWM Test 3.\n\n"
            "PWM output being tested: BCM GPIO13\n\n"
            "Placeholder switch position:\n"
            "TBD switch setting for GPIO13."
        )
    },
    {
        "test_number": 4,
        "gpio": 19,
        "name": "Servo PWM Test 4 - GPIO19",
        "switch_prompt": (
            "Set the switches for Servo PWM Test 4.\n\n"
            "PWM output being tested: BCM GPIO19\n\n"
            "Placeholder switch position:\n"
            "TBD switch setting for GPIO19."
        )
    }
]


def create_popup_root():
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    return root


def ask_switch_confirmation(root, test_info):
    message = (
        f"{test_info['name']}\n\n"
        f"{test_info['switch_prompt']}\n\n"
        "All wiring is automatic. Only change the switch positions.\n\n"
        "Click Yes once the switches are in the correct position.\n"
        "Click No to skip this PWM test."
    )

    return messagebox.askyesno(
        "Switch Position Confirmation",
        message,
        parent=root
    )


def ask_observation_confirmation(root, test_info):
    message = (
        f"{test_info['name']}\n\n"
        "Did the servo move correctly?\n\n"
        "Expected movement:\n"
        "0 degrees → 90 degrees → 180 degrees → 90 degrees\n\n"
        "Click Yes if this PWM setup passed.\n"
        "Click No if this PWM setup failed."
    )

    return messagebox.askyesno(
        "Manual Servo Observation",
        message,
        parent=root
    )


def set_angle(pwm, angle):
    """
    SG90-style servo control.
    Duty cycle values are approximate and may need adjustment for different servos.
    """
    duty = 2 + (angle / 18)

    pwm.ChangeDutyCycle(duty)
    time.sleep(ANGLE_HOLD_TIME)

    # Stop active duty cycle to reduce jitter
    pwm.ChangeDutyCycle(0)
    time.sleep(PAUSE_BETWEEN_ANGLES)


def run_single_pwm_test(root, test_info):
    gpio_pin = test_info["gpio"]
    test_name = test_info["name"]
    pwm = None

    print()
    print("=" * 45)
    print(test_name)
    print("=" * 45)
    print(f"Testing BCM GPIO{gpio_pin}")

    switch_confirmed = ask_switch_confirmation(root, test_info)

    if not switch_confirmed:
        return {
            "name": test_name,
            "gpio": gpio_pin,
            "status": "SKIP",
            "details": f"{test_name} was skipped because switch position was not confirmed."
        }

    try:
        GPIO.setup(gpio_pin, GPIO.OUT)

        pwm = GPIO.PWM(gpio_pin, SERVO_FREQUENCY)
        pwm.start(0)

        print("Moving servo to 0 degrees")
        set_angle(pwm, 0)

        print("Moving servo to 90 degrees")
        set_angle(pwm, 90)

        print("Moving servo to 180 degrees")
        set_angle(pwm, 180)

        print("Returning servo to 90 degrees")
        set_angle(pwm, 90)

        observed_pass = ask_observation_confirmation(root, test_info)

        if observed_pass:
            return {
                "name": test_name,
                "gpio": gpio_pin,
                "status": "PASS",
                "details": f"{test_name} passed manual observation."
            }
        else:
            return {
                "name": test_name,
                "gpio": gpio_pin,
                "status": "FAIL",
                "details": f"{test_name} failed manual observation."
            }

    except Exception as e:
        return {
            "name": test_name,
            "gpio": gpio_pin,
            "status": "ERROR",
            "details": str(e)
        }

    finally:
        if pwm is not None:
            pwm.stop()

        try:
            GPIO.output(gpio_pin, GPIO.LOW)
        except Exception:
            pass


def build_final_details(subtest_results):
    details_parts = []

    for result in subtest_results:
        details_parts.append(
            f"{result['name']} on GPIO{result['gpio']}: "
            f"{result['status']} - {result['details']}"
        )

    pass_count = sum(1 for result in subtest_results if result["status"] == "PASS")
    fail_count = sum(1 for result in subtest_results if result["status"] == "FAIL")
    skip_count = sum(1 for result in subtest_results if result["status"] == "SKIP")
    error_count = sum(1 for result in subtest_results if result["status"] == "ERROR")

    summary = (
        f"Passed {pass_count} of {len(PWM_TESTS)} servo PWM tests. "
        f"Failures: {fail_count}. Skipped: {skip_count}. Errors: {error_count}. "
    )

    return summary + " | ".join(details_parts)


def determine_final_status(subtest_results):
    if any(result["status"] == "ERROR" for result in subtest_results):
        return "ERROR"

    if all(result["status"] == "PASS" for result in subtest_results):
        return "PASS"

    return "FAIL"


def main():
    popup_root = None

    final_result = {
        "name": TEST_NAME,
        "status": "ERROR",
        "details": "Servo PWM test did not complete."
    }

    subtest_results = []

    try:
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

        popup_root = create_popup_root()

        print("SERVO PWM TEST")
        print("==============")
        print("This single GUI test checks four PWM GPIO setups.")
        print("GPIO numbering mode: BCM")
        print("Test order: GPIO12, GPIO18, GPIO13, GPIO19")

        for test_info in PWM_TESTS:
            result = run_single_pwm_test(popup_root, test_info)
            subtest_results.append(result)

            print(
                f"{result['name']}: {result['status']} - "
                f"{result['details']}"
            )

        final_result = {
            "name": TEST_NAME,
            "status": determine_final_status(subtest_results),
            "details": build_final_details(subtest_results)
        }

    except Exception as e:
        final_result = {
            "name": TEST_NAME,
            "status": "ERROR",
            "details": str(e)
        }

    finally:
        GPIO.cleanup()

        if popup_root is not None:
            popup_root.destroy()

        # The main GUI reads the final printed line as JSON.
        print(json.dumps(final_result))


if __name__ == "__main__":
    main()
