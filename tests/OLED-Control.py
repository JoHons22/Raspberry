import sys
import time
import subprocess
import shutil
import smbus2

I2C_BUS = 1
OLED_ADDRESS = 0x3C

I2C_SDA_PIN = 2
I2C_SCL_PIN = 3


def run_pin_command(command):
    """
    Runs a raspi-gpio command.
    Returns True if successful.
    """
    try:
        completed = subprocess.run(
            command,
            text=True,
            capture_output=True,
            timeout=3
        )

        if completed.returncode != 0:
            print(completed.stderr.strip(), file=sys.stderr)

        return completed.returncode == 0

    except Exception as e:
        print(str(e), file=sys.stderr)
        return False


def restore_i2c_pins():
    """
    Restores GPIO2 and GPIO3 to I2C mode.

    GPIO2 = SDA1
    GPIO3 = SCL1

    This is needed if the GPIO LED test previously used GPIO2/GPIO3
    as normal output pins.
    """

    if not shutil.which("raspi-gpio"):
        print("raspi-gpio not found. Could not force GPIO2/GPIO3 to I2C mode.", file=sys.stderr)
        return False

    sda_ok = run_pin_command(["raspi-gpio", "set", str(I2C_SDA_PIN), "a0", "pu"])
    scl_ok = run_pin_command(["raspi-gpio", "set", str(I2C_SCL_PIN), "a0", "pu"])

    time.sleep(0.1)

    return sda_ok and scl_ok


def send_command(bus, cmd):
    bus.write_byte_data(OLED_ADDRESS, 0x00, cmd)


def send_data(bus, data_bytes):
    for i in range(0, len(data_bytes), 16):
        bus.write_i2c_block_data(
            OLED_ADDRESS,
            0x40,
            data_bytes[i:i + 16]
        )


def init_display(bus):
    commands = [
        0xAE,        # Display off
        0xD5, 0x80,  # Set display clock
        0xA8, 0x3F,  # Multiplex ratio
        0xD3, 0x00,  # Display offset
        0x40,        # Start line
        0x8D, 0x14,  # Charge pump
        0x20, 0x00,  # Horizontal addressing mode
        0xA1,        # Segment remap
        0xC8,        # COM scan direction
        0xDA, 0x12,  # COM pins
        0x81, 0xFF,  # Contrast
        0xD9, 0xF1,  # Pre-charge
        0xDB, 0x40,  # VCOM detect
        0xA4,        # Resume RAM display
        0xA6,        # Normal display
        0xAF         # Display on
    ]

    for cmd in commands:
        send_command(bus, cmd)


def clear_display(bus):
    send_data(bus, [0x00] * 1024)


def write_pattern(bus, mode):
    if mode == "solid":
        send_data(bus, [0xFF] * 1024)

    elif mode == "checker1":
        send_data(bus, [0xAA] * 1024)

    elif mode == "checker2":
        send_data(bus, [0x55] * 1024)

    elif mode == "off":
        send_data(bus, [0x00] * 1024)

    else:
        raise ValueError(f"Unknown OLED mode: {mode}")


def main():
    if len(sys.argv) < 2:
        print("Missing OLED mode argument.", file=sys.stderr)
        sys.exit(1)

    mode = sys.argv[1].lower()

    bus = None

    try:
        restore_i2c_pins()

        bus = smbus2.SMBus(I2C_BUS)

        # Check that the OLED responds on the I2C bus
        bus.write_quick(OLED_ADDRESS)

        init_display(bus)
        write_pattern(bus, mode)

        print(f"OLED mode '{mode}' sent successfully.")
        sys.exit(0)

    except Exception as e:
        print(f"OLED control error: {e}", file=sys.stderr)
        sys.exit(1)

    finally:
        if bus is not None:
            try:
                bus.close()
            except Exception:
                pass


if __name__ == "__main__":
    main()
