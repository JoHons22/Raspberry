import sys
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
        0xAE, 0xD5, 0x80, 0xA8, 0x3F, 0xD3, 0x00, 0x40,
        0x8D, 0x14, 0x20, 0x00, 0xA1, 0xC8, 0xda, 0x12,
        0x81, 0xFF, 0xD9, 0xF1, 0xDB, 0x40, 0xA4, 0xA6, 0xAF
    ]
    for cmd in commands:
        send_command(bus, cmd)

def main():
    if len(sys.argv) < 2:
        sys.exit(1)
        
    mode = sys.argv[1].lower()

    try:
        bus = smbus2.SMBus(I2C_BUS)
        bus.write_quick(OLED_ADDRESS)
        init_display(bus)

        if mode == "solid":
            send_data(bus, [0xFF] * 1024)
        elif mode == "checker1":
            send_data(bus, [0xAA] * 1024)
        elif mode == "checker2":
            send_data(bus, [0x55] * 1024)
        elif mode == "off":
            send_data(bus, [0x00] * 1024)
            
        bus.close()
    except Exception:
        sys.exit(1)

if __name__ == "__main__":
    main()
