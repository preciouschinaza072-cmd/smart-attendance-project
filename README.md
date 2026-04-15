# AI Biometric Smart Attendance (Incremental Upgrade)

This project upgrades the original Flask attendance app into a role-based biometric platform while preserving the existing modular structure (`app.py`, `database.py`, `vision.py`, `liveness.py`, `templates/`, `static/`).

## What changed (incremental, not full rewrite)

### Removed / Replaced
1. **Removed `face_recognition` / dlib dependency** from runtime requirements.
2. **Replaced recognition engine** in `src/vision.py`:
   - from `face_recognition` embeddings + distance matching
   - to **InsightFace embeddings** + **cosine similarity**.
3. **Replaced mixed liveness heuristic** with **blink-only verification** in `src/liveness.py` using **MediaPipe Face Mesh**.

### Added
1. **Role-aware data model** in `src/database.py`:
   - `users (admin|lecturer|student)`
   - `courses`
   - `enrollments`
   - `face_embeddings`
   - `attendance(student_id, course_id, timestamp, confidence, liveness_score)`
2. **Camera-based registration API** (`/api/register_face`) using base64 webcam frames.
3. **Blink-gated attendance API** (`/api/scan_frame`) requiring:
   - enrolled student
   - detected blink
   - embedding match (cosine threshold)
4. **Tailwind UI** with role-based pages:
   - `/admin`
   - `/lecturer`
   - `/student/register`
   - `/student/scan`
5. **Performance optimizations**:
   - resize frames before model inference
   - process every 2nd frame

## Project structure

```text
src/
├── app.py
├── config.py
├── database.py
├── liveness.py
├── main.py
├── vision.py
├── static/
│   ├── admin.js
│   ├── lecturer.js
│   ├── student_register.js
│   ├── student_scan.js
│   ├── app.js
│   └── styles.css
└── templates/
    ├── index.html
    ├── admin.html
    ├── lecturer.html
    ├── student_register.html
    └── student_scan.html
```

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python src/app.py
```

Open:
- Home: `http://localhost:5000/`
- Admin: `http://localhost:5000/admin`
- Lecturer: `http://localhost:5000/lecturer?lecturer_id=2`
- Student register: `http://localhost:5000/student/register`
- Student scan: `http://localhost:5000/student/scan`

## Flow

1. Admin creates users/courses and enrolls students.
2. Student opens **Register** page and clicks **Capture Face**.
3. Student opens **Scan** page, selects course, and scans face.
4. System only marks attendance when:
   - student is enrolled,
   - blink is detected,
   - embedding match passes cosine threshold.

## Backward compatibility notes

- Existing endpoints `/api/attendance`, `/api/stats/daily`, `/export/csv`, `/export/pdf` are preserved.
- `/video_feed` is kept as compatibility route and redirects to the new scan page.
