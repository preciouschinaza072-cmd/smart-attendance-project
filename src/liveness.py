from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Dict, Tuple

import numpy as np


Point = Tuple[int, int]


def _distance(p1: Point, p2: Point) -> float:
    return float(np.linalg.norm(np.array(p1) - np.array(p2)))


def eye_aspect_ratio(eye_points: list[Point]) -> float:
    """Compute Eye Aspect Ratio using 6-point eye contour."""
    if len(eye_points) != 6:
        return 0.0
    vertical_1 = _distance(eye_points[1], eye_points[5])
    vertical_2 = _distance(eye_points[2], eye_points[4])
    horizontal = _distance(eye_points[0], eye_points[3])
    if horizontal == 0:
        return 0.0
    return (vertical_1 + vertical_2) / (2.0 * horizontal)


@dataclass
class LivenessState:
    ear_history: Deque[float] = field(default_factory=lambda: deque(maxlen=12))
    center_history: Deque[Point] = field(default_factory=lambda: deque(maxlen=12))


class LivenessDetector:
    """Simple anti-spoofing by combining blink signal + motion signal."""

    def __init__(
        self,
        ear_drop_threshold: float = 0.08,
        motion_threshold: float = 6.0,
        window: int = 12,
    ):
        self.ear_drop_threshold = ear_drop_threshold
        self.motion_threshold = motion_threshold
        self.window = window
        self.states: Dict[str, LivenessState] = {}

    def _state(self, face_key: str) -> LivenessState:
        state = self.states.get(face_key)
        if state is None:
            state = LivenessState(
                ear_history=deque(maxlen=self.window),
                center_history=deque(maxlen=self.window),
            )
            self.states[face_key] = state
        return state

    def update(self, face_key: str, left_eye: list[Point], right_eye: list[Point], center: Point) -> float:
        state = self._state(face_key)

        ear_left = eye_aspect_ratio(left_eye)
        ear_right = eye_aspect_ratio(right_eye)
        ear = (ear_left + ear_right) / 2.0
        state.ear_history.append(ear)
        state.center_history.append(center)

        blink_score = 0.0
        motion_score = 0.0

        if len(state.ear_history) >= 4:
            max_ear = max(state.ear_history)
            min_ear = min(state.ear_history)
            ear_drop = max_ear - min_ear
            blink_score = min(1.0, ear_drop / max(self.ear_drop_threshold, 1e-5))

        if len(state.center_history) >= 2:
            movement = 0.0
            points = list(state.center_history)
            for prev, curr in zip(points, points[1:]):
                movement += _distance(prev, curr)
            avg_movement = movement / (len(points) - 1)
            motion_score = min(1.0, avg_movement / max(self.motion_threshold, 1e-5))

        return (0.6 * blink_score) + (0.4 * motion_score)
