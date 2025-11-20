const POLL_INTERVAL = 3000;
const DATA_URL = '/data';
const SIM_URL = '/simulate';

let chart = null;
let radarAlertActive = false;
let popupEl = null;
let popupMsgEl = null;
let popupCloseBtn = null;
let prevRadarVal = null;

// Time formatting
function fmtTime(iso) {
  if (!iso) return '--';
  return new Date(iso).toLocaleTimeString();
}

function showPopup(message) {
  if (!popupEl) return;
  if (popupMsgEl && message) popupMsgEl.textContent = message;
  popupEl.style.display = 'flex';
}

function hidePopup() {
  if (!popupEl) return;
  popupEl.style.display = 'none';
}

// Initialize Chart.js
function initChart() {
  const ctx = document.getElementById('sensorChart').getContext('2d');

  chart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: [],
      datasets: [
        { label: "Temperature (°C)", data: [], borderColor: "#ff4d67", tension: 0.3 },
        { label: "Humidity (%)", data: [], borderColor: "#3ba5ff", tension: 0.3 },
        { label: "Rainfall (mm/hr)", data: [], borderColor: "#ffe071", tension: 0.2 },
        { label: "Soil (0/1)", data: [], borderColor: "#2beb8a", tension: 0.1 },
        { label: "Radar", data: [], borderColor: "#c78cff", tension: 0.3 }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { labels: { color: "#e2e8f0" } }
      },
      scales: {
        x: { ticks: { color: "#e2e8f0" } },
        y: { ticks: { color: "#e2e8f0" } }
      }
    }
  });
}

// Update UI cards
function updateUI(latest) {
  if (!latest) return;

  document.getElementById('temp').textContent = latest.temperature + " °C";
  document.getElementById('hum').textContent = latest.humidity + " %";
  document.getElementById('rain').textContent = latest.rainfall;
  document.getElementById('soil').textContent = latest.soil ? "Wet" : "Dry";
  document.getElementById('ult').textContent = latest.ultrasonic;
  document.getElementById('updated').textContent = fmtTime(latest.timestamp);

  const radarVal = Number(latest.ultrasonic);
  if (Number.isFinite(radarVal)) {
    // Debug log (can be removed later)
    console.log('Radar:', radarVal, 'Prev:', prevRadarVal);
    const crossedUp = (prevRadarVal == null || prevRadarVal <= 6) && radarVal > 6;
    if (crossedUp && !radarAlertActive) {
      radarAlertActive = true;
      showPopup('Cloud Burst: Radar value exceeded threshold (> 6).');
    }
    if (radarVal <= 6) {
      radarAlertActive = false;
    }
    prevRadarVal = radarVal;
  }
}

function loadAndRender() {
  fetch(DATA_URL)
    .then(res => res.json())
    .then(data => {
      updateUI(data.latest);
      renderChart(data.history);
    })
    .catch(err => console.log("Error:", err));
}

function renderChart(history) {
  if (!chart) return;

  chart.data.labels = history.map(s =>
    new Date(s.timestamp).toLocaleTimeString()
  );

  chart.data.datasets[0].data = history.map(s => s.temperature);
  chart.data.datasets[1].data = history.map(s => s.humidity);
  chart.data.datasets[2].data = history.map(s => s.rainfall);
  chart.data.datasets[3].data = history.map(s => s.soil);
  chart.data.datasets[4].data = history.map(s => s.ultrasonic);

  chart.update();
}

// EVENTS
document.addEventListener("DOMContentLoaded", () => {
  // Cache popup elements and wire handlers FIRST so alerts can show on first data load
  popupEl = document.getElementById('cloudburstPopup');
  popupMsgEl = document.getElementById('cloudburstMsg');
  popupCloseBtn = document.getElementById('cloudburstClose');
  if (popupCloseBtn) popupCloseBtn.addEventListener('click', hidePopup);
  if (popupEl) {
    popupEl.addEventListener('click', (e) => {
      if (e.target === popupEl) hidePopup();
    });
  }

  initChart();
  loadAndRender();
  setInterval(loadAndRender, POLL_INTERVAL);

  document.getElementById('simulateBtn').addEventListener('click', () => {
    fetch(SIM_URL).then(() => loadAndRender());
  });

  document.getElementById('clearBtn').addEventListener('click', () => {
    chart.data.labels = [];
    chart.data.datasets.forEach(d => d.data = []);
    chart.update();
  });
});
