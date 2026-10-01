/* ==============================================================================
   GéoFoncier NGOGOM_UAD — Graphiques Chart.js (charts.js)
   Helpers d'instanciation pour diagrammes donut et diagrammes en barres
   ============================================================================== */

/* =====================================================
   Graphique Donut (Répartition des espaces, taux d'occupation)
   ===================================================== */
function createDonutChart(canvasId, labels, data, colors) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;
  return new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels,
      datasets: [{
        data,
        backgroundColor: colors,
        borderWidth: 2,
        borderColor: '#fff'
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'bottom',
          labels: { padding: 16, font: { family: 'Poppins', size: 12 } }
        },
        tooltip: {
          callbacks: {
            label: ctx => ` ${ctx.label}: ${ctx.parsed.toFixed(2)} ha`
          }
        }
      },
      cutout: '65%',
    }
  });
}

/* =====================================================
   Graphique Barres (Évolution constructions par année)
   ===================================================== */
function createBarChart(canvasId, labels, data, color) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;
  return new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        label: 'Constructions',
        data,
        backgroundColor: color || '#1E3A8A',
        borderRadius: 6,
        borderSkipped: false,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        y: { beginAtZero: true, ticks: { stepSize: 1 }, grid: { color: '#f1f5f9' } },
        x: { grid: { display: false } }
      }
    }
  });
}
