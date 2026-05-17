# IoT Motion Target Prototype

## 가상환경 실행

```bash
cd /Users/park/Uni/26-1/IoT/project
source .venv/bin/activate
```

## 패키지 설치

```bash
python -m pip install -r requirements.txt
```

## 환경 확인

```bash
python src/check_env.py
```

## 개발 순서

1. 스마트폰으로 투척 동작 영상을 촬영해 `videos/` 폴더에 넣는다.
2. OpenCV로 영상을 프레임 단위로 읽는다.
3. MediaPipe로 손목, 팔꿈치, 어깨 좌표를 추출한다.
4. 손목 좌표 변화량으로 릴리즈 프레임과 속도, 방향을 계산한다.
5. 릴리즈 후보와 초기 속도를 이용해 가상 다트 궤적을 계산한다.
6. 계산 결과를 화면 시뮬레이터 또는 LED 타깃판 출력으로 연결한다.

## 기본 실행 흐름

```bash
python src/extract_landmarks.py videos/throw_test.mp4 \
  --out output/landmarks.csv \
  --preview output/pose_preview.mp4

python src/analyze_throw.py output/landmarks.csv \
  --hand right \
  --out output/throw_analysis.csv

python src/trajectory.py output/throw_analysis.csv \
  --hand right \
  --out output/trajectory.csv \
  --plot output/trajectory.png
```

자세한 설계와 동작 흐름은 `docs/project_design.md`를 참고한다.
