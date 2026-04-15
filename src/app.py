from __future__ import annotations

import io
from collections import defaultdict

from flask import Flask, jsonify, redirect, render_template, request, send_file, url_for

from config import BLINK_EAR_DROP, DB_PATH, FACE_MATCH_THRESHOLD, FRAME_SKIP
from database import AttendanceDB
from liveness import BlinkLiveness
from vision import FaceEngine, decode_base64_image

app = Flask(__name__)

db = AttendanceDB(DB_PATH)
db.init_schema()
db.seed_demo_data()

face_engine = FaceEngine()
blink_liveness = BlinkLiveness(ear_drop_threshold=BLINK_EAR_DROP)
frame_counters = defaultdict(int)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/admin")
def admin_dashboard():
    return render_template("admin.html")


@app.route("/lecturer")
def lecturer_dashboard():
    lecturer_id = int(request.args.get("lecturer_id", "2"))
    return render_template("lecturer.html", lecturer_id=lecturer_id)


@app.route("/student/register")
def student_register_page():
    return render_template("student_register.html")


@app.route("/student/scan")
def student_scan_page():
    return render_template("student_scan.html")


@app.route("/api/users", methods=["GET", "POST"])
def users_api():
    if request.method == "POST":
        data = request.get_json(force=True)
        user_id = db.create_user(data["name"], data["role"])
        return jsonify({"ok": True, "user_id": user_id})

    role = request.args.get("role")
    return jsonify(db.list_users(role=role))


@app.route("/api/courses", methods=["GET", "POST"])
def courses_api():
    if request.method == "POST":
        data = request.get_json(force=True)
        course_id = db.create_course(data["name"], int(data["lecturer_id"]))
        return jsonify({"ok": True, "course_id": course_id})

    lecturer_id = request.args.get("lecturer_id")
    return jsonify(db.list_courses(lecturer_id=int(lecturer_id) if lecturer_id else None))


@app.route("/api/enroll", methods=["POST"])
def enroll_api():
    data = request.get_json(force=True)
    db.enroll_student(int(data["student_id"]), int(data["course_id"]))
    return jsonify({"ok": True})


@app.route("/api/register_face", methods=["POST"])
def register_face_api():
    data = request.get_json(force=True)
    student_id = int(data["student_id"])
    frame = decode_base64_image(data.get("image", ""))
    if frame is None:
        return jsonify({"ok": False, "message": "Invalid image payload"}), 400

    small = frame[::2, ::2]
    faces = face_engine.detect_faces(small)
    if not faces:
        return jsonify({"ok": False, "message": "No face detected"}), 400

    embedding = faces[0]["embedding"]
    db.save_embedding(student_id, embedding)
    return jsonify({"ok": True, "message": "Face registered successfully"})


@app.route("/api/scan_frame", methods=["POST"])
def scan_frame_api():
    data = request.get_json(force=True)
    student_id = int(data["student_id"])
    course_id = int(data["course_id"])

    if not db.is_enrolled(student_id, course_id):
        return jsonify({"ok": False, "status": "blocked", "message": "Student is not enrolled in this course"})

    frame = decode_base64_image(data.get("image", ""))
    if frame is None:
        return jsonify({"ok": False, "status": "error", "message": "Invalid image payload"}), 400

    frame_counters[student_id] += 1
    if frame_counters[student_id] % FRAME_SKIP != 0:
        return jsonify({"ok": True, "status": "processing", "message": "Hold still..."})

    small = frame[::2, ::2]
    rgb_small = small[:, :, ::-1]

    liveness = blink_liveness.update(f"student:{student_id}", rgb_small)
    if not liveness["blinked"]:
        return jsonify(
            {
                "ok": False,
                "status": "blink_required",
                "message": liveness["message"],
                "liveness_score": 0.0,
            }
        )

    faces = face_engine.detect_faces(small)
    if not faces:
        return jsonify({"ok": False, "status": "no_face", "message": "Face not detected"})

    candidates = db.get_course_student_embeddings(course_id)
    if not candidates:
        return jsonify({"ok": False, "status": "no_candidates", "message": "No registered students for course"})

    match = face_engine.best_match(faces[0]["embedding"], candidates, threshold=FACE_MATCH_THRESHOLD)
    if not match or match.student_id != student_id:
        return jsonify({"ok": False, "status": "not_matched", "message": "Face not matched"})

    inserted = db.mark_attendance(student_id, course_id, confidence=match.similarity, liveness_score=1.0)
    return jsonify(
        {
            "ok": True,
            "status": "verified",
            "message": "Attendance marked" if inserted else "Already marked today",
            "similarity": round(match.similarity, 4),
            "liveness_score": 1.0,
        }
    )


@app.route("/api/attendance")
def attendance_api():
    course_id = request.args.get("course_id")
    lecturer_id = request.args.get("lecturer_id")
    return jsonify(
        db.fetch_attendance(
            course_id=int(course_id) if course_id else None,
            lecturer_id=int(lecturer_id) if lecturer_id else None,
            limit=300,
        )
    )


@app.route("/api/stats/daily")
def daily_stats_api():
    course_id = request.args.get("course_id")
    return jsonify(db.daily_counts(course_id=int(course_id) if course_id else None))


@app.route("/export/csv")
def export_csv():
    course_id = request.args.get("course_id")
    content = db.rows_as_csv(course_id=int(course_id) if course_id else None).encode("utf-8")
    return send_file(
        io.BytesIO(content),
        mimetype="text/csv",
        as_attachment=True,
        download_name="attendance_export.csv",
    )


@app.route("/export/pdf")
def export_pdf():
    rows = db.rows_as_iter()
    lines = ["Attendance Report", "================="]
    for row in rows:
        lines.append(
            f"{row['student_name']} | {row['course_name']} | {row['recognized_at']} | "
            f"sim={row['confidence']:.3f}"
        )
    content = "\n".join(lines).encode("utf-8")

    return send_file(
        io.BytesIO(content),
        mimetype="application/pdf",
        as_attachment=True,
        download_name="attendance_report.pdf",
    )


@app.route("/video_feed")
def legacy_video_feed_redirect():
    # Backward compatibility with previous UI entry.
    return redirect(url_for("student_scan_page"))


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
