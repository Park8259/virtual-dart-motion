from pathlib import Path

import pandas as pd

from src.analyze_throw import MOTION_POINTS, clamp, point_prefix, resolve_motion_point


def _nearest_frame_row(df, frame_index):
    if df.empty:
        return None

    distances = (df["frame_index"] - frame_index).abs()
    return df.loc[distances.idxmin()]


def _front_window(df, release_frame, window):
    start_frame = max(0, release_frame - window)
    recent = df[(df["frame_index"] >= start_frame) & (df["frame_index"] <= release_frame)]
    recent = recent[recent["front_tracking_ok"] == True]
    return recent


def apply_front_camera_direction(
    side_analysis_csv,
    front_landmarks_csv,
    hand,
    motion_point,
    output_csv=None,
    direction_window=20,
    horizontal_gain=1.0,
):
    side_df = pd.read_csv(side_analysis_csv)
    front_df = pd.read_csv(front_landmarks_csv)
    hand = hand.lower()

    release_rows = side_df[side_df["is_release_candidate"] == True]
    if release_rows.empty:
        raise ValueError("No release candidate frame found in side analysis CSV.")

    release_row = release_rows.iloc[0]
    release_frame = int(release_row["frame_index"])

    if motion_point == "auto":
        motion_point = release_row.get("throw_motion_point", "auto")
    if motion_point not in MOTION_POINTS:
        motion_point = resolve_motion_point(front_df, hand, "auto")

    point = point_prefix(hand, motion_point)
    required = ["frame_index", f"{point}_x", f"{point}_y"]
    missing = [column for column in required if column not in front_df.columns]
    if missing:
        raise ValueError(f"Missing required front camera columns: {missing}")

    for column in required:
        front_df[column] = pd.to_numeric(front_df[column], errors="coerce")

    front_df["front_tracking_ok"] = (
        front_df[f"{point}_x"].notna() & front_df[f"{point}_y"].notna()
    )
    recent = _front_window(front_df, release_frame, direction_window)
    if len(recent) < 2:
        raise ValueError("Not enough front camera tracking points near release frame.")

    start_row = recent.iloc[0]
    front_release_row = _nearest_frame_row(recent, release_frame)
    if front_release_row is None:
        raise ValueError("Cannot find matching front camera release frame.")

    dx = front_release_row[f"{point}_x"] - start_row[f"{point}_x"]
    dy = front_release_row[f"{point}_y"] - start_row[f"{point}_y"]
    distance = (dx**2 + dy**2) ** 0.5
    if pd.isna(distance) or distance == 0:
        front_direction_x = 0.0
    else:
        front_direction_x = clamp((dx / distance) * horizontal_gain, -1.0, 1.0)

    side_df["throw_side_direction_x"] = side_df["throw_direction_x"]
    side_df["throw_direction_x"] = front_direction_x
    side_df["front_camera_enabled"] = True
    side_df["front_motion_point"] = motion_point
    side_df["front_release_frame"] = int(front_release_row["frame_index"])
    side_df["front_start_frame"] = int(start_row["frame_index"])
    side_df["front_direction_x"] = front_direction_x
    side_df["front_raw_dx"] = dx
    side_df["front_raw_dy"] = dy
    side_df["front_direction_window"] = direction_window
    side_df["front_horizontal_gain"] = horizontal_gain

    output_path = Path(output_csv) if output_csv else Path(side_analysis_csv)
    side_df.to_csv(output_path, index=False)

    print("Front camera direction correction")
    print(f"Front landmarks CSV: {front_landmarks_csv}")
    print(f"Release frame: {release_frame}")
    print(f"Front frame used: {int(front_release_row['frame_index'])}")
    print(f"Front motion point: {motion_point}")
    print(f"Front raw movement: dx={dx:.4f}, dy={dy:.4f}")
    print(f"Front direction x: {front_direction_x:.4f}")
    print(f"Updated analysis CSV: {output_path}")

    return {
        "release_frame": release_frame,
        "front_release_frame": int(front_release_row["frame_index"]),
        "front_motion_point": motion_point,
        "front_direction_x": front_direction_x,
        "front_raw_dx": dx,
        "front_raw_dy": dy,
    }
