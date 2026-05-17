import argparse
from pathlib import Path

import cv2
import pandas as pd


def read_markers(analysis_csv):
    df = pd.read_csv(analysis_csv)
    start_rows = df[df["is_start_frame"] == True]
    release_rows = df[df["is_release_candidate"] == True]

    if start_rows.empty:
        raise ValueError("No start frame found in analysis CSV.")
    if release_rows.empty:
        raise ValueError("No release candidate frame found in analysis CSV.")

    return df, start_rows.iloc[0], release_rows.iloc[0]


def draw_label(frame, text, origin, color):
    x, y = origin
    cv2.putText(
        frame,
        text,
        (x + 2, y + 2),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (0, 0, 0),
        3,
        cv2.LINE_AA,
    )
    cv2.putText(
        frame,
        text,
        (x, y),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        color,
        2,
        cv2.LINE_AA,
    )


def draw_wrist_marker(frame, row, hand, label, color):
    height, width = frame.shape[:2]
    x = row[f"{hand}_wrist_x"]
    y = row[f"{hand}_wrist_y"]

    if pd.isna(x) or pd.isna(y):
        return

    px = int(x * width)
    py = int(y * height)

    cv2.circle(frame, (px, py), 12, color, -1)
    cv2.circle(frame, (px, py), 16, (255, 255, 255), 2)
    draw_label(frame, label, (px + 18, py - 12), color)


def render_preview(video_path, analysis_csv, output_video, hand, flip_horizontal=False):
    df, start_row, release_row = read_markers(analysis_csv)
    frame_lookup = {int(row.frame_index): row for row in df.itertuples(index=False)}

    start_frame = int(start_row["frame_index"])
    release_frame = int(release_row["frame_index"])

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise FileNotFoundError(f"Cannot open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")

    output_video.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(str(output_video), fourcc, fps, (width, height))

    frame_index = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break

        if flip_horizontal:
            frame = cv2.flip(frame, 1)

        draw_label(frame, f"Frame: {frame_index}", (24, 36), (255, 255, 255))

        if frame_index in frame_lookup:
            row = frame_lookup[frame_index]
            wrist_x = getattr(row, f"{hand}_wrist_x")
            wrist_y = getattr(row, f"{hand}_wrist_y")
            if not pd.isna(wrist_x) and not pd.isna(wrist_y):
                px = int(wrist_x * width)
                py = int(wrist_y * height)
                cv2.circle(frame, (px, py), 7, (0, 255, 255), -1)

        if frame_index == start_frame:
            draw_wrist_marker(frame, start_row, hand, "START", (128, 128, 128))
            draw_label(frame, "START FRAME", (24, 72), (200, 200, 200))

        if frame_index == release_frame:
            draw_wrist_marker(frame, release_row, hand, "RELEASE", (0, 0, 255))
            draw_label(frame, "RELEASE CANDIDATE", (24, 72), (0, 0, 255))

        if start_frame <= frame_index <= release_frame:
            draw_label(frame, "THROW WINDOW", (24, height - 30), (0, 255, 255))

        writer.write(frame)
        frame_index += 1

    cap.release()
    writer.release()

    print(f"Video: {video_path}")
    print(f"Flip horizontal: {flip_horizontal}")
    print(f"Analysis CSV: {analysis_csv}")
    print(f"Start frame: {start_frame}")
    print(f"Release candidate frame: {release_frame}")
    print(f"Preview saved: {output_video}")


def main():
    parser = argparse.ArgumentParser(
        description="Render a video preview with start and release candidate markers."
    )
    parser.add_argument("video", type=Path, help="Input video path")
    parser.add_argument("analysis_csv", type=Path, help="CSV created by analyze_throw.py")
    parser.add_argument(
        "--hand",
        choices=["right", "left"],
        default="right",
        help="Throwing hand to visualize",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("output/analysis_preview.mp4"),
        help="Output annotated video path",
    )
    parser.add_argument(
        "--flip-horizontal",
        action="store_true",
        help="Flip mirrored/selfie videos before drawing markers",
    )
    args = parser.parse_args()

    render_preview(args.video, args.analysis_csv, args.out, args.hand, args.flip_horizontal)


if __name__ == "__main__":
    main()
