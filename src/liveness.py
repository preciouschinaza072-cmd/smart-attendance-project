from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Dict, Tuple

import mediapipe as mp
import numpy as np

Point = Tuple[float, float]

LEFT_EYE_IDX = [33, 160, 158, 133, 153, 144]
RIGHT_EYE_IDX = [362, 385, 387, 263, 373, 380]


def _distance(p1: Point, p2: Point) -> float:
    return float(np.linalg.norm(np.array(p1) - np.array(p2)))


def eye_aspect_ratio(eye_points: list[Point]) -> float:
    if len(eye_points) != 6:
        return 0.0
    v1 = _distance(eye_points[1], eye_points[5])
    v2 = _distance(eye_points[2], eye_points[4])
    h = _distance(eye_points[0], eye_points[3])
    if h == 0:
        return 0.0
    return (v1 + v2) / (2 * h)


@dataclass
class BlinkState:
    ear_history: Deque[float] = field(default_factory=lambda: deque(maxlen=8))
    blinked: bool = False


class BlinkLiveness:
    """Blink-only liveness using MediaPipe FaceMesh landmarks."""

    def __init__(self, ear_drop_threshold: float = 0.06):
        self.ear_drop_threshold = ear_drop_threshold
        self.states: Dict[str, BlinkState] = {}
        self.mesh = mp.solutions.face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )

    def _state(self, key: str) -> BlinkState:
        state = self.states.get(key)
        if state is None:
            state = BlinkState()
            self.states[key] = state
        return state

    def _extract_eye(self, landmarks, idxs: list[int], width: int, height: int) -> list[Point]:
        pts: list[Point] = []
        for idx in idxs:
            lm = landmarks[idx]
            pts.append((lm.x * width, lm.y * height))
        return pts

    def update(self, key: str, frame_rgb: np.ndarray) -> dict:
        out = {"blinked": False, "ear": 0.0, "message": "Please blink to verify"}
        h, w = frame_rgb.shape[:2]
        result = self.mesh.process(frame_rgb)
        if not result.multi_face_landmarks:
            out["message"] = "Face not detected"
            return out

        state = self._state(key)
        landmarks = result.multi_face_landmarks[0].landmark
        left_eye = self._extract_eye(landmarks, LEFT_EYE_IDX, w, h)
        right_eye = self._extract_eye(landmarks, RIGHT_EYE_IDX, w, h)

        ear = (eye_aspect_ratio(left_eye) + eye_aspect_ratio(right_eye)) / 2.0
        state.ear_history.append(ear)

        if len(state.ear_history) >= 4:
            ear_range = max(state.ear_history) - min(state.ear_history)
            if ear_range >= self.ear_drop_threshold:
                state.blinked = True

        out["ear"] = ear
        out["blinked"] = state.blinked
        out["message"] = "Verified" if state.blinked else "Please blink to verify"
        return out
