async function fetchAttendance() {
  const res = await fetch('/api/attendance');
  return res.json();
}

async function fetchDailyStats() {
  const res = await fetch('/api/stats/daily');
  return res.json();
}

function renderTable(rows) {
  const tbody = document.querySelector('#attendanceTable tbody');
  tbody.innerHTML = '';
  rows.forEach((r) => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${r.id}</td>
      <td>${r.person_name}</td>
      <td>${r.recognized_at}</td>
      <td>${Number(r.liveness_score).toFixed(2)}</td>
    `;
    tbody.appendChild(tr);
  });
}

function renderChart(stats) {
  const ctx = document.getElementById('dailyChart');
  new Chart(ctx, {
    type: 'bar',
    data: {
      labels: stats.map((s) => s.day),
      datasets: [{
        label: 'Attendance Count',
        data: stats.map((s) => s.count),
        backgroundColor: '#38bdf8',
      }]
    },
    options: {
      scales: {
        y: { beginAtZero: true }
      }
    }
  });
}

async function boot() {
  const [rows, stats] = await Promise.all([fetchAttendance(), fetchDailyStats()]);
  renderTable(rows);
  renderChart(stats);
}

boot();
setInterval(boot, 10000);
