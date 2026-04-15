const video = document.getElementById('scanCamera');
const statusEl = document.getElementById('scanStatus');

async function loadDropdowns() {
  const [studentsRes, coursesRes] = await Promise.all([
    fetch('/api/users?role=student'),
    fetch('/api/courses')
  ]);
  const students = await studentsRes.json();
  const courses = await coursesRes.json();

  document.getElementById('scanStudentId').innerHTML = students.map((s) => `<option value="${s.id}">${s.name} (#${s.id})</option>`).join('');
  document.getElementById('scanCourseId').innerHTML = courses.map((c) => `<option value="${c.id}">${c.name}</option>`).join('');
}

async function startCamera() {
  const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
  video.srcObject = stream;
}

function captureFrame() {
  const canvas = document.createElement('canvas');
  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  canvas.getContext('2d').drawImage(video, 0, 0);
  return canvas.toDataURL('image/jpeg', 0.85);
}

async function scanFace() {
  const student_id = Number(document.getElementById('scanStudentId').value);
  const course_id = Number(document.getElementById('scanCourseId').value);
  const image = captureFrame();

  const res = await fetch('/api/scan_frame', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ student_id, course_id, image })
  });
  const data = await res.json();

  statusEl.textContent = data.message || 'Please blink to verify';
  if (data.status === 'verified') {
    statusEl.className = 'mt-3 text-sm text-emerald-300';
  } else if (data.status === 'blink_required') {
    statusEl.className = 'mt-3 text-sm text-amber-300';
  } else {
    statusEl.className = 'mt-3 text-sm text-red-300';
  }
}

document.getElementById('startScanCamera').addEventListener('click', startCamera);
document.getElementById('scanFace').addEventListener('click', scanFace);
loadDropdowns();
