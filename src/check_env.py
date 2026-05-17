import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("MPLCONFIGDIR", str(PROJECT_ROOT / ".mplconfig"))

import cv2
import mediapipe as mp
import numpy as np
import pandas as pd
import matplotlib


def main():
    print("Environment OK")
    print(f"OpenCV: {cv2.__version__}")
    print(f"MediaPipe: {mp.__version__}")
    print(f"NumPy: {np.__version__}")
    print(f"Pandas: {pd.__version__}")
    print(f"Matplotlib: {matplotlib.__version__}")


if __name__ == "__main__":
    main()
