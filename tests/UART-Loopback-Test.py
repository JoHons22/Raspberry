import serial
import time
import json

uart = None

result = {
    "name": "UART Loopback Test",
    "status": "ERROR",
    "details": "Test did not complete."
}

try:
    uart = serial.Serial(
        port="/dev/serial0",
        baudrate=9600,
        timeout=1
    )

    message = "Hello UART Loopback"

    print("\n================================")
    print("UART LOOPBACK TEST")
    print("================================")

    # Clear old data from the UART buffer
    uart.reset_input_buffer()
    uart.reset_output_buffer()

    # Transmit
    print(f"TX -> {message}")
    uart.write(message.encode())
    uart.flush()

    time.sleep(0.1)

    # Receive
    received = uart.read(len(message)).decode(errors="ignore")

    print(f"RX <- {received}")

    # Verify
    if received == "":
        print("STATUS: FAIL - NO DATA RECEIVED")
        result = {
            "name": "UART Loopback Test",
            "status": "FAIL",
            "details": f"No message was received. Sent '{message}', but RX returned nothing. Check TX-to-RX wiring, UART enable settings, and serial port."
        }
    
    elif received == message:
        print("STATUS: PASS")
        result = {
            "name": "UART Loopback Test",
            "status": "PASS",
            "details": f"Sent '{message}' and received matching response."
        }
    
    else:
        print("STATUS: FAIL - DATA MISMATCH")
        result = {
            "name": "UART Loopback Test",
            "status": "FAIL",
            "details": f"Message mismatch. Sent '{message}', but received '{received}'."
        }

    print("================================")

except Exception as e:
    result = {
        "name": "UART Loopback Test",
        "status": "ERROR",
        "details": str(e)
    }

finally:
    if uart is not None and uart.is_open:
        uart.close()

    print(json.dumps(result))
