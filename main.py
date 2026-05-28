import argparse
import sys
from pathlib import Path

import cv2

from src.adb_capture import AdbCaptureError, capture_video
from src.extract_landmarks import extract_pose
from src.analyze_throw import analyze
from src.object_tracker import track_object, correct_release_from_object_track, COLOR_RANGES
from src.trajectory import predict
from src.simulate_board import read_hit_position, render_board
from src.render_analysis_preview import render_preview


def find_latest_video(videos_dir):
    videos = []
    for pattern in ["*.mp4", "*.mov", "*.MOV", "*.MP4"]:
        videos.extend(videos_dir.glob(pattern))

    if not videos:
        raise FileNotFoundError(f"No video file found in {videos_dir}")

    return max(videos, key=lambda path: path.stat().st_mtime)


def build_run_name(video_path, flip_horizontal):
    run_name = video_path.stem
    if flip_horizontal:
        run_name = f"{run_name}_flipped"
    return run_name


def normalized_screen_endpoint_x(video_path, endpoint_margin_px):
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise FileNotFoundError(f"Cannot open video: {video_path}")

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    cap.release()

    if width <= 0:
        return None

    margin = max(0, min(endpoint_margin_px, width - 1))
    return (width - margin) / width


def parse_args():
    parser = argparse.ArgumentParser(description="Run virtual dart motion analysis.")
    parser.add_argument(
        "input_video",
        nargs="?",
        type=Path,
        help="Input video path. If omitted, the latest video in videos/ is used.",
    )
    parser.add_argument(
        "--video",
        type=Path,
        help="Input video path. Kept for compatibility with the ADB workflow.",
    )
    parser.add_argument(
        "--adb-capture",
        action="store_true",
        help="Record a new video over ADB, pull it into videos/, then analyze it.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("adb_config.json"),
        help="ADB capture config path.",
    )
    parser.add_argument(
        "--hand",
        choices=["right", "left"],
        default="right",
        help="Throwing hand to analyze.",
    )
    parser.add_argument(
        "--motion-point",
        choices=["auto", "wrist", "thumb_tip", "index_tip", "middle_tip"],
        default="auto",
        help="Landmark used for release timing and trajectory start.",
    )
    parser.add_argument(
        "--start-mode",
        choices=["recent", "video-start"],
        default="video-start",
        help="How to choose the throw start frame.",
    )
    parser.add_argument(
        "--flip-horizontal",
        action="store_true",
        help="Flip mirrored/selfie videos before analysis.",
    )
    parser.add_argument(
        "--board-distance",
        type=float,
        default=2.0,
        help="Fixed distance from thrower to virtual board in meters.",
    )
    parser.add_argument(
        "--physics-mode",
        choices=["simple", "dart"],
        default="dart",
        help="Trajectory model to use.",
    )
    parser.add_argument(
        "--dart-speed-mps",
        type=float,
        default=8.0,
        help="Initial dart speed in meters per second for dart physics mode.",
    )
    parser.add_argument(
        "--direction-window",
        type=int,
        default=20,
        help="Recent frames before release used to estimate throw direction.",
    )
    parser.add_argument(
        "--release-offset-frames",
        type=int,
        default=0,
        help="Move the detected release frame this many frames earlier.",
    )
    parser.add_argument(
        "--trajectory-y-offset-px",
        type=int,
        default=0,
        help="Move the rendered trajectory upward by this many pixels in the preview video.",
    )
    parser.add_argument(
        "--endpoint-margin-px",
        type=int,
        default=10,
        help="Fix the rendered 2m endpoint this many pixels before the right edge.",
    )
    parser.add_argument(
        "--track-object",
        action="store_true",
        help="Track a colored projectile after release and use it to correct trajectory.",
    )
    parser.add_argument(
        "--object-method",
        choices=["color", "flow"],
        default="flow",
        help="Projectile tracking method when --track-object is enabled.",
    )
    parser.add_argument(
        "--object-color",
        choices=sorted(COLOR_RANGES),
        default="green",
        help="Projectile color to track when --track-object is enabled.",
    )
    parser.add_argument(
        "--object-min-area",
        type=float,
        default=20,
        help="Minimum contour area for projectile tracking.",
    )
    parser.add_argument(
        "--object-max-frames",
        type=int,
        default=40,
        help="Maximum frames to scan after release for projectile tracking.",
    )
    parser.add_argument(
        "--object-min-motion-px",
        type=float,
        default=4.0,
        help="Minimum optical-flow motion in pixels.",
    )
    parser.add_argument(
        "--object-release-lead-frames",
        type=int,
        default=3,
        help="Move release marker this many frames before first tracked object frame.",
    )
    return parser.parse_args()


def run_analysis(
    video_path,
    hand,
    motion_point,
    start_mode,
    flip_horizontal,
    board_distance,
    physics_mode,
    dart_speed_mps,
    direction_window,
    release_offset_frames,
    trajectory_y_offset_px,
    endpoint_margin_px,
    track_object_enabled,
    object_method,
    object_color,
    object_min_area,
    object_max_frames,
    object_min_motion_px,
    object_release_lead_frames,
):
    run_name = build_run_name(video_path, flip_horizontal)

    output_dir = Path("output") / run_name
    landmarks_csv = output_dir / f"{run_name}_landmarks.csv"
    pose_preview = output_dir / f"{run_name}_pose_preview.mp4"
    analysis_csv = output_dir / f"{run_name}_analysis.csv"
    trajectory_csv = output_dir / f"{run_name}_trajectory.csv"
    object_track_csv = output_dir / f"{run_name}_object_track.csv"
    trajectory_png = output_dir / f"{run_name}_trajectory.png"
    board_png = output_dir / f"{run_name}_board.png"
    analysis_preview = output_dir / f"{run_name}_analysis_preview.mp4"

    board_w = 16
    board_h = 16

    print("실행 설정")
    print(f"Video: {video_path}")
    print(f"Hand: {hand}")
    print(f"Motion point: {motion_point}")
    print(f"Start mode: {start_mode}")
    print(f"Flip horizontal: {flip_horizontal}")
    print(f"Board distance: {board_distance}m")
    print(f"Physics mode: {physics_mode}")
    print(f"Dart speed: {dart_speed_mps}m/s")
    print(f"Direction window: {direction_window}")
    print(f"Release offset frames: {release_offset_frames}")
    print(f"Trajectory Y offset: {trajectory_y_offset_px}px")
    print(f"Endpoint margin: {endpoint_margin_px}px")
    print(f"Track object: {track_object_enabled}")
    print(f"Object method: {object_method}")
    print(f"Output folder: {output_dir}")

    print("\n1. 관절 및 손가락 좌표 추출 중...")
    extract_pose(
        video_path=video_path,
        output_csv=landmarks_csv,
        preview_path=pose_preview,
        flip_horizontal=flip_horizontal,
    )

    print("\n2. 투척 동작 분석 중...")
    analyze(
        csv_path=landmarks_csv,
        hand=hand,
        motion_point=motion_point,
        start_mode=start_mode,
        output_csv=analysis_csv,
        window=5,
        lookback=10,
        direction_window=direction_window,
        min_visibility=0.5,
        board_w=board_w,
        board_h=board_h,
        sensitivity=0.35,
        release_offset_frames=release_offset_frames,
    )

    if track_object_enabled:
        print("\n2-1. 릴리즈 이후 물체 추적 중...")
        track_object(
            video_path=video_path,
            analysis_csv=analysis_csv,
            output_csv=object_track_csv,
            method=object_method,
            color=object_color,
            min_area=object_min_area,
            max_frames_after_release=object_max_frames,
            flip_horizontal=flip_horizontal,
            min_motion_px=object_min_motion_px,
        )
        correction = correct_release_from_object_track(
            analysis_csv=analysis_csv,
            object_track_csv=object_track_csv,
            lead_frames=object_release_lead_frames,
        )
        if correction:
            print(
                "Release corrected from object track: "
                f"{correction['corrected_release_frame']} "
                f"(first object frame: {correction['first_object_frame']})"
            )
    else:
        object_track_csv = None

    print("\n3. 가상 다트 궤적 예측 중...")
    screen_endpoint_x = normalized_screen_endpoint_x(video_path, endpoint_margin_px)
    predict(
        analysis_csv=analysis_csv,
        hand=hand,
        output_csv=trajectory_csv,
        plot_path=trajectory_png,
        gravity=0.25,
        duration=0.8,
        steps=30,
        velocity_scale=0.8,
        board_w=board_w,
        board_h=board_h,
        board_scale=20.0,
        board_distance=board_distance,
        speed_to_mps=2.5,
        min_duration=0.25,
        max_duration=1.2,
        physics_mode=physics_mode,
        dart_speed_mps=dart_speed_mps,
        board_width_m=0.6,
        board_height_m=0.6,
        gravity_mps2=9.81,
        max_horizontal_angle_deg=15.0,
        max_vertical_angle_deg=15.0,
        object_track_csv=object_track_csv,
        min_object_points=3,
        screen_endpoint_x=screen_endpoint_x,
    )

    print("\n4. 가상 보드 결과 이미지 생성 중...")
    hit_x, hit_y = read_hit_position(trajectory_csv)
    render_board(
        hit_x=hit_x,
        hit_y=hit_y,
        board_w=board_w,
        board_h=board_h,
        output_png=board_png,
    )

    print("\n5. 분석 미리보기 영상 생성 중...")
    render_preview(
        video_path=video_path,
        analysis_csv=analysis_csv,
        trajectory_csv=trajectory_csv,
        output_video=analysis_preview,
        hand=hand,
        flip_horizontal=flip_horizontal,
        trajectory_y_offset_px=trajectory_y_offset_px,
    )

    print("\n전체 실행 완료")
    print(f"명중 위치: ({hit_x}, {hit_y})")
    print(f"결과 폴더: {output_dir}")
    print(f"좌표 CSV: {landmarks_csv}")
    print(f"분석 CSV: {analysis_csv}")
    print(f"궤적 이미지: {trajectory_png}")
    print(f"분석 영상: {analysis_preview}")


def main():
    args = parse_args()

    try:
        if args.adb_capture:
            video_path = capture_video(args.config)
        else:
            video_path = args.video or args.input_video or find_latest_video(Path("videos"))

        run_analysis(
            video_path=video_path,
            hand=args.hand,
            motion_point=args.motion_point,
            start_mode=args.start_mode,
            flip_horizontal=args.flip_horizontal,
            board_distance=args.board_distance,
            physics_mode=args.physics_mode,
            dart_speed_mps=args.dart_speed_mps,
            direction_window=args.direction_window,
            release_offset_frames=args.release_offset_frames,
            trajectory_y_offset_px=args.trajectory_y_offset_px,
            endpoint_margin_px=args.endpoint_margin_px,
            track_object_enabled=args.track_object,
            object_method=args.object_method,
            object_color=args.object_color,
            object_min_area=args.object_min_area,
            object_max_frames=args.object_max_frames,
            object_min_motion_px=args.object_min_motion_px,
            object_release_lead_frames=args.object_release_lead_frames,
        )
    except AdbCaptureError as exc:
        print(f"[ADB 오류] {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
