import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def read_hit_position(trajectory_csv):
    df = pd.read_csv(trajectory_csv)
    required = {"board_hit_x", "board_hit_y"}
    if not required.issubset(df.columns):
        raise ValueError("Trajectory CSV must contain board_hit_x and board_hit_y columns.")

    last = df.iloc[-1]
    return int(last["board_hit_x"]), int(last["board_hit_y"])


def render_board(hit_x, hit_y, board_w, board_h, output_png):
    fig, ax = plt.subplots(figsize=(7, 7))
    ax.set_xlim(0, board_w)
    ax.set_ylim(board_h, 0)
    ax.set_aspect("equal")

    for x in range(board_w + 1):
        ax.axvline(x, color="#cccccc", linewidth=0.8)
    for y in range(board_h + 1):
        ax.axhline(y, color="#cccccc", linewidth=0.8)

    ax.add_patch(
        plt.Rectangle(
            (hit_x, hit_y),
            1,
            1,
            facecolor="#ff3333",
            edgecolor="#111111",
            linewidth=2,
        )
    )

    ax.scatter([hit_x + 0.5], [hit_y + 0.5], color="#111111", s=80)
    ax.set_xticks(range(board_w))
    ax.set_yticks(range(board_h))
    ax.set_title(f"Virtual LED Board Hit: ({hit_x}, {hit_y}) on {board_w}x{board_h}")
    ax.set_xlabel("Board X")
    ax.set_ylabel("Board Y")
    ax.tick_params(labelsize=8)

    output_png.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(output_png, dpi=160)
    plt.close()

    print(f"Board hit position: ({hit_x}, {hit_y}) on {board_w}x{board_h}")
    print(f"Board image saved: {output_png}")


def main():
    parser = argparse.ArgumentParser(description="Render a virtual LED board hit image.")
    parser.add_argument("trajectory_csv", type=Path, help="CSV created by trajectory.py")
    parser.add_argument("--board-w", type=int, default=16, help="Virtual board width")
    parser.add_argument("--board-h", type=int, default=16, help="Virtual board height")
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("output/board_result.png"),
        help="Output board image path",
    )
    args = parser.parse_args()

    hit_x, hit_y = read_hit_position(args.trajectory_csv)
    render_board(hit_x, hit_y, args.board_w, args.board_h, args.out)


if __name__ == "__main__":
    main()
