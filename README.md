# AI-Powered Smart Attendance System with Real-Time Face Recognition + Anti-Spoofing

This project provides a practical end-to-end attendance system with:
- **real-time face recognition** (OpenCV + `face_recognition`)
- **anti-spoofing / liveness signal** (blink + motion score)
- **attendance persistence** in **SQLite**
- **Flask dashboard** with logs, analytics, and export endpoints

## Features implemented

- Real-time face detection and identity matching
- Attendance logging with timestamp and liveness score
- Duplicate suppression (same person cannot be marked twice in one day)
- Liveness scoring using eye-aspect-ratio variation + face movement
- Admin dashboard page with:
  - live MJPEG stream
  - recent attendance table
  - daily attendance bar chart (Chart.js)
  - CSV and PDF export actions

## Project layout

```text
smart-attendance-project/
├── data/
│   ├── known_faces/
│   └── attendance.db
├── src/
│   ├── app.py
│   ├── config.py
│   ├── database.py
│   ├── liveness.py
│   ├── vision.py
│   ├── static/
│   │   ├── app.js
│   │   └── styles.css
│   └── templates/
│       └── index.html
└── requirements.txt
```

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

> `face_recognition` depends on `dlib`, which may require C++ build tooling.

## Add known faces

Put clear frontal images in `data/known_faces`.
- filename example: `Jane_Smith.jpg`
- display name becomes: `Jane Smith`

## Run

```bash
python src/app.py
```

Then open: `http://localhost:5000`

## API routes

- `GET /api/attendance` → recent attendance rows (JSON)
- `GET /api/stats/daily` → daily aggregate counts
- `GET /export/csv` → CSV export
- `GET /export/pdf` → simple PDF download placeholder

## Notes / Production recommendations

- Current anti-spoofing is lightweight heuristic; for strong security, integrate a dedicated liveness model.
- Current PDF export is minimal placeholder content; use `reportlab` or `weasyprint` for full formatting.
- For large deployments, move to MySQL/PostgreSQL and run Flask behind Gunicorn + Nginx.
