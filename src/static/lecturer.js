let chart;

async function fetchCourses(lecturerId) {
  const res = await fetch(`/api/courses?lecturer_id=${lecturerId}`);
  return res.json();
}

async function fetchAttendance(courseId, lecturerId) {
  const res = await fetch(`/api/attendance?course_id=${courseId}&lecturer_id=${lecturerId}`);
  return res.json();
}

async function fetchDaily(courseId) {
  const res = await fetch(`/api/stats/daily?course_id=${courseId}`);
  return res.json();
}

function renderRows(rows) {
  const tbody = document.getElementById('attendanceRows');
  tbody.innerHTML = rows.map((r) => `<tr class="border-b border-slate-800"><td class="py-2">${r.student_name}</td><td>${r.course_name}</td><td>${r.recognized_at}</td><td>${Number(r.confidence).toFixed(3)}</td></tr>`).join('');
}

function renderChart(stats) {
  const ctx = document.getElementById('dailyChart');
  if (chart) chart.destroy();
  chart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: stats.map((s) => s.day),
      datasets: [{ label: 'Attendance', data: stats.map((s) => s.count), borderColor: '#22d3ee' }]
    }
  });
}

async function bootLecturer() {
  const lecturerId = Number(document.getElementById('lecturerId').value);
  const courses = await fetchCourses(lecturerId);
  const select = document.getElementById('courseFilter');
  select.innerHTML = courses.map((c) => `<option value="${c.id}">${c.name}</option>`).join('');

  async function refresh() {
    const courseId = Number(select.value);
    const [rows, stats] = await Promise.all([fetchAttendance(courseId, lecturerId), fetchDaily(courseId)]);
    renderRows(rows);
    renderChart(stats);
    document.getElementById('csvLink').href = `/export/csv?course_id=${courseId}`;
    document.getElementById('pdfLink').href = `/export/pdf?course_id=${courseId}`;
  }

  select.addEventListener('change', refresh);
  await refresh();
}

bootLecturer();
