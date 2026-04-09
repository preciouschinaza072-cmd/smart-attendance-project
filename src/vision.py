from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

import cv2
import face_recognition
import numpy as np


@dataclass
class KnownFace:
    name: str
    encoding: np.ndarray


def load_known_faces(directory: Path) -> List[KnownFace]:
    known_faces: List[KnownFace] = []
    directory.mkdir(parents=True, exist_ok=True)

    for image_path in sorted(directory.iterdir()):
        if image_path.suffix.lower() not in {".jpg", ".jpeg", ".png"}:
            continue

        image = face_recognition.load_image_file(str(image_path))
        encodings = face_recognition.face_encodings(image)
        if not encodings:
            continue
        known_faces.append(KnownFace(name=image_path.stem.replace("_", " "), encoding=encodings[0]))

    return known_faces


def recognize_face(face_encoding: np.ndarray, known_faces: List[KnownFace], tolerance: float) -> Optional[str]:
    if not known_faces:
        return None

    known_encodings = [k.encoding for k in known_faces]
    matches = face_recognition.compare_faces(known_encodings, face_encoding, tolerance=tolerance)
    if not any(matches):
        return None

    distances = face_recognition.face_distance(known_encodings, face_encoding)
    best_index = int(np.argmin(distances))
    return known_faces[best_index].name if matches[best_index] else None


def encode_jpeg(frame_bgr: np.ndarray) -> bytes:
    ok, buffer = cv2.imencode(".jpg", frame_bgr)
    if not ok:
        return b""
    return buffer.tobytes()


def landmarks_for_face(rgb_frame: np.ndarray, face_location: Tuple[int, int, int, int]):
    all_landmarks = face_recognition.face_landmarks(rgb_frame, [face_location])
    if not all_landmarks:
        return None
    return all_landmarks[0]
