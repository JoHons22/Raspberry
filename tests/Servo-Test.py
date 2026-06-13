import RPi.GPIO as GPIO
import time

# GPIO pin connected to servo signal wire
SERVO_PIN = 18

GPIO.setmode(GPIO.BCM)
GPIO.setup(SERVO_PIN, GPIO.OUT)

# Create PWM object at 50 Hz (standard servo frequency)
pwm = GPIO.PWM(SERVO_PIN, 50)
pwm.start(0)

def set_angle(angle):
    """
    Convert angle (0-180) to duty cycle.
    Typical servo range: 2.5% to 12.5%
    """
    duty = 2 + (angle / 18)
    pwm.ChangeDutyCycle(duty)
    time.sleep(0.5)
    pwm.ChangeDutyCycle(0)  # Reduce servo jitter

try:
    while True:
        print("0 degrees")
        set_angle(0)
        time.sleep(1)

        print("90 degrees")
        set_angle(90)
        time.sleep(1)

        print("180 degrees")
        set_angle(180)
        time.sleep(1)

        time.sleep(1)

except KeyboardInterrupt:
    pass

finally:
    pwm.stop()
    GPIO.cleanup()
