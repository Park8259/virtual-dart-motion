import argparse
import csv
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("MPLCONFIGDIR", str(PROJECT_ROOT / ".mplconfig"))

import cv2
import mediapipe as mp


POSE_POINTS = {
    "right_shoulder": mp.solutions.pose.PoseLandmark.RIGHT_SHOULDER,
    "right_elbow": mp.solutions.pose.PoseLandmark.RIGHT_ELBOW,
    "right_wrist": mp.solutions.pose.PoseLandmark.RIGHT_WRIST,
    "left_shoulder": mp.solutions.pose.PoseLandmark.LEFT_SHOULDER,
    "left_elbow": mp.solutions.pose.PoseLandmark.LEFT_ELBOW,
    "left_wrist": mp.solutions.pose.PoseLandmark.LEFT_WRIST,
}


def landmark_row(frame_index, time_sec, landmarks):
    row = {
        "frame_index": frame_index,
        "time_sec": time_sec,
        "pose_detected": landmarks is not None,
    }

    for name, landmark_id in POSE_POINTS.items():
        if landmarks is None:
            row[f"{name}_x"] = ""
            row[f"{name}_y"] = ""
            row[f"{name}_z"] = ""
            row[f"{name}_visibility"] = ""
            continue

        point = landmarks[landmark_id.value]
        row[f"{name}_x"] = point.x
        row[f"{name}_y"] = point.y
        row[f"{name}_z"] = point.z
        row[f"{name}_visibility"] = point.visibility

    return row


def extract_pose(video_path, output_csv, preview_path=None):
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise FileNotFoundError(f"Cannot open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)

    fieldnames = [
        "frame_index",
        "time_sec",
        "pose_detected",
    ]
    for name in POSE_POINTS:
        fieldnames.extend(
            [
                f"{name}_x",
                f"{name}_y",
                f"{name}_z",
                f"{name}_visibility",
            ]
        )

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    preview_writer = None

    if preview_path:
        preview_path.parent.mkdir(parents=True, exist_ok=True)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        preview_writer = cv2.VideoWriter(str(preview_path), fourcc, fps, (width, height))

    mp_pose = mp.solutions.pose
    drawing = mp.solutions.drawing_utils

    with mp_pose.Pose(
        static_image_mode=False,
        model_complexity=1,
        enable_segmentation=False,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
    ) as pose, output_csv.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()

        frame_index = 0
        detected_count = 0

        while True:
            ok, frame = cap.read()
            if not ok:
                break

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            result = pose.process(rgb)

            landmarks = None
            if result.pose_landmarks:
                landmarks = result.pose_landmarks.landmark
                detected_count += 1

            time_sec = frame_index / fps
            writer.writerow(landmark_row(frame_index, time_sec, landmarks))

            if preview_writer:
                annotated = frame.copy()
                if result.pose_landmarks:
                    drawing.draw_landmarks(
                        annotated,
                        result.pose_landmarks,
                        mp_pose.POSE_CONNECTIONS,
                    )
                preview_writer.write(annotated)

            frame_index += 1

    cap.release()
    if preview_writer:
        preview_writer.release()

    print(f"Video: {video_path}")
    print(f"FPS: {fps:.2f}")
    print(f"Frames: {frame_index}/{total_frames}")
    print(f"Pose detected: {detected_count} frames")
    print(f"CSV saved: {output_csv}")
    if preview_path:
        print(f"Preview saved: {preview_path}")


def main():
    parser = argparse.ArgumentParser(description="Extract MediaPipe pose landmarks from a video.")
    parser.add_argument("video", type=Path, help="Input video path")
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("output/landmarks.csv"),
        help="Output CSV path",
    )
    parser.add_argument(
        "--preview",
        type=Path,
        help="Optional annotated preview video path",
    )
    args = parser.parse_args()

    extract_pose(args.video, args.out, args.preview)


if __name__ == "__main__":
    main()
