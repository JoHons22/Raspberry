import serial
import time

uart = serial.Serial(
    port='/dev/serial0',
    baudrate=9600,
    timeout=1
)

test_num = 1

try:
    while True:

        message = f"Hello UART #{test_num}"

        print("\n================================")
        print("UART LOOPBACK TEST")
        print("================================")

        # Transmit
        print(f"TX -> {message}")
        uart.write(message.encode())

        time.sleep(0.1)

        # Receive
        received = uart.read(len(message)).decode()

        print(f"RX <- {received}")

        # Verify
        if received == message:
            print("STATUS: PASS")
        else:
            print("STATUS: FAIL")

        print("================================")

        test_num += 1
        time.sleep(2)

except KeyboardInterrupt:
    print("\nStopping UART test...")

finally:
    uart.close()
