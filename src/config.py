from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
KNOWN_FACES_DIR = DATA_DIR / "known_faces"
DB_PATH = DATA_DIR / "attendance.db"
EXPORT_DIR = DATA_DIR / "exports"

# Recognition configuration
FACE_TOLERANCE = 0.5
FRAME_SCALE = 0.25

# Liveness configuration
MOTION_THRESHOLD = 6.0
BLINK_EAR_DROP = 0.08
LIVENESS_WINDOW = 12
