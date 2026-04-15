async function fetchUsers(role) {
  const res = await fetch(`/api/users${role ? `?role=${role}` : ''}`);
  return res.json();
}

async function fetchCourses() {
  const res = await fetch('/api/courses');
  return res.json();
}

function fillSelect(el, rows, textKey = 'name', valueKey = 'id') {
  el.innerHTML = rows.map((r) => `<option value="${r[valueKey]}">${r[textKey]} (#${r[valueKey]})</option>`).join('');
}

async function bootstrapAdmin() {
  const lecturers = await fetchUsers('lecturer');
  const students = await fetchUsers('student');
  const courses = await fetchCourses();
  fillSelect(document.getElementById('lecturerSelect'), lecturers);
  fillSelect(document.getElementById('studentSelect'), students);
  fillSelect(document.getElementById('courseSelect'), courses);
}

async function createUser() {
  const name = document.getElementById('userName').value;
  const role = document.getElementById('userRole').value;
  await fetch('/api/users', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name, role }) });
  document.getElementById('status').textContent = 'User created';
  bootstrapAdmin();
}

async function createCourse() {
  const name = document.getElementById('courseName').value;
  const lecturer_id = Number(document.getElementById('lecturerSelect').value);
  await fetch('/api/courses', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name, lecturer_id }) });
  document.getElementById('status').textContent = 'Course created';
  bootstrapAdmin();
}

async function enrollStudent() {
  const student_id = Number(document.getElementById('studentSelect').value);
  const course_id = Number(document.getElementById('courseSelect').value);
  await fetch('/api/enroll', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ student_id, course_id }) });
  document.getElementById('status').textContent = 'Student enrolled';
}

bootstrapAdmin();
