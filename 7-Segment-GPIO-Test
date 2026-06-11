import RPi.GPIO as GPIO
import time

# GPIO pins connected to segments a-g
segments = {
    'a': 17,
    'b': 18,
    'c': 27,
    'd': 22,
    'e': 23,
    'f': 24,
    'g': 25
}

GPIO.setmode(GPIO.BCM)

for pin in segments.values():
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.LOW)

try:
    while True:
        for name, pin in segments.items():
            print(f"Testing segment {name}")

            # Turn all segments off
            for p in segments.values():
                GPIO.output(p, GPIO.LOW)

            # Turn on one segment
            GPIO.output(pin, GPIO.HIGH)

            time.sleep(1)

except KeyboardInterrupt:
    pass

finally:
    GPIO.cleanup()
