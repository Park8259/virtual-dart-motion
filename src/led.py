import json
import time
from pathlib import Path

import RPi.GPIO as GPIO


UP_LED = 17
MID_LED = 27
DOWN_LED = 22

PX_OUTPUT_FILE = Path("output/pxoutput.json")


UP_RANGE = (750, 850)
MID_RANGE = (550, 650)
DOWN_RANGE = (350, 450)


def setup_gpio():

    GPIO.setwarnings(False)

    GPIO.setmode(GPIO.BCM)

    GPIO.setup(UP_LED, GPIO.OUT)
    GPIO.setup(MID_LED, GPIO.OUT)
    GPIO.setup(DOWN_LED, GPIO.OUT)

    clear_leds()


def clear_leds():

    GPIO.output(UP_LED, GPIO.LOW)
    GPIO.output(MID_LED, GPIO.LOW)
    GPIO.output(DOWN_LED, GPIO.LOW)


def load_px_result():

    if not PX_OUTPUT_FILE.exists():

        raise FileNotFoundError(
            f"PX output file not found: {PX_OUTPUT_FILE}"
        )

    with open(
        PX_OUTPUT_FILE,
        "r",
        encoding="utf-8"
    ) as f:

        return json.load(f)


def classify_zone(hit_y_px):

    if UP_RANGE[0] <= hit_y_px <= UP_RANGE[1]:

        return "UP"

    if MID_RANGE[0] <= hit_y_px <= MID_RANGE[1]:

        return "MID"

    if DOWN_RANGE[0] <= hit_y_px <= DOWN_RANGE[1]:

        return "DOWN"

    return "MISS"


def light_zone(zone):

    clear_leds()

    if zone == "UP":

        GPIO.output(
            UP_LED,
            GPIO.HIGH
        )

    elif zone == "MID":

        GPIO.output(
            MID_LED,
            GPIO.HIGH
        )

    elif zone == "DOWN":

        GPIO.output(
            DOWN_LED,
            GPIO.HIGH
        )


def process_hit():

    result = load_px_result()

    hit_x_px = result.get(
        "hit_x_px",
        None
    )

    hit_y_px = result.get(
        "hit_y_px",
        None
    )

    if hit_y_px is None:

        raise ValueError(
            "hit_y_px not found"
        )

    zone = classify_zone(hit_y_px)

    light_zone(zone)

    print("\n====================")
    print("LED RESULT")
    print("====================")
    print(f"Hit X: {hit_x_px}")
    print(f"Hit Y: {hit_y_px}")
    print(f"Zone : {zone}")

    return zone


def cleanup():

    clear_leds()
    GPIO.cleanup()


def main():

    try:

        setup_gpio()

        process_hit()

        time.sleep(5)

    finally:

        cleanup()


if __name__ == "__main__":

    main()