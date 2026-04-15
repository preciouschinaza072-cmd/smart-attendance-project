const video = document.getElementById('camera');
const statusEl = document.getElementById('registerStatus');

async function loadStudents() {
  const res = await fetch('/api/users?role=student');
  const students = await res.json();
  document.getElementById('studentId').innerHTML = students.map((s) => `<option value="${s.id}">${s.name} (#${s.id})</option>`).join('');
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
  return canvas.toDataURL('image/jpeg', 0.92);
}

async function registerFace() {
  const student_id = Number(document.getElementById('studentId').value);
  const image = captureFrame();
  const res = await fetch('/api/register_face', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ student_id, image })
  });
  const data = await res.json();
  statusEl.textContent = data.message;
  statusEl.className = data.ok ? 'mt-3 text-sm text-emerald-300' : 'mt-3 text-sm text-red-300';
}

document.getElementById('startCamera').addEventListener('click', startCamera);
document.getElementById('captureFace').addEventListener('click', registerFace);
loadStudents();
