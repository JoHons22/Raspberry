import RPi.GPIO as GPIO
import time

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

        print("\n===== STARTING GPIO TEST CYCLE =====")
        time.sleep(0.5)

        for segment, pin in segments.items():

            for p in segments.values():
                GPIO.output(p, GPIO.LOW)

            GPIO.output(pin, GPIO.HIGH)

            print(f"Testing Segment {segment.upper()} on GPIO {pin}")

            time.sleep(1)

        print("===== END OF GPIO TEST CYCLE =====\n")

        time.sleep(2)

except KeyboardInterrupt:
    pass

finally:
    GPIO.cleanup()
