import json
import sys
import time
import smbus2

# SSD1306 Configuration Constants
I2C_BUS = 1
OLED_ADDRESS = 0x3C  # Standard default address for 0.96" OLEDs

def send_command(bus, cmd):
    bus.write_byte_data(OLED_ADDRESS, 0x00, cmd)

def send_data(bus, data_bytes):
    # Break into chunks to prevent I2C buffer overflows
    for i in range(0, len(data_bytes), 16):
        bus.write_i2c_block_data(OLED_ADDRESS, 0x40, data_bytes[i:i+16])

def init_display(bus):
    """Basic initialization sequence for a 128x64 SSD1306 OLED"""
    commands = [
        0xAE,  # Display OFF
        0xD5, 0x80,  # Set Display Clock Divide Ratio
        0xA8, 0x3F,  # Set Multiplex Ratio (64 rows)
        0xD3, 0x00,  # Set Display Offset
        0x40,  # Set Start Line
        0x8D, 0x14,  # Enable Charge Pump (Crucial for 3.3V power)
        0x20, 0x00,  # Set Memory Addressing Mode to Horizontal
        0xA1,  # Segment Re-map (Flip Horizontal)
        0xC8,  # COM Output Scan Direction (Flip Vertical)
        0xDA, 0x12,  # Set COM Pins Hardware Configuration
        0x81, 0xCF,  # Set Contrast Control
        0xD9, 0xF1,  # Set Pre-charge Period
        0xDB, 0x40,  # Set VCOMH Deselect Level
        0xA4,  # Entire Display ON (Resume from RAM)
        0xA6,  # Normal Display Mode (Not Inverted)
        0xAF   # Display ON
    ]
    for cmd in commands:
        send_command(bus, cmd)

def draw_test_pattern(bus):
    """Draws a boundary border box and clear checkerboard markers"""
    # 128 columns x 64 rows = 8 pages of 128 bytes each
    buffer = [0x00] * 1024
    
    # Page 0 (Top line) and Page 7 (Bottom line) solid borders
    for x in range(128):
        buffer[x] |= 0x01          # Top pixel row
        buffer[896 + x] |= 0x80    # Bottom pixel row
        
    # Vertical side borders across all pages
    for page in range(8):
        buffer[page * 128] |= 0xFF        # Leftmost pixel column
        buffer[(page * 128) + 127] |= 0xFF  # Rightmost pixel column
        
    # Draw a distinct visual hatch mark pattern in the center box
    for page in range(2, 6):
        for col in range(32, 96, 4):
            buffer[(page * 128) + col] |= 0x3C

    send_data(bus, buffer)

def main():
    try:
        # 1. Verify the I2C physical connection dynamically
        try:
            bus = smbus2.SMBus(I2C_BUS)
        except Exception:
            print(json.dumps({
                "status": "ERROR", 
                "details": f"Failed to open I2C Bus {I2C_BUS}. Is I2C interface interface blocked or disabled?"
            }))
            sys.exit(1)

        # 2. Check if device ACK responds on the expected hardware target address
        try:
            # Write a dummy quick command byte to verify address presence
            bus.write_quick(OLED_ADDRESS)
        except OSError:
            print(json.dumps({
                "status": "FAIL", 
                "details": f"No I2C device acknowledged at address 0x{OLED_ADDRESS:02X}. Check your SDA/SCL lines."
            }))
            sys.exit(0)

        # 3. Initialize hardware & flash patterns
        init_display(bus)
        draw_test_pattern(bus)
        bus.close()

        # 4. Pass bus verification stage
        print(json.dumps({
            "status": "PASS", 
            "details": f"Successfully communicated with SSD1306 OLED at address 0x{OLED_ADDRESS:02X} over I2C. Visual pattern rendered."
        }))
        sys.exit(0)

    except Exception as e:
        print(json.dumps({
            "status": "ERROR", 
            "details": f"Unhandled runtime error during script execution: {str(e)}"
        }))
        sys.exit(1)

if __name__ == "__main__":
    main()
