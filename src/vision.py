from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

import cv2
import numpy as np
from insightface.app import FaceAnalysis


@dataclass
class MatchResult:
    student_id: int
    student_name: str
    similarity: float


class FaceEngine:
    def __init__(self, det_size: Tuple[int, int] = (320, 320)):
        self.analyzer = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
        self.analyzer.prepare(ctx_id=0, det_size=det_size)

    def detect_faces(self, frame_bgr: np.ndarray) -> list[Dict[str, Any]]:
        faces = self.analyzer.get(frame_bgr)
        results: list[Dict[str, Any]] = []
        for f in faces:
            results.append(
                {
                    "bbox": f.bbox.astype(int).tolist(),
                    "embedding": np.asarray(f.embedding, dtype=np.float32),
                }
            )
        return results

    @staticmethod
    def cosine_similarity(v1: np.ndarray, v2: np.ndarray) -> float:
        denom = (np.linalg.norm(v1) * np.linalg.norm(v2)) + 1e-8
        return float(np.dot(v1, v2) / denom)

    def best_match(
        self,
        query_embedding: np.ndarray,
        candidates: list[Dict[str, Any]],
        threshold: float,
    ) -> Optional[MatchResult]:
        best: Optional[MatchResult] = None
        for c in candidates:
            sim = self.cosine_similarity(query_embedding, c["embedding"])
            if best is None or sim > best.similarity:
                best = MatchResult(
                    student_id=int(c["student_id"]),
                    student_name=str(c["student_name"]),
                    similarity=sim,
                )
        if best is None or best.similarity < threshold:
            return None
        return best


def decode_base64_image(payload: str) -> Optional[np.ndarray]:
    """Decode data URL/base64 image into BGR image."""
    if not payload:
        return None

    if "," in payload:
        payload = payload.split(",", 1)[1]

    try:
        raw = base64.b64decode(payload)
        arr = np.frombuffer(raw, dtype=np.uint8)
        image = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        return image
    except Exception:
        return None


def encode_jpeg(frame_bgr: np.ndarray) -> bytes:
    ok, buffer = cv2.imencode(".jpg", frame_bgr)
    if not ok:
        return b""
    return buffer.tobytes()
