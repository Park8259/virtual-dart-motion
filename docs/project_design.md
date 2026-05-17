## 1. 프로젝트 목표

이 프로젝트는 실제 다트를 던지지 않고, 사용자의 팔 동작을 영상으로 분석하여 가상의 다트 궤적과 명중 위치를 계산하는 프로토타입이다.  
현재 단계의 목표는 스마트폰으로 촬영한 투척 동작 영상을 입력으로 받아 손목, 팔꿈치, 어깨 좌표를 추출하고, 손목의 이동 속도와 방향을 기반으로 릴리즈 후보 프레임과 가상 명중 위치를 계산하는 것이다.

최종적으로는 계산된 명중 위치를 화면 시뮬레이터 또는 LED 타깃판에 출력하는 구조로 확장한다.

## 2. 현실적인 구현 방향

웹캠 실시간 방식은 손가락 릴리즈 순간을 안정적으로 잡기 어렵다. 일반 웹캠은 FPS가 낮고 손이 빠르게 움직이면 모션 블러가 생기기 때문이다.

따라서 현재 프로토타입은 다음 방식으로 구현한다.

```text
스마트폰 고속 촬영 영상
→ OpenCV 프레임 처리
→ MediaPipe 관절 좌표 추출
→ 손목 속도와 팔 방향 분석
→ 릴리즈 후보 프레임 추정
→ 가상 다트 궤적 계산
→ 보드 명중 위치 계산
```

이 방식은 완전한 실시간 게임은 아니지만, 릴리즈 순간과 손목 이동 방향을 더 안정적으로 분석할 수 있어 1차 프로토타입에 적합하다.

## 3. 전체 폴더 구조

```text
/Users/park/Uni/26-1/IoT/project
  .venv/
  docs/
    project_design.md
  output/
    landmarks.csv
    throw_analysis.csv
    trajectory.csv
    trajectory.png
  src/
    check_env.py
    extract_landmarks.py
    analyze_throw.py
    trajectory.py
  videos/
    throw_test.mp4
  README.md
  requirements.txt
```

## 4. 실행 순서

### 4.1 가상환경 실행

```bash
cd /Users/park/Uni/26-1/IoT/project
source .venv/bin/activate
```

### 4.2 환경 확인

```bash
python src/check_env.py
```

이 스크립트는 OpenCV, MediaPipe, NumPy, Pandas, Matplotlib이 정상 설치되었는지 확인한다.

### 4.3 영상에서 관절 좌표 추출

```bash
python src/extract_landmarks.py videos/throw_test.mp4 \
  --out output/landmarks.csv \
  --preview output/pose_preview.mp4
```

결과:

```text
output/landmarks.csv
output/pose_preview.mp4
```

`landmarks.csv`에는 프레임별 관절 좌표가 저장된다.  
`pose_preview.mp4`에는 MediaPipe가 인식한 자세 뼈대가 그려진 영상이 저장된다.

### 4.4 손목 속도와 릴리즈 후보 분석

```bash
python src/analyze_throw.py output/landmarks.csv \
  --hand right \
  --out output/throw_analysis.csv
```

결과:

```text
output/throw_analysis.csv
```

이 파일에는 손목 속도, 이동평균 속도, 팔꿈치 각도, 시작 프레임 표시, 릴리즈 후보 프레임 표시가 저장된다.

### 4.5 가상 다트 궤적 계산

```bash
python src/trajectory.py output/throw_analysis.csv \
  --hand right \
  --out output/trajectory.csv \
  --plot output/trajectory.png
```

결과:

```text
output/trajectory.csv
output/trajectory.png
```

`trajectory.csv`에는 시간별 가상 다트 좌표가 저장된다.  
`trajectory.png`에는 릴리즈 지점과 예상 포물선 궤적이 시각화된다.

## 5. 코드별 역할

## 5.1 check_env.py

역할:

```text
프로젝트 실행 환경 확인
```

확인하는 항목:

```text
OpenCV 버전
MediaPipe 버전
NumPy 버전
Pandas 버전
Matplotlib 버전
```

이 파일은 실제 분석에는 참여하지 않고, 개발 환경이 제대로 구성됐는지 확인하는 용도다.

## 5.2 extract_landmarks.py

역할:

```text
동영상에서 프레임별 사람 관절 좌표를 추출한다.
```

입력:

```text
videos/throw_test.mp4
```

처리 흐름:

```text
1. OpenCV로 동영상 파일을 연다.
2. FPS와 전체 프레임 수를 읽는다.
3. 프레임을 한 장씩 읽는다.
4. BGR 이미지를 RGB 이미지로 변환한다.
5. MediaPipe Pose를 적용한다.
6. 오른쪽/왼쪽 어깨, 팔꿈치, 손목 좌표를 추출한다.
7. 각 프레임의 좌표를 CSV에 저장한다.
8. 옵션이 있으면 관절선이 그려진 미리보기 영상을 저장한다.
```

저장되는 주요 컬럼:

```text
frame_index
time_sec
pose_detected
right_shoulder_x, right_shoulder_y, right_shoulder_z, right_shoulder_visibility
right_elbow_x, right_elbow_y, right_elbow_z, right_elbow_visibility
right_wrist_x, right_wrist_y, right_wrist_z, right_wrist_visibility
left_shoulder_x, left_shoulder_y, left_shoulder_z, left_shoulder_visibility
left_elbow_x, left_elbow_y, left_elbow_z, left_elbow_visibility
left_wrist_x, left_wrist_y, left_wrist_z, left_wrist_visibility
```

좌표는 MediaPipe의 정규화 좌표다.

```text
x: 화면 가로 위치, 0~1
y: 화면 세로 위치, 0~1
z: MediaPipe 기준 상대 깊이
visibility: 해당 관절을 얼마나 신뢰할 수 있는지 나타내는 값
```

## 5.3 analyze_throw.py

역할:

```text
관절 좌표 CSV에서 투척 동작의 속도, 방향, 릴리즈 후보 프레임을 계산한다.
```

입력:

```text
output/landmarks.csv
```

처리 흐름:

```text
1. landmarks.csv를 읽는다.
2. 분석할 손을 선택한다. 기본값은 right다.
3. 프레임별 손목 좌표 차이 dx, dy를 계산한다.
4. 프레임별 시간 차이 dt를 계산한다.
5. speed = sqrt(dx² + dy²) / dt 로 손목 속도를 계산한다.
6. 이동평균을 적용해 속도값을 부드럽게 만든다.
7. 팔꿈치 각도를 계산한다.
8. 손목 속도가 가장 높은 프레임을 릴리즈 후보 프레임으로 선택한다.
9. 릴리즈 후보보다 일정 프레임 전을 시작 프레임으로 선택한다.
10. 시작 프레임에서 릴리즈 후보 프레임까지의 평균 속도와 방향을 계산한다.
11. 16x16 가상 보드의 대략적인 명중 위치를 계산한다.
12. 분석 결과를 throw_analysis.csv로 저장한다.
```

중요한 점:

```text
릴리즈 후보 프레임은 실제 다트가 손에서 떨어진 정확한 순간이 아니다.
손목 속도가 높고 투척 동작이 발생했을 가능성이 큰 프레임을 의미한다.
```

현재 릴리즈 후보 기준:

```text
이동평균 손목 속도가 가장 큰 프레임
```

향후 개선 가능한 기준:

```text
손가락 펼침 정도
팔꿈치 각도 변화
손목이 타깃 방향으로 이동하는지 여부
관절 visibility 값
```

## 5.4 trajectory.py

역할:

```text
분석된 시작 프레임과 릴리즈 후보 프레임을 바탕으로 가상 다트 궤적을 예측한다.
```

입력:

```text
output/throw_analysis.csv
```

처리 흐름:

```text
1. throw_analysis.csv를 읽는다.
2. is_start_frame이 True인 행을 찾는다.
3. is_release_candidate가 True인 행을 찾는다.
4. 시작 프레임과 릴리즈 후보 프레임의 손목 좌표 차이를 계산한다.
5. 시간 차이를 이용해 초기 속도 vx, vy를 추정한다.
6. velocity_scale을 곱해 가상 다트에 맞는 속도로 보정한다.
7. 릴리즈 후보 프레임의 손목 위치를 가상 다트 시작점으로 설정한다.
8. 포물선 운동식을 이용해 시간별 좌표를 계산한다.
9. 마지막 좌표를 기준으로 16x16 보드의 명중 위치를 계산한다.
10. trajectory.csv와 trajectory.png를 저장한다.
```

사용하는 기본 수식:

```text
x(t) = x0 + vx * t
y(t) = y0 + vy * t + 0.5 * g * t²
```

여기서:

```text
x0, y0: 릴리즈 후보 프레임의 손목 좌표
vx, vy: 시작 프레임에서 릴리즈 후보 프레임까지의 손목 이동으로 추정한 초기 속도
g: 가상 중력 보정값
t: 가상 비행 시간
```

주의할 점:

```text
이 궤적은 실제 다트의 물리 궤적을 100% 재현하는 것이 아니다.
카메라 1대의 2D 좌표를 이용한 게임용 가상 궤적이다.
```

## 6. 전체 데이터 흐름

```text
videos/throw_test.mp4
  ↓ extract_landmarks.py
output/landmarks.csv
  ↓ analyze_throw.py
output/throw_analysis.csv
  ↓ trajectory.py
output/trajectory.csv
output/trajectory.png
```

## 7. 현재 프로토타입의 성공 기준

1차 프로토타입은 다음 조건을 만족하면 성공으로 본다.

```text
1. 스마트폰으로 촬영한 영상을 코드가 정상적으로 읽는다.
2. MediaPipe가 팔과 손목 좌표를 대부분의 프레임에서 추출한다.
3. 손목 속도 그래프에서 투척 구간이 뚜렷하게 나타난다.
4. 릴리즈 후보 프레임이 실제 던지는 순간 근처로 잡힌다.
5. 가상 궤적 이미지가 생성된다.
6. 명중 위치 좌표가 16x16 보드 범위 안에서 계산된다.
```

## 8. 촬영 조건

정확도를 높이려면 촬영 조건이 중요하다.

```text
스마트폰은 가능하면 120fps 이상으로 촬영한다.
카메라는 고정한다.
손과 팔이 화면 밖으로 나가지 않게 한다.
배경은 단순하고 손과 대비가 나게 한다.
조명을 밝게 한다.
측면 또는 45도 각도에서 촬영하면 팔의 전진 움직임을 보기 쉽다.
같은 위치에서 반복 촬영한다.
```

## 9. 한계점

현재 방식의 한계는 다음과 같다.

```text
카메라 1대만 사용하면 실제 깊이 방향 움직임을 정확히 알 수 없다.
손목 속도만으로 진짜 릴리즈 순간을 정확히 판단하기 어렵다.
손가락 좌표는 빠른 움직임에서 누락될 수 있다.
실제 다트의 회전, 손가락 힘, 공기 저항, 다트 무게는 반영하지 않는다.
```

따라서 현재 목표는 실제 다트 물리 궤적의 정밀 예측이 아니라,

```text
팔 동작 기반 가상 투사체 궤적 추정
```

으로 정의하는 것이 현실적이다.

## 10. 다음 개발 단계

다음 단계는 다음 순서로 진행한다.

```text
1. 실제 테스트 영상을 videos/에 넣고 전체 파이프라인 실행
2. pose_preview.mp4로 관절 인식 품질 확인
3. throw_analysis.csv에서 릴리즈 후보 프레임 확인
4. trajectory.png로 궤적이 자연스러운지 확인
5. window, lookback, direction-window, min-visibility, velocity-scale, gravity, duration, board-scale 튜닝
6. simulate_board.py를 만들어 16x16 보드 이미지로 명중 위치 시각화
7. ESP32 또는 LED 매트릭스와 연동
```

## 11. 발표용 핵심 설명

이 프로젝트의 현재 개발 방식은 다음과 같이 설명할 수 있다.

```text
스마트폰으로 촬영한 투척 동작 영상을 OpenCV로 프레임 단위로 읽고,
MediaPipe를 이용해 손목, 팔꿈치, 어깨 좌표를 추출한다.
이후 프레임별 손목 좌표 변화량으로 속도와 방향을 계산하고,
손목 속도가 가장 큰 구간을 릴리즈 후보로 추정한다.
릴리즈 후보 프레임의 손목 위치와 시작 프레임부터의 평균 이동 속도를
가상 다트의 초기 조건으로 사용하여 포물선 형태의 가상 궤적을 계산한다.
최종적으로 궤적의 도달 위치를 16x16 LED 타깃판 좌표로 변환한다.
```

## 12. 그래프가 이상할 때 확인할 점

현재 그래프가 이상하게 나오는 대표적인 이유는 다음과 같다.

```text
1. MediaPipe 손목 좌표가 특정 프레임에서 튄 경우
2. 전체 영상에서 속도 최대 프레임만 선택해 실제 릴리즈와 어긋난 경우
3. 이동평균 때문에 릴리즈 후보가 실제 속도 최고점보다 앞뒤로 밀린 경우
4. 시작 프레임부터 릴리즈 프레임까지 평균 방향을 써서 최종 손목 방향과 달라진 경우
5. velocity-scale, duration, gravity 값이 영상에 맞지 않는 경우
```

이를 보완하기 위해 현재 코드는 다음 방식을 사용한다.

```text
관절 visibility가 낮은 프레임 제외
속도 튐을 줄이기 위한 필터 적용
고속 구간 안에서 실제 손목 속도가 가장 큰 프레임을 릴리즈 후보로 선택
릴리즈 직전 몇 프레임의 이동 방향을 최종 방향으로 사용
```

궤적이 너무 짧으면 다음 값을 키운다.

```text
velocity-scale
duration
board-scale
```

궤적이 너무 많이 아래로 떨어지면 다음 값을 줄인다.

```text
gravity
```
