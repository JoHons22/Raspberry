import RPi.GPIO as GPIO
import time
import json

# GPIO pin connected to servo signal wire
SERVO_PIN = 18

# Create result ahead of time
result = {
    "name": "Servo Test",
    "status": "ERROR",
    "details": "Test did not complete."
}

pwm = None


def set_angle(angle):
    """
    Convert angle from 0-180 degrees to duty cycle.
    Typical servo range: about 2.5% to 12.5%.
    """
    duty = 2 + (angle / 18)
    pwm.ChangeDutyCycle(duty)
    time.sleep(0.5)
    pwm.ChangeDutyCycle(0)  # Reduce servo jitter


try:
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(SERVO_PIN, GPIO.OUT)

    # Create PWM object at 50 Hz
    pwm = GPIO.PWM(SERVO_PIN, 50)
    pwm.start(0)

    print("0 degrees")
    set_angle(0)
    time.sleep(1)

    print("90 degrees")
    set_angle(90)
    time.sleep(1)

    print("180 degrees")
    set_angle(180)
    time.sleep(1)

    result = {
        "name": "Servo Test",
        "status": "PASS",
        "details": "Servo moved to 0, 90, and 180 degrees successfully."
    }

except Exception as e:
    result = {
        "name": "Servo Test",
        "status": "ERROR",
        "details": str(e)
    }

finally:
    if pwm is not None:
        pwm.stop()

    GPIO.cleanup()

    print(json.dumps(result))
