from pathlib import Path
import json
import subprocess
import sys

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request


app = FastAPI()

templates = Jinja2Templates(
    directory="app/templates"
)

app.mount(
    "/static",
    StaticFiles(directory="app/static"),
    name="static"
)

app.mount(
    "/output",
    StaticFiles(directory="output"),
    name="output"
)


@app.get("/", response_class=HTMLResponse)
def home(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="index.html"
    )


def read_latest_result():

    result_path = Path("output") / "latest_result.json"

    if not result_path.exists():

        raise FileNotFoundError(
            "No latest_result.json found. Root main.py must create output/latest_result.json."
        )

    with result_path.open("r", encoding="utf-8") as result_file:

        result = json.load(result_file)

    required_keys = {
        "success",
        "hit_x",
        "hit_y",
        "video_name",
        "trajectory_image",
        "board_image",
        "preview_video",
    }

    missing_keys = required_keys - set(result.keys())

    if missing_keys:

        raise ValueError(
            f"latest_result.json is missing keys: {sorted(missing_keys)}"
        )

    return result


@app.post("/analyze")
def analyze_video():

    try:

        print("\n====================")
        print("RUN ROOT MAIN")
        print("====================")

        result = subprocess.run(
            [
                sys.executable,
                "main.py",
                "--adb-capture"
            ],
            capture_output=True,
            text=True
        )

        if result.stdout:

            print(result.stdout)

        if result.stderr:

            print(result.stderr)

        if result.returncode != 0:

            return {
                "success": False,
                "error": result.stderr or "Root main.py failed."
            }

        latest_result = read_latest_result()

        print("\n====================")
        print("WEB RESPONSE")
        print("====================")
        print(f"Video: {latest_result['video_name']}")
        print(f"Hit: ({latest_result['hit_x']}, {latest_result['hit_y']})")

        return latest_result

    except Exception as exc:

        print(f"[WEB ERROR] {exc}")

        return {
            "success": False,
            "error": str(exc)
        }