import json
import time
from pathlib import Path

import RPi.GPIO as GPIO


UP_LED = 17
MID_LED = 27
DOWN_LED = 22

LATEST_RESULT_FILE = Path("output/latest_result.json")

LIGHT_DURATION_SECONDS = 5


TARGET_TO_ZONE = {
    "top": "UP",
    "center": "MID",
    "bottom": "DOWN",

    # 현재 하드웨어는 LED 3개만 사용하므로
    # left/right는 임시로 center와 같은 MID에 매핑합니다.
    # 추후 LED가 늘어나면 여기만 확장하면 됩니다.
    "left": "MID",
    "right": "MID",
}


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


def load_latest_result(result_path=LATEST_RESULT_FILE):
    result_path = Path(result_path)

    if not result_path.exists():
        raise FileNotFoundError(
            f"Latest result file not found: {result_path}"
        )

    with result_path.open("r", encoding="utf-8") as result_file:
        return json.load(result_file)


def normalize_target(target):
    if target is None:
        return "miss"

    return str(target).strip().lower()


def target_to_zone(target):
    normalized_target = normalize_target(target)

    return TARGET_TO_ZONE.get(
        normalized_target,
        "MISS"
    )


def light_zone(zone):
    clear_leds()

    if zone == "UP":
        GPIO.output(UP_LED, GPIO.HIGH)

    elif zone == "MID":
        GPIO.output(MID_LED, GPIO.HIGH)

    elif zone == "DOWN":
        GPIO.output(DOWN_LED, GPIO.HIGH)

    elif zone == "MISS":
        clear_leds()

    else:
        clear_leds()


def process_hit(result_path=LATEST_RESULT_FILE):
    result = load_latest_result(result_path)

    target = normalize_target(
        result.get("target")
    )

    zone = target_to_zone(target)

    hit = result.get("hit")
    endpoint_x_px = result.get("endpoint_x_px")
    endpoint_y_px = result.get("endpoint_y_px")
    distance_px = result.get("distance_px")
    video_name = result.get("video_name")

    light_zone(zone)

    print("\n====================")
    print("LED RESULT")
    print("====================")
    print(f"Video       : {video_name}")
    print(f"Target      : {target}")
    print(f"Zone        : {zone}")
    print(f"Hit         : {hit}")
    print(f"Endpoint X  : {endpoint_x_px}")
    print(f"Endpoint Y  : {endpoint_y_px}")
    print(f"Distance px : {distance_px}")

    return zone


def cleanup():
    clear_leds()
    GPIO.cleanup()


def run_once(
    result_path=LATEST_RESULT_FILE,
    duration=LIGHT_DURATION_SECONDS,
    cleanup_after=True,
):
    try:
        setup_gpio()

        zone = process_hit(result_path)

        time.sleep(duration)

        return zone

    finally:
        if cleanup_after:
            cleanup()
        else:
            clear_leds()


def main():
    run_once()


if __name__ == "__main__":
    main()