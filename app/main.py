from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request

from src.adb_capture import AdbCaptureError, capture_video
from src.extract_landmarks import extract_pose
from src.analyze_throw import analyze
from src.trajectory import predict
from src.simulate_board import read_hit_position, render_board
from src.render_analysis_preview import render_preview


app = FastAPI()

templates = Jinja2Templates(directory="app/templates")

app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.mount("/output", StaticFiles(directory="output"), name="output")


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html"
    )


@app.post("/analyze")
async def analyze_video():
    output_dir = Path("output")
    output_dir.mkdir(parents=True, exist_ok=True)

    board_w = 16
    board_h = 16

    try:
        print("\n====================")
        print("ADB Capture Start")
        print("====================")

        video_path = capture_video("adb_config.json")

        run_name = video_path.stem

        landmarks_csv = output_dir / f"{run_name}_landmarks.csv"
        pose_preview = output_dir / f"{run_name}_pose_preview.mp4"
        analysis_csv = output_dir / f"{run_name}_analysis.csv"
        trajectory_csv = output_dir / f"{run_name}_trajectory.csv"
        trajectory_png = output_dir / f"{run_name}_trajectory.png"
        board_png = output_dir / f"{run_name}_board.png"
        analysis_preview = output_dir / f"{run_name}_analysis_preview.mp4"

        print("\n====================")
        print("Virtual Dart Motion")
        print("====================")
        print(f"Captured video: {video_path}")

        print("\n1. Pose extraction")
        extract_pose(
            video_path=video_path,
            output_csv=landmarks_csv,
            preview_path=pose_preview,
            flip_horizontal=False,
        )

        print("\n2. Throw analysis")
        analyze(
            csv_path=landmarks_csv,
            hand="right",
            motion_point="auto",
            output_csv=analysis_csv,
            window=5,
            lookback=10,
            direction_window=4,
            min_visibility=0.5,
            board_w=board_w,
            board_h=board_h,
            sensitivity=0.35,
        )

        print("\n3. Trajectory prediction")
        predict(
            analysis_csv=analysis_csv,
            hand="right",
            output_csv=trajectory_csv,
            plot_path=trajectory_png,
            gravity=0.25,
            duration=0.8,
            steps=30,
            velocity_scale=0.8,
            board_w=board_w,
            board_h=board_h,
            board_scale=20.0,
            board_distance=2.0,
            speed_to_mps=2.5,
            min_duration=0.25,
            max_duration=1.2,
        )

        print("\n4. Board render")
        hit_x, hit_y = read_hit_position(trajectory_csv)

        render_board(
            hit_x=hit_x,
            hit_y=hit_y,
            board_w=board_w,
            board_h=board_h,
            output_png=board_png,
        )

        print("\n5. Analysis preview render")
        render_preview(
            video_path=video_path,
            analysis_csv=analysis_csv,
            trajectory_csv=trajectory_csv,
            output_video=analysis_preview,
            hand="right",
            flip_horizontal=False,
        )

        print("\n====================")
        print("Analysis completed")
        print("====================")
        print(f"Hit position: ({hit_x}, {hit_y})")

        return {
            "success": True,
            "hit_x": hit_x,
            "hit_y": hit_y,
            "video_name": video_path.name,
            "trajectory_image": f"/output/{run_name}_trajectory.png",
            "board_image": f"/output/{run_name}_board.png",
            "preview_video": f"/output/{run_name}_analysis_preview.mp4",
        }

    except AdbCaptureError as exc:
        print(f"[ADB ERROR] {exc}")
        return {
            "success": False,
            "error": f"ADB ERROR: {exc}",
        }

    except Exception as exc:
        print(f"[ANALYSIS ERROR] {exc}")
        return {
            "success": False,
            "error": f"ANALYSIS ERROR: {exc}",
        }