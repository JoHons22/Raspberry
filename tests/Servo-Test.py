import json
import time
import tkinter as tk
from tkinter import messagebox
import subprocess
import shutil
import RPi.GPIO as GPIO

TEST_NAME = "Servo PWM Test"

SERVO_FREQUENCY = 50
ANGLE_HOLD_TIME = 0.6
PAUSE_BETWEEN_ANGLES = 0.4
CLEANUP_DELAY = 0.5

PWM_TESTS = [
    {
        "test_number": 1,
        "gpio": 12,
        "name": "PWM Test 1 - GPIO12",
        "switch_prompt": (
            "Set the switch bank to route the servo signal line to GPIO12.\n\n"
            "GPIO12 is BCM GPIO12, physical pin 32."
        )
    },
    {
        "test_number": 2,
        "gpio": 18,
        "name": "PWM Test 2 - GPIO18",
        "switch_prompt": (
            "Set the switch bank to route the servo signal line to GPIO18.\n\n"
            "GPIO18 is BCM GPIO18, physical pin 12."
        )
    },
    {
        "test_number": 3,
        "gpio": 13,
        "name": "PWM Test 3 - GPIO13",
        "switch_prompt": (
            "Set the switch bank to route the servo signal line to GPIO13.\n\n"
            "GPIO13 is BCM GPIO13, physical pin 33."
        )
    },
    {
        "test_number": 4,
        "gpio": 19,
        "name": "PWM Test 4 - GPIO19",
        "switch_prompt": (
            "Set the switch bank to route the servo signal line to GPIO19.\n\n"
            "GPIO19 is BCM GPIO19, physical pin 35."
        )
    }
]


def run_restore_command(command):
    """
    Runs a raspi-gpio restore command.
    Errors are ignored so the servo test can still finish normally.
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


def restore_shared_pin_modes():
    """
    Restores shared communication pins after the servo test uses some of them
    as normal PWM GPIO outputs.

    This matches the same recovery approach used for the GPIO LED test.

    I2C:
    GPIO2  = SDA1
    GPIO3  = SCL1

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

    SPI monitor pins:
    GPIO5, GPIO6, GPIO12, GPIO13, GPIO22, GPIO23, GPIO24 = input pull-down
    """

    if not shutil.which("raspi-gpio"):
        return "raspi-gpio not found; shared pin modes were not restored."

    # Restore I2C pins.
    run_restore_command(["raspi-gpio", "set", "2", "a0", "pu"])
    run_restore_command(["raspi-gpio", "set", "3", "a0", "pu"])

    # Restore UART pins.
    # Your previous working configuration used TXD1/RXD1, which is ALT5.
    run_restore_command(["raspi-gpio", "set", "14", "a5", "pn"])
    run_restore_command(["raspi-gpio", "set", "15", "a5", "pu"])

    # Restore SPI0 chip-select pins as normal outputs, idle high.
    run_restore_command(["raspi-gpio", "set", "7", "op", "dh", "pu"])
    run_restore_command(["raspi-gpio", "set", "8", "op", "dh", "pu"])

    # Restore SPI0 data and clock pins to ALT0.
    run_restore_command(["raspi-gpio", "set", "9", "a0", "pd"])
    run_restore_command(["raspi-gpio", "set", "10", "a0", "pd"])
    run_restore_command(["raspi-gpio", "set", "11", "a0", "pd"])

    # Restore SPI1 chip-select pins as normal outputs, idle high.
    run_restore_command(["raspi-gpio", "set", "16", "op", "dh", "pd"])
    run_restore_command(["raspi-gpio", "set", "17", "op", "dh", "pd"])
    run_restore_command(["raspi-gpio", "set", "18", "op", "dh", "pd"])

    # Restore SPI1 data and clock pins to ALT4.
    run_restore_command(["raspi-gpio", "set", "19", "a4", "pd"])
    run_restore_command(["raspi-gpio", "set", "20", "a4", "pd"])
    run_restore_command(["raspi-gpio", "set", "21", "a4", "pd"])

    # Restore SPI monitor pins as inputs with pull-downs.
    for pin in [5, 6, 12, 13, 22, 23, 24]:
        run_restore_command(["raspi-gpio", "set", str(pin), "ip", "pd"])

    return "Shared I2C/UART/SPI pin modes were restored after the servo test."


def create_popup_root():
    """
    Creates a hidden Tkinter root for message boxes.
    """
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    return root


def ask_switch_confirmation(root, test_info):
    """
    Ask the user to set the switch bank before each internal PWM test.
    """
    return messagebox.askyesno(
        "Servo PWM Switch Setup",
        (
            f"{test_info['name']}\n\n"
            f"{test_info['switch_prompt']}\n\n"
            "Click Yes when the switch bank is set correctly.\n"
            "Click No to skip this PWM test."
        ),
        parent=root
    )


def ask_observation_confirmation(root, test_info):
    """
    Ask the user if the servo moved correctly.
    """
    return messagebox.askyesno(
        "Servo Movement Confirmation",
        (
            f"{test_info['name']}\n\n"
            "The servo should have moved through these positions:\n\n"
            "0 degrees → 90 degrees → 180 degrees → 90 degrees\n\n"
            "Did the servo move correctly?"
        ),
        parent=root
    )


def set_angle(pwm, angle):
    """
    Converts a servo angle to duty cycle for a typical SG90 servo.

    Approximate SG90 duty cycle:
    0 degrees   ≈ 2%
    90 degrees  ≈ 7%
    180 degrees ≈ 12%
    """
    duty_cycle = 2 + (angle / 18)

    pwm.ChangeDutyCycle(duty_cycle)
    time.sleep(ANGLE_HOLD_TIME)

    # Stop sending a constant duty cycle to reduce servo jitter.
    pwm.ChangeDutyCycle(0)
    time.sleep(PAUSE_BETWEEN_ANGLES)


def run_single_pwm_test(root, test_info):
    """
    Runs one internal servo PWM test on one GPIO pin.
    """
    pin = test_info["gpio"]

    print()
    print(f"===== {test_info['name']} =====")
    print(f"Testing PWM output on GPIO{pin}")

    user_ready = ask_switch_confirmation(root, test_info)

    if not user_ready:
        return {
            "name": test_info["name"],
            "status": "SKIP",
            "details": f"User skipped PWM test on GPIO{pin}."
        }

    pwm = None

    try:
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

        GPIO.setup(pin, GPIO.OUT)
        pwm = GPIO.PWM(pin, SERVO_FREQUENCY)
        pwm.start(0)

        print("Moving servo to 0 degrees.")
        set_angle(pwm, 0)

        print("Moving servo to 90 degrees.")
        set_angle(pwm, 90)

        print("Moving servo to 180 degrees.")
        set_angle(pwm, 180)

        print("Returning servo to 90 degrees.")
        set_angle(pwm, 90)

        movement_ok = ask_observation_confirmation(root, test_info)

        if movement_ok:
            return {
                "name": test_info["name"],
                "status": "PASS",
                "details": f"Servo movement was confirmed on GPIO{pin}."
            }

        return {
            "name": test_info["name"],
            "status": "FAIL",
            "details": f"User reported incorrect servo movement on GPIO{pin}."
        }

    except Exception as e:
        return {
            "name": test_info["name"],
            "status": "ERROR",
            "details": f"Error while testing GPIO{pin}: {e}"
        }

    finally:
        try:
            if pwm is not None:
                pwm.ChangeDutyCycle(0)
                pwm.stop()
        except Exception:
            pass

        try:
            GPIO.cleanup(pin)
        except Exception:
            pass


def combine_results(subtest_results, restore_details):
    """
    Combines all internal PWM test results into one GUI result.
    """
    pass_count = 0
    fail_count = 0
    skip_count = 0
    error_count = 0

    detail_lines = []

    for result in subtest_results:
        status = result["status"]

        if status == "PASS":
            pass_count += 1
        elif status == "FAIL":
            fail_count += 1
        elif status == "SKIP":
            skip_count += 1
        elif status == "ERROR":
            error_count += 1

        detail_lines.append(
            f"{result['name']}: {result['status']} - {result['details']}"
        )

    detail_lines.append(restore_details)

    if error_count > 0:
        overall_status = "ERROR"
    elif fail_count > 0:
        overall_status = "FAIL"
    elif pass_count > 0 and skip_count == 0:
        overall_status = "PASS"
    elif pass_count > 0 and skip_count > 0:
        overall_status = "WARN"
    else:
        overall_status = "SKIP"

    details = (
        f"Servo PWM testing completed. "
        f"PASS={pass_count}, FAIL={fail_count}, SKIP={skip_count}, ERROR={error_count}. "
        + " | ".join(detail_lines)
    )

    return {
        "name": TEST_NAME,
        "status": overall_status,
        "details": details
    }


def main():
    popup_root = None
    subtest_results = []
    restore_details = "Shared pin restoration did not run."

    try:
        popup_root = create_popup_root()

        print("SERVO PWM TEST")
        print("==============")
        print("This test checks four PWM-capable GPIO setups.")
        print("The user will be prompted to change the switch position before each PWM test.")
        print()

        for test_info in PWM_TESTS:
            subtest_result = run_single_pwm_test(popup_root, test_info)
            subtest_results.append(subtest_result)

        # Cleanup all GPIO use from the servo test.
        try:
            GPIO.cleanup()
        except Exception:
            pass

        time.sleep(CLEANUP_DELAY)

        # Restore shared pin modes so SPI, UART, and I2C tests can work after this test.
        restore_details = restore_shared_pin_modes()
        print(restore_details)

        result = combine_results(subtest_results, restore_details)

    except Exception as e:
        result = {
            "name": TEST_NAME,
            "status": "ERROR",
            "details": f"Servo PWM test error: {e}"
        }

    finally:
        try:
            if popup_root is not None:
                popup_root.destroy()
        except Exception:
            pass

    print(json.dumps(result))


if __name__ == "__main__":
    main()
