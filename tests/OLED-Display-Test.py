import json
import sys
import time
import smbus2

I2C_BUS = 1
OLED_ADDRESS = 0x3C

def send_command(bus, cmd):
    bus.write_byte_data(OLED_ADDRESS, 0x00, cmd)

def send_data(bus, data_bytes):
    for i in range(0, len(data_bytes), 16):
        bus.write_i2c_block_data(OLED_ADDRESS, 0x40, data_bytes[i:i+16])

def init_display(bus):
    commands = [
        0xAE,        # Display OFF
        0xD5, 0x80,  # Set Display Clock Divide Ratio
        0xA8, 0x3F,  # Set Multiplex Ratio (64 rows)
        0xD3, 0x00,  # Set Display Offset
        0x40,        # Set Start Line
        0x8D, 0x14,  # Enable Charge Pump
        0x20, 0x00,  # Horizontal Memory Addressing Mode
        0xA1,        # Segment Re-map (Flip Horizontal)
        0xC8,        # COM Output Scan Direction (Flip Vertical)
        0xDA, 0x12,  # Set COM Pins Hardware Configuration
        0x81, 0xFF,  # Set Contrast Control to Maximum Brightness
        0xD9, 0xF1,  # Set Pre-charge Period
        0xDB, 0x40,  # Set VCOMH Deselect Level
        0xA4,        # Entire Display ON (Resume from RAM)
        0xA6,        # Normal Display Mode
        0xAF         # Display ON
    ]
    for cmd in commands:
        send_command(bus, cmd)

def main():
    try:
        try:
            bus = smbus2.SMBus(I2C_BUS)
        except Exception:
            print(json.dumps({"status": "ERROR", "details": f"Failed to open I2C Bus {I2C_BUS}."}))
            sys.exit(1)

        try:
            bus.write_quick(OLED_ADDRESS)
        except OSError:
            print(json.dumps({"status": "FAIL", "details": f"No device found at 0x{OLED_ADDRESS:02X}."}))
            sys.exit(0)

        init_display(bus)

        # ---- STAGE 1: Full Pixel Solid Illumination ----
        # 1024 bytes filled with 0xFF turns on every single pixel (128x64)
        full_on_buffer = [0xFF] * 1024
        send_data(bus, full_on_buffer)
        time.sleep(2.0)

        # ---- STAGE 2: Checkerboard Pattern A ----
        # Alternating bits (0xAA = 10101010)
        checker_a_buffer = [0xAA] * 1024
        send_data(bus, checker_a_buffer)
        time.sleep(1.5)

        # ---- STAGE 3: Checkerboard Pattern B ----
        # Flipped alternating bits (0x55 = 01010101)
        checker_b_buffer = [0x55] * 1024
        send_data(bus, checker_b_buffer)
        time.sleep(1.5)

        # ---- STAGE 4: Clear Screen / All Off ----
        full_off_buffer = [0x00] * 1024
        send_data(bus, full_off_buffer)
        
        bus.close()

        print(json.dumps({
            "status": "PASS", 
            "details": f"OLED verified at 0x{OLED_ADDRESS:02X}. Full pixel diagnostic cycle complete."
        }))
        sys.exit(0)

    except Exception as e:
        print(json.dumps({"status": "ERROR", "details": str(e)}))
        sys.exit(1)

if __name__ == "__main__":
    main()
