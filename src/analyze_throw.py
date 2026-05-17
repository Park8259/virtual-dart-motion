import argparse
import math
from pathlib import Path

import pandas as pd


def moving_average(values, window):
    return values.rolling(window=window, center=True, min_periods=1).mean()


def calculate_speed(df, hand):
    wrist_x = f"{hand}_wrist_x"
    wrist_y = f"{hand}_wrist_y"

    df["dx"] = df[wrist_x].diff()
    df["dy"] = df[wrist_y].diff()
    df["dt"] = df["time_sec"].diff()
    df["speed"] = ((df["dx"] ** 2 + df["dy"] ** 2) ** 0.5) / df["dt"]
    return df


def calculate_elbow_angle(row, hand):
    shoulder = (row[f"{hand}_shoulder_x"], row[f"{hand}_shoulder_y"])
    elbow = (row[f"{hand}_elbow_x"], row[f"{hand}_elbow_y"])
    wrist = (row[f"{hand}_wrist_x"], row[f"{hand}_wrist_y"])

    if any(pd.isna(v) for point in [shoulder, elbow, wrist] for v in point):
        return math.nan

    upper = (shoulder[0] - elbow[0], shoulder[1] - elbow[1])
    lower = (wrist[0] - elbow[0], wrist[1] - elbow[1])

    upper_len = math.hypot(*upper)
    lower_len = math.hypot(*lower)
    if upper_len == 0 or lower_len == 0:
        return math.nan

    dot = upper[0] * lower[0] + upper[1] * lower[1]
    cos_theta = max(-1.0, min(1.0, dot / (upper_len * lower_len)))
    return math.degrees(math.acos(cos_theta))


def find_release_candidate(df, speed_threshold_ratio=0.45):
    max_speed = df["smooth_speed"].max()
    if pd.isna(max_speed) or max_speed <= 0:
        raise ValueError("Cannot find release candidate because speed values are empty.")

    threshold = max_speed * speed_threshold_ratio
    candidates = df[df["smooth_speed"] >= threshold].copy()
    candidates = candidates[candidates["pose_detected"] == True]

    if candidates.empty:
        release_idx = df["smooth_speed"].idxmax()
        return release_idx, threshold

    release_idx = candidates["smooth_speed"].idxmax()
    return release_idx, threshold


def clamp(value, low, high):
    return max(low, min(high, value))


def calculate_hit_position(direction_x, direction_y, speed, board_w, board_h, sensitivity):
    center_x = (board_w - 1) / 2
    center_y = (board_h - 1) / 2

    hit_x = center_x + direction_x * speed * sensitivity
    hit_y = center_y + direction_y * speed * sensitivity

    return (
        int(round(clamp(hit_x, 0, board_w - 1))),
        int(round(clamp(hit_y, 0, board_h - 1))),
    )


def analyze(csv_path, hand, output_csv, window, lookback, board_w, board_h, sensitivity):
    df = pd.read_csv(csv_path)
    hand = hand.lower()
    if hand not in {"right", "left"}:
        raise ValueError("--hand must be either right or left")

    required = [
        "frame_index",
        "time_sec",
        "pose_detected",
        f"{hand}_shoulder_x",
        f"{hand}_shoulder_y",
        f"{hand}_elbow_x",
        f"{hand}_elbow_y",
        f"{hand}_wrist_x",
        f"{hand}_wrist_y",
    ]
    missing = [column for column in required if column not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    numeric_columns = [column for column in required if column not in {"pose_detected"}]
    for column in numeric_columns:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    df = calculate_speed(df, hand)
    df["smooth_speed"] = moving_average(df["speed"].fillna(0), window)
    df["elbow_angle"] = df.apply(lambda row: calculate_elbow_angle(row, hand), axis=1)

    release_idx, threshold = find_release_candidate(df)
    release_row = df.loc[release_idx]

    start_pos = max(0, df.index.get_loc(release_idx) - lookback)
    start_idx = df.index[start_pos]
    start_row = df.loc[start_idx]

    dx = release_row[f"{hand}_wrist_x"] - start_row[f"{hand}_wrist_x"]
    dy = release_row[f"{hand}_wrist_y"] - start_row[f"{hand}_wrist_y"]
    dt = release_row["time_sec"] - start_row["time_sec"]

    if dt <= 0 or pd.isna(dt):
        avg_speed = 0.0
    else:
        avg_speed = math.hypot(dx, dy) / dt

    distance = math.hypot(dx, dy)
    if distance == 0 or pd.isna(distance):
        direction_x, direction_y = 0.0, 0.0
    else:
        direction_x, direction_y = dx / distance, dy / distance

    angle_deg = math.degrees(math.atan2(direction_y, direction_x))
    hit_x, hit_y = calculate_hit_position(
        direction_x,
        direction_y,
        avg_speed,
        board_w,
        board_h,
        sensitivity,
    )

    df["is_release_candidate"] = False
    df.loc[release_idx, "is_release_candidate"] = True
    df["is_start_frame"] = False
    df.loc[start_idx, "is_start_frame"] = True

    if output_csv:
        output_csv.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_csv, index=False)

    print("Throw analysis result")
    print(f"Input CSV: {csv_path}")
    print(f"Hand: {hand}")
    print(f"Start frame: {int(start_row['frame_index'])} ({start_row['time_sec']:.4f}s)")
    print(f"Release candidate frame: {int(release_row['frame_index'])} ({release_row['time_sec']:.4f}s)")
    print(f"Release speed threshold: {threshold:.4f}")
    print(f"Release smooth speed: {release_row['smooth_speed']:.4f}")
    print(f"Average throw speed: {avg_speed:.4f}")
    print(f"Direction vector: ({direction_x:.4f}, {direction_y:.4f})")
    print(f"Direction angle: {angle_deg:.2f} degrees")
    print(f"Elbow angle at release: {release_row['elbow_angle']:.2f} degrees")
    print(f"Board hit position: ({hit_x}, {hit_y}) on {board_w}x{board_h}")
    if output_csv:
        print(f"Analysis CSV saved: {output_csv}")


def main():
    parser = argparse.ArgumentParser(description="Analyze throw motion from MediaPipe landmark CSV.")
    parser.add_argument(
        "csv",
        type=Path,
        help="Input CSV created by extract_landmarks.py",
    )
    parser.add_argument(
        "--hand",
        choices=["right", "left"],
        default="right",
        help="Throwing hand to analyze",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("output/throw_analysis.csv"),
        help="Output CSV with speed and release markers",
    )
    parser.add_argument(
        "--window",
        type=int,
        default=5,
        help="Moving average window for speed smoothing",
    )
    parser.add_argument(
        "--lookback",
        type=int,
        default=10,
        help="Frames before release candidate used as start frame",
    )
    parser.add_argument("--board-w", type=int, default=16, help="Virtual board width")
    parser.add_argument("--board-h", type=int, default=16, help="Virtual board height")
    parser.add_argument(
        "--sensitivity",
        type=float,
        default=0.35,
        help="Scale factor from throw speed to board position",
    )
    args = parser.parse_args()

    analyze(
        args.csv,
        args.hand,
        args.out,
        args.window,
        args.lookback,
        args.board_w,
        args.board_h,
        args.sensitivity,
    )


if __name__ == "__main__":
    main()
