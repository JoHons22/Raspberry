import sys
import time
import subprocess
import shutil
import smbus2

I2C_BUS = 1
OLED_ADDRESS = 0x3C

I2C_SDA_PIN = 2
I2C_SCL_PIN = 3

WIDTH = 128
HEIGHT = 64
PAGES = HEIGHT // 8


FONT = {
    " ": [0x00, 0x00, 0x00, 0x00, 0x00],
    "-": [0x08, 0x08, 0x08, 0x08, 0x08],
    "0": [0x3E, 0x51, 0x49, 0x45, 0x3E],
    "1": [0x00, 0x42, 0x7F, 0x40, 0x00],
    "2": [0x42, 0x61, 0x51, 0x49, 0x46],
    "3": [0x21, 0x41, 0x45, 0x4B, 0x31],
    "4": [0x18, 0x14, 0x12, 0x7F, 0x10],
    "5": [0x27, 0x45, 0x45, 0x45, 0x39],
    "6": [0x3C, 0x4A, 0x49, 0x49, 0x30],
    "7": [0x01, 0x71, 0x09, 0x05, 0x03],
    "8": [0x36, 0x49, 0x49, 0x49, 0x36],
    "9": [0x06, 0x49, 0x49, 0x29, 0x1E],
    "A": [0x7E, 0x11, 0x11, 0x11, 0x7E],
    "B": [0x7F, 0x49, 0x49, 0x49, 0x36],
    "C": [0x3E, 0x41, 0x41, 0x41, 0x22],
    "D": [0x7F, 0x41, 0x41, 0x22, 0x1C],
    "E": [0x7F, 0x49, 0x49, 0x49, 0x41],
    "F": [0x7F, 0x09, 0x09, 0x09, 0x01],
    "G": [0x3E, 0x41, 0x49, 0x49, 0x7A],
    "H": [0x7F, 0x08, 0x08, 0x08, 0x7F],
    "I": [0x00, 0x41, 0x7F, 0x41, 0x00],
    "J": [0x20, 0x40, 0x41, 0x3F, 0x01],
    "K": [0x7F, 0x08, 0x14, 0x22, 0x41],
    "L": [0x7F, 0x40, 0x40, 0x40, 0x40],
    "M": [0x7F, 0x02, 0x04, 0x02, 0x7F],
    "N": [0x7F, 0x04, 0x08, 0x10, 0x7F],
    "O": [0x3E, 0x41, 0x41, 0x41, 0x3E],
    "P": [0x7F, 0x09, 0x09, 0x09, 0x06],
    "Q": [0x3E, 0x41, 0x51, 0x21, 0x5E],
    "R": [0x7F, 0x09, 0x19, 0x29, 0x46],
    "S": [0x46, 0x49, 0x49, 0x49, 0x31],
    "T": [0x01, 0x01, 0x7F, 0x01, 0x01],
    "U": [0x3F, 0x40, 0x40, 0x40, 0x3F],
    "V": [0x1F, 0x20, 0x40, 0x20, 0x1F],
    "W": [0x7F, 0x20, 0x18, 0x20, 0x7F],
    "X": [0x63, 0x14, 0x08, 0x14, 0x63],
    "Y": [0x07, 0x08, 0x70, 0x08, 0x07],
    "Z": [0x61, 0x51, 0x49, 0x45, 0x43],
}


def run_pin_command(command):
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
    """

    if not shutil.which("raspi-gpio"):
        print(
            "raspi-gpio not found. Could not force GPIO2/GPIO3 to I2C mode.",
            file=sys.stderr
        )
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
        0xAE,
        0xD5, 0x80,
        0xA8, 0x3F,
        0xD3, 0x00,
        0x40,
        0x8D, 0x14,
        0x20, 0x00,
        0xA1,
        0xC8,
        0xDA, 0x12,
        0x81, 0xFF,
        0xD9, 0xF1,
        0xDB, 0x40,
        0xA4,
        0xA6,
        0xAF
    ]

    for cmd in commands:
        send_command(bus, cmd)


def set_address_window(bus):
    send_command(bus, 0x21)
    send_command(bus, 0x00)
    send_command(bus, WIDTH - 1)

    send_command(bus, 0x22)
    send_command(bus, 0x00)
    send_command(bus, PAGES - 1)


def create_blank_frame():
    return [0x00] * (WIDTH * PAGES)


def set_pixel(frame, x, y, on=True):
    if x < 0 or x >= WIDTH or y < 0 or y >= HEIGHT:
        return

    page = y // 8
    bit = y % 8
    index = page * WIDTH + x

    if on:
        frame[index] |= (1 << bit)
    else:
        frame[index] &= ~(1 << bit)


def fill_rect(frame, x, y, w, h, on=True):
    for row in range(y, y + h):
        for col in range(x, x + w):
            set_pixel(frame, col, row, on)


def draw_rect(frame, x, y, w, h, on=True):
    for col in range(x, x + w):
        set_pixel(frame, col, y, on)
        set_pixel(frame, col, y + h - 1, on)

    for row in range(y, y + h):
        set_pixel(frame, x, row, on)
        set_pixel(frame, x + w - 1, row, on)


def draw_char(frame, x, y, char, on=True):
    char = char.upper()

    if char not in FONT:
        char = " "

    columns = FONT[char]

    for col_index, column_data in enumerate(columns):
        for row in range(7):
            pixel_on = (column_data >> row) & 0x01

            if pixel_on:
                set_pixel(frame, x + col_index, y + row, on)


def draw_text(frame, x, y, text, on=True):
    cursor_x = x

    for char in text.upper():
        draw_char(frame, cursor_x, y, char, on)
        cursor_x += 6


def center_text(frame, y, text, on=True):
    text_width = len(text) * 6 - 1
    x = max(0, (WIDTH - text_width) // 2)
    draw_text(frame, x, y, text, on)


def write_frame(bus, frame):
    set_address_window(bus)
    send_data(bus, frame)


def make_start_screen():
    frame = create_blank_frame()

    draw_rect(frame, 0, 0, WIDTH, HEIGHT, True)
    center_text(frame, 6, "I2C TEST", True)
    center_text(frame, 22, "START", True)
    center_text(frame, 38, "OLED FOUND", True)

    return frame


def make_address_screen():
    frame = create_blank_frame()

    draw_rect(frame, 0, 0, WIDTH, HEIGHT, True)
    center_text(frame, 6, "I2C ADDRESS", True)
    center_text(frame, 22, "ADDR 3C", True)
    center_text(frame, 38, "DEVICE OK", True)

    return frame


def make_write_screen():
    frame = create_blank_frame()

    draw_rect(frame, 0, 0, WIDTH, HEIGHT, True)
    center_text(frame, 6, "I2C WRITE", True)
    center_text(frame, 22, "DATA SENT", True)
    center_text(frame, 38, "COMM OK", True)

    # Small bar pattern to show that bulk pixel data was written
    fill_rect(frame, 16, 52, 20, 6, True)
    fill_rect(frame, 42, 52, 20, 6, True)
    fill_rect(frame, 68, 52, 20, 6, True)
    fill_rect(frame, 94, 52, 20, 6, True)

    return frame


def make_off_screen():
    frame = create_blank_frame()

    # Show a final message first. This is not a dead-pixel check;
    # it confirms the Pi can clear/write the OLED over I2C.
    center_text(frame, 8, "I2C TEST", True)
    center_text(frame, 24, "CLEAR", True)
    center_text(frame, 40, "DONE", True)

    return frame


def make_frame_for_mode(mode):
    if mode == "start":
        return make_start_screen()

    if mode == "address":
        return make_address_screen()

    if mode == "write":
        return make_write_screen()

    if mode == "off":
        return make_off_screen()

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

        # If this fails, the Pi is not communicating with the OLED address.
        bus.write_quick(OLED_ADDRESS)

        init_display(bus)

        frame = make_frame_for_mode(mode)
        write_frame(bus, frame)

        print(f"OLED I2C mode '{mode}' sent successfully.")
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
