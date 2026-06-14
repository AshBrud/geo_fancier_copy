/* GéoFoncier UAD — Scripts principaux */

document.addEventListener('DOMContentLoaded', function () {

  // --- Sidebar toggle ---
  const sidebar      = document.getElementById('sidebar');
  const mainWrapper  = document.getElementById('mainWrapper');
  const toggleBtn    = document.getElementById('sidebarToggle');

  // Overlay mobile
  let overlay = document.createElement('div');
  overlay.className = 'sidebar-overlay';
  document.body.appendChild(overlay);

  if (toggleBtn) {
    toggleBtn.addEventListener('click', function () {
      if (window.innerWidth <= 992) {
        sidebar.classList.toggle('mobile-open');
        overlay.classList.toggle('show');
      } else {
        sidebar.classList.toggle('collapsed');
        mainWrapper.classList.toggle('expanded');
        localStorage.setItem('sidebarCollapsed', sidebar.classList.contains('collapsed'));
      }
    });
  }

  overlay.addEventListener('click', function () {
    sidebar.classList.remove('mobile-open');
    overlay.classList.remove('show');
  });

  // Restaurer l'état de la sidebar
  if (localStorage.getItem('sidebarCollapsed') === 'true' && window.innerWidth > 992) {
    sidebar && sidebar.classList.add('collapsed');
    mainWrapper && mainWrapper.classList.add('expanded');
  }

  // --- Auto-dismiss alertes ---
  document.querySelectorAll('.alert:not(.alert-permanent)').forEach(function (alert) {
    setTimeout(function () {
      const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
      if (bsAlert) bsAlert.close();
    }, 5000);
  });

  // --- Confirmation de suppression ---
  document.querySelectorAll('[data-confirm]').forEach(function (btn) {
    btn.addEventListener('click', function (e) {
      if (!confirm(this.dataset.confirm || 'Confirmer cette action ?')) {
        e.preventDefault();
      }
    });
  });

  // --- Tooltips Bootstrap ---
  document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(function (el) {
    new bootstrap.Tooltip(el);
  });
});

/* =====================================================
   Initialisation carte Leaflet
   ===================================================== */
function initCampusMap(containerId, options) {
  options = options || {};

  const defaultCenter = options.center || [14.696291168874254, -16.477368387258974];
  const defaultZoom   = options.zoom   || 17;

  const map = L.map(containerId, { zoomControl: false }).setView(defaultCenter, defaultZoom);

  L.control.zoom({ position: 'bottomright' }).addTo(map);

  // Pane dédié aux orthophotos : au-dessus du fond de carte, sous les vecteurs
  map.createPane('orthophotoPane');
  map.getPane('orthophotoPane').style.zIndex = 250;

  const osm = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    maxZoom: 22
  });

  const satellite = L.tileLayer(
    'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
    attribution: 'Tiles © Esri — Source: Esri, USGS, NOAA',
    maxZoom: 22
  });

  osm.addTo(map);

  // Référence aux fonds de carte pour le panneau custom
  map._baseLayers = { osm: osm, satellite: satellite };
  map._activeBase = 'osm';

  if (!options.hideLayerControl) {
    L.control.layers(
      { 'Plan (OSM)': osm, 'Satellite': satellite },
      {},
      { position: 'topright', collapsed: true }
    ).addTo(map);
  }

  L.control.scale({ imperial: false }).addTo(map);

  return map;
}

/* =====================================================
   Charger une orthophoto en tuiles XYZ (WebODM / QGIS)
   ===================================================== */
function loadOrthophoto(map, tilesUrl, opts) {
  opts = opts || {};
  return L.tileLayer(tilesUrl, {
    pane: 'orthophotoPane',
    opacity: opts.opacity !== undefined ? opts.opacity : 0.85,
    maxZoom: opts.maxZoom || 22,
    maxNativeZoom: opts.maxNativeZoom || 20,
    tms: opts.tms || false,
    attribution: 'Orthophoto GéoFoncier UAD — WebODM/QGIS',
  });
}

/* =====================================================
   Charger les couches GeoJSON depuis l'API
   ===================================================== */
function loadEspaces(map, layerGroup) {
  layerGroup = layerGroup || L.layerGroup().addTo(map);
  fetch('/api/espaces/')
    .then(r => r.json())
    .then(data => {
      layerGroup.clearLayers();
      L.geoJSON(data, {
        style: function (feature) {
          return {
            fillColor:   feature.properties.couleur || '#6b7280',
            color:       '#fff',
            weight:      1.5,
            fillOpacity: 0.55,
          };
        },
        onEachFeature: function (feature, layer) {
          const p = feature.properties;
          layer.bindPopup(
            `<strong>${p.nom}</strong><br>
             Code: ${p.code}<br>
             Type: ${p.type_display}<br>
             Superficie: ${p.superficie ? (p.superficie / 10000).toFixed(2) + ' ha' : 'N/A'}`
          );
        }
      }).addTo(layerGroup);
    })
    .catch(err => console.warn('Espaces non chargés:', err));
  return layerGroup;
}

function loadBatiments(map, layerGroup) {
  layerGroup = layerGroup || L.layerGroup().addTo(map);
  fetch('/api/batiments/')
    .then(r => r.json())
    .then(data => {
      layerGroup.clearLayers();
      L.geoJSON(data, {
        style: {
          fillColor: '#1E3A8A',
          color: '#fff',
          weight: 1.5,
          fillOpacity: 0.7,
        },
        onEachFeature: function (feature, layer) {
          const p = feature.properties;
          layer.bindPopup(
            `<strong>${p.nom}</strong><br>
             Code: ${p.code}<br>
             Fonction: ${p.fonction_nom || 'N/A'}<br>
             Étages: ${p.etages}<br>
             Superficie: ${p.superficie ? p.superficie.toFixed(0) + ' m²' : 'N/A'}`
          );
        }
      }).addTo(layerGroup);
    })
    .catch(err => console.warn('Bâtiments non chargés:', err));
  return layerGroup;
}

/* =====================================================
   Recherche en temps réel (autocomplete)
   ===================================================== */
function initSearchAutocomplete(inputId, resultsId) {
  const input   = document.getElementById(inputId);
  const results = document.getElementById(resultsId);
  if (!input || !results) return;

  let timer;
  input.addEventListener('input', function () {
    clearTimeout(timer);
    const q = this.value.trim();
    if (q.length < 2) { results.innerHTML = ''; results.classList.add('d-none'); return; }
    timer = setTimeout(function () {
      fetch('/navigation/ajax/?q=' + encodeURIComponent(q))
        .then(r => r.json())
        .then(data => {
          if (!data.resultats.length) {
            results.innerHTML = '<div class="p-3 text-muted text-center">Aucun résultat</div>';
          } else {
            results.innerHTML = data.resultats.map(r =>
              `<a href="#" class="search-result-item"
                  data-lat="${r.lat}" data-lng="${r.lng}" data-nom="${r.nom}">
                <div class="search-icon ${r.type === 'batiment' ? 'bg-primary bg-opacity-10 text-primary' : 'bg-success bg-opacity-10 text-success'}">
                  <i class="bi bi-${r.type === 'batiment' ? 'building' : 'grid-3x3-gap'}"></i>
                </div>
                <div>
                  <div class="fw-semibold">${r.nom}</div>
                  <small class="text-muted">${r.code} · ${r.type === 'batiment' ? (r.fonction || 'Bâtiment') : r.type_espace || 'Espace'}</small>
                </div>
              </a>`
            ).join('');
          }
          results.classList.remove('d-none');
        })
        .catch(() => { results.innerHTML = ''; });
    }, 300);
  });

  document.addEventListener('click', function (e) {
    if (!results.contains(e.target) && e.target !== input) {
      results.classList.add('d-none');
    }
  });
}

/* =====================================================
   Graphiques Chart.js — helpers
   ===================================================== */
function createDonutChart(canvasId, labels, data, colors) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;
  return new Chart(ctx, {
    type: 'doughnut',
    data: { labels, datasets: [{ data, backgroundColor: colors, borderWidth: 2, borderColor: '#fff' }] },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: 'bottom', labels: { padding: 16, font: { family: 'Poppins', size: 12 } } },
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
