# Virtual Dart Motion

실제 다트를 던지지 않고, 사용자의 투척 동작 영상을 분석하여 가상의 다트 궤적과 명중 위치를 추정하는 프로토타입입니다.

이 프로젝트는 스마트폰으로 촬영한 투척 동작 영상을 입력으로 받아 MediaPipe로 팔 관절 좌표를 추출하고, 손목의 이동 속도와 방향을 기반으로 릴리즈 후보 프레임과 가상 다트 궤적을 계산합니다.

## 프로젝트 개요

기존 다트나 투척형 활동은 실제 물체를 던져야 하므로 부상 위험과 공간 제약이 있습니다. 본 프로젝트는 실제 물체 없이 사용자의 팔 동작만으로 가상의 투사체 결과를 계산하여, 안전한 비접촉형 타깃 시스템으로 확장하는 것을 목표로 합니다.

현재 구현 단계에서는 실제 LED 타깃판 대신 영상 분석 결과와 가상 궤적을 CSV 및 이미지로 출력합니다. 이후 계산된 명중 위치를 LED 매트릭스 또는 화면 시뮬레이터에 연결할 수 있습니다.

## 주요 기능

- 동영상에서 프레임별 사용자 자세 좌표 추출
- MediaPipe Pose 기반 어깨, 팔꿈치, 손목 좌표 저장
- 손목 좌표 변화량 기반 속도 및 방향 계산
- 손목 속도 기반 릴리즈 후보 프레임 추정
- 시작 프레임과 릴리즈 후보 프레임 기반 가상 초기 속도 계산
- 포물선 모델을 이용한 가상 다트 궤적 예측
- 가상 보드 명중 위치 계산
- 분석 결과 CSV 및 궤적 이미지 출력

## 기술 스택

- Python
- OpenCV
- MediaPipe
- Pandas
- NumPy
- Matplotlib

## 프로젝트 구조

```text
virtual-dart-motion/
  docs/
    project_design.md
  output/
    분석 결과 파일이 저장되는 폴더
  src/
    check_env.py
    extract_landmarks.py
    analyze_throw.py
    trajectory.py
  videos/
    분석할 투척 동영상 파일을 넣는 폴더
  requirements.txt
  README.md
```

## 설치 방법

프로젝트 폴더로 이동합니다.

```bash
cd /Users/park/Uni/26-1/IoT/project
```

가상환경을 생성하지 않았다면 다음 명령어로 생성합니다.

```bash
python3 -m venv .venv
```

가상환경을 실행합니다.

```bash
source .venv/bin/activate
```

필요한 패키지를 설치합니다.

```bash
python -m pip install -r requirements.txt
```

설치가 정상적으로 되었는지 확인합니다.

```bash
python src/check_env.py
```

## 실행 방법

분석할 투척 동영상을 `videos/` 폴더에 넣습니다. 예시는 `videos/throw_test.mp4`입니다.

### 1. 영상에서 관절 좌표 추출

```bash
python src/extract_landmarks.py videos/throw_test.mp4 \
  --out output/landmarks.csv \
  --preview output/pose_preview.mp4
```

출력 결과:

- `output/landmarks.csv`: 프레임별 관절 좌표
- `output/pose_preview.mp4`: MediaPipe 관절선이 표시된 확인용 영상

### 2. 투척 동작 분석

```bash
python src/analyze_throw.py output/landmarks.csv \
  --hand right \
  --out output/throw_analysis.csv
```

출력 결과:

- `output/throw_analysis.csv`: 손목 속도, 팔꿈치 각도, 시작 프레임, 릴리즈 후보 프레임

### 3. 가상 다트 궤적 계산

```bash
python src/trajectory.py output/throw_analysis.csv \
  --hand right \
  --out output/trajectory.csv \
  --plot output/trajectory.png
```

출력 결과:

- `output/trajectory.csv`: 시간별 가상 궤적 좌표
- `output/trajectory.png`: 예측된 가상 다트 궤적 이미지

## 전체 동작 흐름

```text
투척 동작 영상
  ↓
OpenCV로 프레임 단위 처리
  ↓
MediaPipe로 팔 관절 좌표 추출
  ↓
손목 속도 및 이동 방향 계산
  ↓
릴리즈 후보 프레임 추정
  ↓
가상 다트 초기 속도 계산
  ↓
포물선 형태의 가상 궤적 예측
  ↓
가상 보드 명중 위치 계산
```

## 코드 설명

### `src/check_env.py`

개발 환경을 확인하는 스크립트입니다. OpenCV, MediaPipe, NumPy, Pandas, Matplotlib 버전을 출력합니다.

### `src/extract_landmarks.py`

동영상을 프레임 단위로 읽고 MediaPipe Pose를 적용하여 오른쪽/왼쪽 어깨, 팔꿈치, 손목 좌표를 CSV로 저장합니다. 옵션으로 관절선이 그려진 미리보기 영상을 생성할 수 있습니다.

### `src/analyze_throw.py`

`landmarks.csv`를 읽어 손목의 프레임별 이동 속도를 계산합니다. 이동평균을 적용한 뒤 손목 속도가 가장 높은 프레임을 릴리즈 후보 프레임으로 추정하고, 시작 프레임부터 릴리즈 후보 프레임까지의 평균 속도와 방향을 계산합니다.

### `src/trajectory.py`

`throw_analysis.csv`에서 시작 프레임과 릴리즈 후보 프레임을 읽고, 릴리즈 후보 프레임의 손목 위치를 가상 다트의 시작점으로 설정합니다. 이후 포물선 운동 모델을 적용하여 가상 궤적과 보드 명중 위치를 계산합니다.

## 현재 한계

- 현재 방식은 실제 다트의 물리 궤적을 정확히 재현하는 것이 아니라, 팔 동작 기반의 가상 투사체 궤적을 추정하는 방식입니다.
- 카메라 1대의 2D 좌표를 사용하므로 실제 깊이 방향 움직임을 정확히 알 수 없습니다.
- 손목 속도 기반 릴리즈 후보 추정은 실제 릴리즈 순간과 차이가 있을 수 있습니다.
- 손가락 움직임, 손목 스냅, 다트 회전, 공기 저항 등은 아직 반영하지 않았습니다.

## 향후 개선 방향

- 손가락 펼침 정도를 이용한 릴리즈 순간 보정
- 측면 카메라 추가를 통한 깊이 방향 추정
- 가상 LED 보드 시뮬레이터 구현
- ESP32 및 LED 매트릭스 연동
- 사용자별 점수 기록 및 온라인 비교 기능 추가

## 자세한 설계 문서

전체 설계와 코드별 동작 흐름은 [`docs/project_design.md`](docs/project_design.md)를 참고하면 됩니다.
