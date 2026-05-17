import argparse
import math
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("MPLCONFIGDIR", str(PROJECT_ROOT / ".mplconfig"))

import pandas as pd


def clamp(value, low, high):
    return max(low, min(high, value))


def get_marked_row(df, column_name):
    if column_name not in df.columns:
        raise ValueError(f"Missing marker column: {column_name}")

    marked = df[df[column_name] == True]
    if marked.empty:
        raise ValueError(f"No frame is marked as {column_name}")

    return marked.iloc[0]


def normalize_vector(x, y):
    length = math.hypot(x, y)
    if length == 0 or math.isnan(length):
        return 0.0, 0.0
    return x / length, y / length


def estimate_initial_velocity(start_row, release_row, hand, velocity_scale):
    if {
        "throw_direction_x",
        "throw_direction_y",
        "throw_release_speed",
    }.issubset(release_row.index):
        direction_x = release_row["throw_direction_x"]
        direction_y = release_row["throw_direction_y"]
        release_speed = release_row["throw_release_speed"]
        if not any(pd.isna(v) for v in [direction_x, direction_y, release_speed]):
            vx = direction_x * release_speed * velocity_scale
            vy = direction_y * release_speed * velocity_scale
            speed = math.hypot(vx, vy)
            return vx, vy, speed

    start_x = start_row[f"{hand}_wrist_x"]
    start_y = start_row[f"{hand}_wrist_y"]
    release_x = release_row[f"{hand}_wrist_x"]
    release_y = release_row[f"{hand}_wrist_y"]
    dt = release_row["time_sec"] - start_row["time_sec"]

    if dt <= 0 or pd.isna(dt):
        return 0.0, 0.0, 0.0

    vx = ((release_x - start_x) / dt) * velocity_scale
    vy = ((release_y - start_y) / dt) * velocity_scale
    speed = math.hypot(vx, vy)
    return vx, vy, speed


def build_trajectory(release_x, release_y, vx, vy, gravity, duration, steps):
    points = []
    if steps < 2:
        raise ValueError("--steps must be at least 2")

    for i in range(steps):
        t = duration * i / (steps - 1)
        x = release_x + vx * t
        y = release_y + vy * t + 0.5 * gravity * (t**2)
        points.append(
            {
                "point_index": i,
                "t": t,
                "x": x,
                "y": y,
            }
        )

    return points


def endpoint_to_board(endpoint, release_x, release_y, board_w, board_h, board_scale):
    center_x = (board_w - 1) / 2
    center_y = (board_h - 1) / 2

    delta_x = endpoint["x"] - release_x
    delta_y = endpoint["y"] - release_y

    hit_x = center_x + delta_x * board_scale
    hit_y = center_y + delta_y * board_scale

    return (
        int(round(clamp(hit_x, 0, board_w - 1))),
        int(round(clamp(hit_y, 0, board_h - 1))),
    )


def save_plot(points, start_row, release_row, hand, hit, plot_path, board_w, board_h):
    import matplotlib.pyplot as plt

    xs = [point["x"] for point in points]
    ys = [point["y"] for point in points]
    endpoint = points[-1]

    plt.figure(figsize=(7, 7))
    plt.plot(xs, ys, marker="o", linewidth=2, markersize=3, label="Predicted trajectory")
    plt.scatter(
        [start_row[f"{hand}_wrist_x"]],
        [start_row[f"{hand}_wrist_y"]],
        color="gray",
        s=80,
        label="Start frame",
    )
    plt.scatter(
        [release_row[f"{hand}_wrist_x"]],
        [release_row[f"{hand}_wrist_y"]],
        color="red",
        s=80,
        label="Release candidate",
    )
    plt.scatter(
        [endpoint["x"]],
        [endpoint["y"]],
        color="dodgerblue",
        edgecolor="black",
        s=90,
        label="Trajectory endpoint",
    )
    plt.annotate(
        "release",
        (release_row[f"{hand}_wrist_x"], release_row[f"{hand}_wrist_y"]),
        textcoords="offset points",
        xytext=(8, -14),
    )
    plt.annotate(
        "endpoint",
        (endpoint["x"], endpoint["y"]),
        textcoords="offset points",
        xytext=(8, 8),
    )
    plt.gca().invert_yaxis()
    margin = 0.08
    min_x = min(0, min(xs), start_row[f"{hand}_wrist_x"], release_row[f"{hand}_wrist_x"]) - margin
    max_x = max(1, max(xs), start_row[f"{hand}_wrist_x"], release_row[f"{hand}_wrist_x"]) + margin
    min_y = min(0, min(ys), start_row[f"{hand}_wrist_y"], release_row[f"{hand}_wrist_y"]) - margin
    max_y = max(1, max(ys), start_row[f"{hand}_wrist_y"], release_row[f"{hand}_wrist_y"]) + margin
    plt.xlim(min_x, max_x)
    plt.ylim(max_y, min_y)
    plt.grid(True, alpha=0.25)
    plt.title(f"Predicted Virtual Dart Trajectory / Board Hit: {hit} on {board_w}x{board_h}")
    plt.xlabel("Normalized camera X")
    plt.ylabel("Normalized camera Y")
    plt.legend()
    plot_path.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(plot_path, dpi=160)
    plt.close()


def predict(
    analysis_csv,
    hand,
    output_csv,
    plot_path,
    gravity,
    duration,
    steps,
    velocity_scale,
    board_w,
    board_h,
    board_scale,
):
    df = pd.read_csv(analysis_csv)
    hand = hand.lower()

    start_row = get_marked_row(df, "is_start_frame")
    release_row = get_marked_row(df, "is_release_candidate")

    vx, vy, speed = estimate_initial_velocity(start_row, release_row, hand, velocity_scale)
    direction_x, direction_y = normalize_vector(vx, vy)

    release_x = release_row[f"{hand}_wrist_x"]
    release_y = release_row[f"{hand}_wrist_y"]

    points = build_trajectory(release_x, release_y, vx, vy, gravity, duration, steps)
    endpoint = points[-1]
    hit = endpoint_to_board(endpoint, release_x, release_y, board_w, board_h, board_scale)

    trajectory_df = pd.DataFrame(points)
    trajectory_df["vx"] = vx
    trajectory_df["vy"] = vy
    trajectory_df["speed"] = speed
    trajectory_df["direction_x"] = direction_x
    trajectory_df["direction_y"] = direction_y
    trajectory_df["board_hit_x"] = hit[0]
    trajectory_df["board_hit_y"] = hit[1]

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    trajectory_df.to_csv(output_csv, index=False)

    if plot_path:
        save_plot(points, start_row, release_row, hand, hit, plot_path, board_w, board_h)

    print("Trajectory prediction result")
    print(f"Input analysis CSV: {analysis_csv}")
    print(f"Hand: {hand}")
    print(f"Initial velocity: ({vx:.4f}, {vy:.4f})")
    print(f"Initial speed: {speed:.4f}")
    print(f"Direction: ({direction_x:.4f}, {direction_y:.4f})")
    print(f"Gravity: {gravity}")
    print(f"Duration: {duration}s")
    print(f"Endpoint: ({endpoint['x']:.4f}, {endpoint['y']:.4f})")
    print(f"Board hit position: {hit} on {board_w}x{board_h}")
    print(f"Trajectory CSV saved: {output_csv}")
    if plot_path:
        print(f"Trajectory plot saved: {plot_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Predict a virtual dart trajectory from throw analysis CSV."
    )
    parser.add_argument(
        "analysis_csv",
        type=Path,
        help="CSV created by analyze_throw.py",
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
        default=Path("output/trajectory.csv"),
        help="Output CSV for trajectory points",
    )
    parser.add_argument(
        "--plot",
        type=Path,
        default=Path("output/trajectory.png"),
        help="Optional trajectory plot path",
    )
    parser.add_argument(
        "--gravity",
        type=float,
        default=0.25,
        help="Virtual downward acceleration in normalized camera units",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=0.8,
        help="Virtual flight duration in seconds",
    )
    parser.add_argument(
        "--steps",
        type=int,
        default=30,
        help="Number of trajectory sample points",
    )
    parser.add_argument(
        "--velocity-scale",
        type=float,
        default=0.8,
        help="Scale factor applied to wrist velocity before trajectory prediction",
    )
    parser.add_argument("--board-w", type=int, default=16, help="Virtual board width")
    parser.add_argument("--board-h", type=int, default=16, help="Virtual board height")
    parser.add_argument(
        "--board-scale",
        type=float,
        default=20.0,
        help="Scale factor from normalized trajectory displacement to board cells",
    )
    args = parser.parse_args()

    predict(
        args.analysis_csv,
        args.hand,
        args.out,
        args.plot,
        args.gravity,
        args.duration,
        args.steps,
        args.velocity_scale,
        args.board_w,
        args.board_h,
        args.board_scale,
    )


if __name__ == "__main__":
    main()
