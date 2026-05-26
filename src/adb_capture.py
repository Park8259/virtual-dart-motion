import json
import shutil
import subprocess
import time
from datetime import datetime
from pathlib import Path


DEFAULT_CONFIG = {
    "shutter_x": 540,
    "shutter_y": 2150,
    "record_seconds": 2.0,
    "save_wait_seconds": 3.0,
    "remote_camera_dir": "/sdcard/DCIM/Camera",
    "local_video_dir": "videos",
    "beep_enabled": True,
}


class AdbCaptureError(RuntimeError):
    pass


def load_config(config_path):
    config = DEFAULT_CONFIG.copy()
    path = Path(config_path)
    if path.exists():
        with path.open("r", encoding="utf-8") as config_file:
            loaded = json.load(config_file)
        if not isinstance(loaded, dict):
            raise AdbCaptureError(f"ADB config must be a JSON object: {path}")
        config.update(loaded)
    return config


def run_adb(args, check=True):
    try:
        result = subprocess.run(
            ["adb", *args],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise AdbCaptureError(
            "adb command not found. Install android-tools-adb on the Raspberry Pi."
        ) from exc

    if check and result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or "unknown adb error"
        raise AdbCaptureError(message)

    return result


def get_single_authorized_device():
    result = run_adb(["devices"])
    devices = []
    unauthorized = []

    for line in result.stdout.splitlines()[1:]:
        line = line.strip()
        if not line:
            continue

        parts = line.split()
        if len(parts) < 2:
            continue

        serial, state = parts[0], parts[1]
        if state == "device":
            devices.append(serial)
        elif state == "unauthorized":
            unauthorized.append(serial)

    if unauthorized:
        raise AdbCaptureError(
            "ADB device is unauthorized. Approve USB debugging on the Galaxy screen."
        )

    if not devices:
        raise AdbCaptureError(
            "No authorized ADB device found. Check USB cable, USB debugging, and adb installation."
        )

    if len(devices) > 1:
        raise AdbCaptureError("More than one authorized ADB device found. Connect only one device.")

    return devices[0]


def play_beep():
    if not shutil.which("play"):
        print("[경고] sox/play 명령을 찾지 못해 알림음을 건너뜁니다.")
        return

    subprocess.run(
        ["play", "-n", "synth", "0.2", "sin", "800"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )


def tap_shutter(serial, x, y):
    run_adb(["-s", serial, "shell", "input", "tap", str(x), str(y)])


def find_latest_mp4(serial, remote_camera_dir):
    command = f"ls -t {remote_camera_dir.rstrip('/')}/*.mp4 2>/dev/null | head -n 1"
    result = run_adb(["-s", serial, "shell", command])
    target_file = result.stdout.strip().splitlines()[0] if result.stdout.strip() else ""

    if not target_file or ".mp4" not in target_file.lower():
        raise AdbCaptureError(f"No mp4 file found in {remote_camera_dir}.")

    return target_file


def pull_video(serial, remote_file, local_video_dir):
    local_dir = Path(local_video_dir)
    local_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    local_path = local_dir / f"capture_{timestamp}.mp4"
    run_adb(["-s", serial, "pull", remote_file, str(local_path)])

    if not local_path.exists():
        raise AdbCaptureError(f"adb pull finished, but local file was not created: {local_path}")

    return local_path


def capture_video(config_path="adb_config.json"):
    config = load_config(config_path)
    serial = get_single_authorized_device()

    shutter_x = int(config["shutter_x"])
    shutter_y = int(config["shutter_y"])
    record_seconds = float(config["record_seconds"])
    save_wait_seconds = float(config["save_wait_seconds"])
    remote_camera_dir = str(config["remote_camera_dir"])
    local_video_dir = str(config["local_video_dir"])
    beep_enabled = bool(config["beep_enabled"])

    print(f"[ADB] 연결된 장치: {serial}")
    print("[ADB] 2초 뒤 촬영을 시작합니다. 갤럭시 카메라가 프로 동영상 모드인지 확인하세요.")
    time.sleep(2)

    if beep_enabled:
        play_beep()

    print("[ADB] 녹화 시작")
    tap_shutter(serial, shutter_x, shutter_y)

    print(f"[ADB] {record_seconds:.1f}초 동안 녹화 중")
    time.sleep(record_seconds)

    print("[ADB] 녹화 종료")
    tap_shutter(serial, shutter_x, shutter_y)

    if beep_enabled:
        play_beep()

    print(f"[ADB] 파일 저장 대기: {save_wait_seconds:.1f}초")
    time.sleep(save_wait_seconds)

    print("[ADB] 최신 mp4 검색")
    remote_file = find_latest_mp4(serial, remote_camera_dir)
    print(f"[ADB] 타깃 파일: {remote_file}")

    print("[ADB] 라즈베리파이로 파일 전송")
    local_path = pull_video(serial, remote_file, local_video_dir)
    print(f"[ADB] 저장 완료: {local_path}")

    return local_path
