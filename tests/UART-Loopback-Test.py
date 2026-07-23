import serial
import time
import json
import subprocess
import shutil

TEST_NAME = "UART Loopback Test"

UART_PORT = "/dev/serial0"
BAUD_RATE = 9600
TX_PIN = 14
RX_PIN = 15


def run_pin_command(command):
    """
    Runs a pin setup command.
    Errors are ignored so the UART test can still try to run normally.
    """
    try:
        completed = subprocess.run(
            command,
            text=True,
            capture_output=True,
            timeout=3
        )
        return completed.returncode == 0, completed.stderr.strip()
    except Exception as e:
        return False, str(e)


def configure_uart_pins():
    """
    Configure GPIO14 and GPIO15 for UART0.

    GPIO14 = TXD0, physical pin 8
    GPIO15 = RXD0, physical pin 10

    This helps restore UART mode if a previous test used these pins as normal GPIO.
    """

    if not shutil.which("raspi-gpio"):
        return "raspi-gpio not found; UART pins were not manually reconfigured."

    tx_ok, tx_error = run_pin_command(["raspi-gpio", "set", str(TX_PIN), "a0"])
    rx_ok, rx_error = run_pin_command(["raspi-gpio", "set", str(RX_PIN), "a0"])

    if tx_ok and rx_ok:
        return "GPIO14 and GPIO15 were configured for UART alternate function."

    return (
        "Attempted to configure GPIO14/GPIO15 for UART, but one or more commands failed. "
        f"TX error: {tx_error}. RX error: {rx_error}."
    )


def main():
    uart = None

    result = {
        "name": TEST_NAME,
        "status": "ERROR",
        "details": "Test did not complete."
    }

    try:
        print()
        print("================================")
        print("UART LOOPBACK TEST")
        print("================================")
        print("Required connection:")
        print("GPIO14 TXD, physical pin 8 -> GPIO15 RXD, physical pin 10")
        print()

        pin_setup_details = configure_uart_pins()
        print(pin_setup_details)

        uart = serial.Serial(
            port=UART_PORT,
            baudrate=BAUD_RATE,
            timeout=1
        )

        message = "Hello UART Loopback"

        uart.reset_input_buffer()
        uart.reset_output_buffer()

        print(f"TX -> {message}")
        uart.write(message.encode())
        uart.flush()

        time.sleep(0.1)

        received = uart.read(len(message)).decode(errors="ignore")

        print(f"RX <- {received}")

        if received == "":
            print("STATUS: FAIL - NO DATA RECEIVED")
            result = {
                "name": TEST_NAME,
                "status": "FAIL",
                "details": (
                    f"{pin_setup_details} No message was received. "
                    f"Sent '{message}', but RX returned nothing. "
                    "Check switch position, TX-to-RX routing, UART enable settings, "
                    "and make sure the serial console is disabled."
                )
            }

        elif received == message:
            print("STATUS: PASS")
            result = {
                "name": TEST_NAME,
                "status": "PASS",
                "details": (
                    f"{pin_setup_details} Sent '{message}' and received matching response."
                )
            }

        else:
            print("STATUS: FAIL - DATA MISMATCH")
            result = {
                "name": TEST_NAME,
                "status": "FAIL",
                "details": (
                    f"{pin_setup_details} Message mismatch. "
                    f"Sent '{message}', but received '{received}'."
                )
            }

        print("================================")

    except Exception as e:
        result = {
            "name": TEST_NAME,
            "status": "ERROR",
            "details": str(e)
        }

    finally:
        if uart is not None and uart.is_open:
            uart.close()

        # The GUI reads the final printed line as JSON.
        print(json.dumps(result))


if __name__ == "__main__":
    main()
