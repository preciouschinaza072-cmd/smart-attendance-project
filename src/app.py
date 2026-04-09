from __future__ import annotations

import io
from datetime import datetime

import cv2
import face_recognition
from flask import Flask, Response, jsonify, render_template, send_file

from config import (
    BLINK_EAR_DROP,
    DB_PATH,
    EXPORT_DIR,
    FACE_TOLERANCE,
    FRAME_SCALE,
    KNOWN_FACES_DIR,
    LIVENESS_WINDOW,
    MOTION_THRESHOLD,
)
from database import AttendanceDB
from liveness import LivenessDetector
from vision import encode_jpeg, landmarks_for_face, load_known_faces, recognize_face

app = Flask(__name__)

db = AttendanceDB(DB_PATH)
db.init_schema()

known_faces = load_known_faces(KNOWN_FACES_DIR)
liveness = LivenessDetector(
    ear_drop_threshold=BLINK_EAR_DROP,
    motion_threshold=MOTION_THRESHOLD,
    window=LIVENESS_WINDOW,
)


def generate_camera_stream():
    camera = cv2.VideoCapture(0)
    if not camera.isOpened():
        return

    while True:
        ok, frame = camera.read()
        if not ok:
            break

        small = cv2.resize(frame, (0, 0), fx=FRAME_SCALE, fy=FRAME_SCALE)
        rgb_small = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)

        locations = face_recognition.face_locations(rgb_small)
        encodings = face_recognition.face_encodings(rgb_small, locations)

        for location, encoding in zip(locations, encodings):
            top, right, bottom, left = location
            name = recognize_face(encoding, known_faces, tolerance=FACE_TOLERANCE) or "Unknown"

            landmarks = landmarks_for_face(rgb_small, location)
            score = 0.0
            if landmarks and "left_eye" in landmarks and "right_eye" in landmarks:
                center = ((left + right) // 2, (top + bottom) // 2)
                face_key = f"{name}:{left}:{top}"
                score = liveness.update(face_key, landmarks["left_eye"], landmarks["right_eye"], center)

            live_ok = score >= 0.5
            if name != "Unknown" and live_ok:
                db.mark_attendance(name, score)

            # scale back to original resolution
            inv = int(1 / FRAME_SCALE)
            top, right, bottom, left = [v * inv for v in (top, right, bottom, left)]

            color = (0, 200, 0) if live_ok and name != "Unknown" else (0, 0, 255)
            label = f"{name} | live:{score:.2f}" if name != "Unknown" else "Unknown"
            cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
            cv2.rectangle(frame, (left, bottom - 28), (right, bottom), color, cv2.FILLED)
            cv2.putText(frame, label, (left + 5, bottom - 7), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)

        payload = encode_jpeg(frame)
        if not payload:
            continue

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" + payload + b"\r\n"
        )

    camera.release()


@app.route("/")
def dashboard():
    return render_template("index.html", now=datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"))


@app.route("/video_feed")
def video_feed():
    return Response(generate_camera_stream(), mimetype="multipart/x-mixed-replace; boundary=frame")


@app.route("/api/attendance")
def attendance_api():
    return jsonify(db.fetch_recent(limit=200))


@app.route("/api/stats/daily")
def daily_stats_api():
    return jsonify(db.daily_counts())


@app.route("/export/csv")
def export_csv():
    content = db.rows_as_csv().encode("utf-8")
    return send_file(
        io.BytesIO(content),
        mimetype="text/csv",
        as_attachment=True,
        download_name="attendance_export.csv",
    )


@app.route("/export/pdf")
def export_pdf():
    # Minimal PDF-like export placeholder (plain text in .pdf extension).
    # Replace with reportlab/weasyprint in production.
    rows = db.rows_as_iter()
    lines = ["Attendance Report", "================="]
    for row in rows:
        lines.append(f"{row['person_name']} | {row['recognized_at']} | live={row['liveness_score']:.2f}")
    content = "\n".join(lines).encode("utf-8")

    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    return send_file(
        io.BytesIO(content),
        mimetype="application/pdf",
        as_attachment=True,
        download_name="attendance_report.pdf",
    )


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
