import json
import time
import tkinter as tk
from tkinter import ttk
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


def show_touch_popup(
    title,
    message,
    popup_type="yesno",
    yes_text="Yes",
    no_text="No",
    ok_text="OK"
):
    """
    Creates a visible touchscreen-friendly popup.

    This version uses the Tk root window directly instead of using
    a hidden root plus a Toplevel window. This prevents the servo test
    from stalling while waiting for an invisible popup.
    """
    result = {"value": None}

    popup = tk.Tk()
    popup.title(title)

    screen_width = popup.winfo_screenwidth()
    screen_height = popup.winfo_screenheight()

    popup_width = min(760, max(420, screen_width - 40))
    popup_height = min(400, max(300, screen_height - 80))

    popup_x = max(0, int((screen_width - popup_width) / 2))
    popup_y = max(0, int((screen_height - popup_height) / 2))

    popup.geometry(f"{popup_width}x{popup_height}+{popup_x}+{popup_y}")
    popup.resizable(False, False)
    popup.attributes("-topmost", True)

    style = ttk.Style()

    try:
        style.theme_use("clam")
    except Exception:
        pass

    style.configure("TButton", font=("Arial", 11), padding=(6, 8))
    style.configure("TLabel", font=("Arial", 10))

    main_frame = ttk.Frame(popup, padding=8)
    main_frame.pack(fill="both", expand=True)

    title_label = ttk.Label(
        main_frame,
        text=title,
        font=("Arial", 12, "bold"),
        anchor="center"
    )
    title_label.pack(fill="x", pady=(0, 6))

    text_frame = ttk.Frame(main_frame)
    text_frame.pack(fill="both", expand=True)

    message_text = tk.Text(
        text_frame,
        wrap="word",
        font=("Arial", 10),
        padx=6,
        pady=6
    )

    text_scrollbar = ttk.Scrollbar(
        text_frame,
        orient="vertical",
        command=message_text.yview
    )

    message_text.configure(yscrollcommand=text_scrollbar.set)
    message_text.insert("1.0", message)
    message_text.config(state="disabled")

    message_text.pack(side="left", fill="both", expand=True)
    text_scrollbar.pack(side="right", fill="y")

    button_frame = ttk.Frame(main_frame)
    button_frame.pack(fill="x", pady=(8, 0))

    def close_with_value(value):
        result["value"] = value
        popup.quit()

    if popup_type == "yesno":
        button_frame.columnconfigure(0, weight=1)
        button_frame.columnconfigure(1, weight=1)

        yes_button = ttk.Button(
            button_frame,
            text=yes_text,
            command=lambda: close_with_value(True)
        )
        yes_button.grid(row=0, column=0, sticky="ew", padx=(0, 4), ipady=8)

        no_button = ttk.Button(
            button_frame,
            text=no_text,
            command=lambda: close_with_value(False)
        )
        no_button.grid(row=0, column=1, sticky="ew", padx=(4, 0), ipady=8)

        popup.bind("<Return>", lambda event: close_with_value(True))
        popup.bind("<Escape>", lambda event: close_with_value(False))
        yes_button.focus_set()

    else:
        button_frame.columnconfigure(0, weight=1)

        ok_button = ttk.Button(
            button_frame,
            text=ok_text,
            command=lambda: close_with_value(True)
        )
        ok_button.grid(row=0, column=0, sticky="ew", padx=80, ipady=8)

        popup.bind("<Return>", lambda event: close_with_value(True))
        popup.bind("<Escape>", lambda event: close_with_value(True))
        ok_button.focus_set()

    def on_close():
        if popup_type == "yesno":
            close_with_value(False)
        else:
            close_with_value(True)

    popup.protocol("WM_DELETE_WINDOW", on_close)

    popup.update_idletasks()
    popup.lift()
    popup.focus_force()

    popup.mainloop()

    try:
        popup.destroy()
    except Exception:
        pass

    return result["value"]


def ask_switch_confirmation(test_info):
    return show_touch_popup(
        "Servo Switch Setup",
        (
            f"{test_info['name']}\n\n"
            f"{test_info['switch_prompt']}\n\n"
            "Press Continue when the switch bank is set correctly.\n"
            "Press Skip to skip this PWM test."
        ),
        popup_type="yesno",
        yes_text="Continue",
        no_text="Skip"
    )


def ask_observation_confirmation(test_info):
    return show_touch_popup(
        "Servo Movement Check",
        (
            f"{test_info['name']}\n\n"
            "The servo should have moved through these positions:\n\n"
            "0 degrees → 90 degrees → 180 degrees → 90 degrees\n\n"
            "Press PASS if the servo moved correctly.\n"
            "Press FAIL if the servo did not move correctly."
        ),
        popup_type="yesno",
        yes_text="PASS",
        no_text="FAIL"
    )


def set_angle(pwm, angle):
    """
    Converts a servo angle to an SG90-style duty cycle.

    Approximate mapping:
    0 degrees   -> about 2% duty
    90 degrees  -> about 7% duty
    180 degrees -> about 12% duty
    """
    duty_cycle = 2 + (angle / 18)

    pwm.ChangeDutyCycle(duty_cycle)
    time.sleep(ANGLE_HOLD_TIME)

    # Stop sending the pulse briefly to reduce servo jitter.
    pwm.ChangeDutyCycle(0)
    time.sleep(PAUSE_BETWEEN_ANGLES)


def run_single_pwm_test(test_info):
    gpio_pin = test_info["gpio"]
    pwm = None

    switch_ready = ask_switch_confirmation(test_info)

    if not switch_ready:
        return {
            "name": test_info["name"],
            "status": "SKIP",
            "details": (
                f"{test_info['name']} was skipped because the switch setup "
                "was not confirmed by the operator."
            )
        }

    try:
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(gpio_pin, GPIO.OUT)

        pwm = GPIO.PWM(gpio_pin, SERVO_FREQUENCY)
        pwm.start(0)

        set_angle(pwm, 0)
        set_angle(pwm, 90)
        set_angle(pwm, 180)
        set_angle(pwm, 90)

        observed_pass = ask_observation_confirmation(test_info)

        if observed_pass:
            return {
                "name": test_info["name"],
                "status": "PASS",
                "details": (
                    f"{test_info['name']} passed. "
                    f"Servo signal was tested on GPIO{gpio_pin}, and the operator "
                    "confirmed correct movement."
                )
            }

        return {
            "name": test_info["name"],
            "status": "FAIL",
            "details": (
                f"{test_info['name']} failed. "
                f"Servo signal was tested on GPIO{gpio_pin}, but the operator "
                "reported incorrect or missing servo movement."
            )
        }

    except Exception as e:
        return {
            "name": test_info["name"],
            "status": "ERROR",
            "details": (
                f"{test_info['name']} caused an error while testing GPIO{gpio_pin}: {e}"
            )
        }

    finally:
        try:
            if pwm is not None:
                pwm.stop()
        except Exception:
            pass

        try:
            GPIO.cleanup(gpio_pin)
        except Exception:
            pass


def run_restore_command(command):
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
    Restores shared GPIO pins after the servo test.

    This is important because GPIO.cleanup() can leave pins as normal inputs,
    which can break UART, SPI, and I2C tests that run after the servo test.
    """
    if not shutil.which("raspi-gpio"):
        return "raspi-gpio not found; shared pin modes were not restored."

    # I2C pins
    run_restore_command(["raspi-gpio", "set", "2", "a0", "pu"])
    run_restore_command(["raspi-gpio", "set", "3", "a0", "pu"])

    # UART TXD1/RXD1 pins
    run_restore_command(["raspi-gpio", "set", "14", "a5", "pn"])
    run_restore_command(["raspi-gpio", "set", "15", "a5", "pu"])

    # SPI0 chip selects as outputs high
    run_restore_command(["raspi-gpio", "set", "7", "op", "dh", "pu"])
    run_restore_command(["raspi-gpio", "set", "8", "op", "dh", "pu"])

    # SPI0 data/clock pins
    run_restore_command(["raspi-gpio", "set", "9", "a0", "pd"])
    run_restore_command(["raspi-gpio", "set", "10", "a0", "pd"])
    run_restore_command(["raspi-gpio", "set", "11", "a0", "pd"])

    # SPI1 chip selects as outputs high
    run_restore_command(["raspi-gpio", "set", "16", "op", "dh", "pd"])
    run_restore_command(["raspi-gpio", "set", "17", "op", "dh", "pd"])
    run_restore_command(["raspi-gpio", "set", "18", "op", "dh", "pd"])

    # SPI1 data/clock pins
    run_restore_command(["raspi-gpio", "set", "19", "a4", "pd"])
    run_restore_command(["raspi-gpio", "set", "20", "a4", "pd"])
    run_restore_command(["raspi-gpio", "set", "21", "a4", "pd"])

    # SPI monitor pins
    for pin in [5, 6, 12, 13, 22, 23, 24]:
        run_restore_command(["raspi-gpio", "set", str(pin), "ip", "pd"])

    return (
        "I2C, UART, and SPI shared pin modes were restored after the servo test "
        "using the working pre-test configuration."
    )


def combine_results(results, restore_message):
    pass_count = 0
    fail_count = 0
    error_count = 0
    skip_count = 0
    detail_lines = []

    for result in results:
        status = result.get("status", "ERROR")

        if status == "PASS":
            pass_count += 1
        elif status == "FAIL":
            fail_count += 1
        elif status == "ERROR":
            error_count += 1
        elif status == "SKIP":
            skip_count += 1

        detail_lines.append(
            f"{result.get('name', 'PWM Test')}: "
            f"{status} - {result.get('details', '')}"
        )

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
        f"Servo PWM test completed. "
        f"PASS={pass_count}, FAIL={fail_count}, ERROR={error_count}, SKIP={skip_count}.\n"
        + "\n".join(detail_lines)
        + f"\n{restore_message}"
    )

    return {
        "name": TEST_NAME,
        "status": overall_status,
        "details": details
    }


def main():
    results = []

    try:
        for test_info in PWM_TESTS:
            result = run_single_pwm_test(test_info)
            results.append(result)

    finally:
        try:
            GPIO.cleanup()
        except Exception:
            pass

        time.sleep(CLEANUP_DELAY)
        restore_message = restore_shared_pin_modes()

    final_result = combine_results(results, restore_message)
    print(json.dumps(final_result))


if __name__ == "__main__":
    main()
