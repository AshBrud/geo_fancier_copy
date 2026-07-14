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

  const map = L.map(containerId, {
    zoomControl: false,
    maxZoom: options.maxZoom || 28,
  }).setView(defaultCenter, defaultZoom);

  L.control.zoom({ position: 'bottomright' }).addTo(map);

  // Pane dédié aux orthophotos : au-dessus du fond de carte, sous les vecteurs
  map.createPane('orthophotoPane');
  map.getPane('orthophotoPane').style.zIndex = 250;

  const osm = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    maxZoom: 28,
    maxNativeZoom: 19
  });

  const satellite = L.tileLayer(
    'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
    attribution: 'Tiles &copy; Esri &mdash; Source: Esri, USGS, NOAA',
    maxZoom: 28,
    maxNativeZoom: 19
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

  /* invalidateSize robuste : double requestAnimationFrame + fallback 400ms
     Corrige le décalage de tuiles quand Leaflet s'init avant que Bootstrap
     ait calculé la largeur des colonnes (col-lg-X). */
  requestAnimationFrame(function () {
    requestAnimationFrame(function () {
      map.invalidateSize();
    });
  });
  setTimeout(function () { map.invalidateSize(); }, 400);

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
   Charger l'orthophoto la plus récente comme carte
   interactive principale (opacité 100%, vue calée sur
   son emprise via tiles.json WebODM).
   ===================================================== */
function loadPriorityOrthophoto(map, opts) {
  opts = opts || {};
  var fit = opts.fit !== false;
  return fetch('/api/orthophotos/')
    .then(r => r.json())
    .then(data => {
      if (!data.length) return null;
      var m = data[0];
      var layer = loadOrthophoto(map, m.tiles_url, { opacity: 1 });
      layer.addTo(map);

      if (fit) {
        var tilesJsonUrl = m.tiles_url.split('/tiles/')[0] + '/tiles.json';
        fetch(tilesJsonUrl)
          .then(r => r.json())
          .then(meta => {
            if (meta.bounds && meta.bounds.length === 4) {
              var b = meta.bounds;
              map.fitBounds([[b[1], b[0]], [b[3], b[2]]], { maxZoom: 21 });
            }
          })
          .catch(function () { /* pas grave, on garde la vue par défaut */ });
      }

      return layer;
    })
    .catch(function () {
      console.warn('Orthophoto prioritaire non chargée.');
      return null;
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

function loadTerrains(map, layerGroup) {
  layerGroup = layerGroup || L.layerGroup().addTo(map);
  fetch('/api/terrains/')
    .then(r => r.json())
    .then(data => {
      layerGroup.clearLayers();
      L.geoJSON(data, {
        style: {
          fillColor: '#A16207',
          color: '#fff',
          weight: 1.5,
          fillOpacity: 0.5,
        },
        onEachFeature: function (feature, layer) {
          const p = feature.properties;
          layer.bindPopup(
            `<strong>${p.nom}</strong><br>
             Type: ${p.type_terrain || 'N/A'}<br>
             État: ${p.etat || 'N/A'}<br>
             Superficie: ${p.superficie ? (p.superficie / 10000).toFixed(2) + ' ha' : 'N/A'}`
          );
        }
      }).addTo(layerGroup);
    })
    .catch(err => console.warn('Terrains non chargés:', err));
  return layerGroup;
}

function loadEspacesVerts(map, layerGroup) {
  layerGroup = layerGroup || L.layerGroup().addTo(map);
  fetch('/api/espaces-verts/')
    .then(r => r.json())
    .then(data => {
      layerGroup.clearLayers();
      L.geoJSON(data, {
        style: {
          fillOpacity: 0,
          color: '#22C55E',
          weight: 2,
        },
        onEachFeature: function (feature, layer) {
          const p = feature.properties;
          layer.bindPopup(
            `<strong>${p.nom}</strong><br>
             Type: ${p.type_espace_vert || 'N/A'}<br>
             État: ${p.etat || 'N/A'}<br>
             Superficie: ${p.superficie ? (p.superficie / 10000).toFixed(2) + ' ha' : 'N/A'}`
          );
        }
      }).addTo(layerGroup);
    })
    .catch(err => console.warn('Espaces verts non chargés:', err));
  return layerGroup;
}

function loadVoiries(map, layerGroup) {
  layerGroup = layerGroup || L.layerGroup().addTo(map);
  fetch('/api/voiries/')
    .then(r => r.json())
    .then(data => {
      layerGroup.clearLayers();
      L.geoJSON(data, {
        style: {
          color: '#6B7280',
          weight: 3,
        },
        onEachFeature: function (feature, layer) {
          const p = feature.properties;
          layer.bindPopup(
            `<strong>${p.nom}</strong><br>
             Type: ${p.type_voirie || 'N/A'}<br>
             Revêtement: ${p.revetement || 'N/A'}<br>
             État: ${p.etat || 'N/A'}<br>
             Longueur: ${p.longueur ? p.longueur.toFixed(0) + ' m' : 'N/A'}`
          );
        }
      }).addTo(layerGroup);
    })
    .catch(err => console.warn('Voiries non chargées:', err));
  return layerGroup;
}

function loadPointsInteret(map, layerGroup) {
  layerGroup = layerGroup || L.layerGroup().addTo(map);
  fetch('/api/points-interet/')
    .then(r => r.json())
    .then(data => {
      layerGroup.clearLayers();
      L.geoJSON(data, {
        pointToLayer: function (feature, latlng) {
          return L.circleMarker(latlng, {
            radius: 7,
            fillColor: '#DB2777',
            color: '#fff',
            weight: 2,
            fillOpacity: 0.9,
          });
        },
        onEachFeature: function (feature, layer) {
          const p = feature.properties;
          layer.bindPopup(
            `<strong>${p.nom}</strong><br>
             Catégorie: ${p.categorie || 'N/A'}`
          );
        }
      }).addTo(layerGroup);
    })
    .catch(err => console.warn('Points d\'intérêt non chargés:', err));
  return layerGroup;
}

/* =====================================================
   Recherche en temps réel (autocomplete)
   ===================================================== */
function initSearchAutocomplete(inputId, resultsId) {
  const input   = document.getElementById(inputId);
  const results = document.getElementById(resultsId);
  if (!input || !results) return;

  const hide = () => results.classList.remove('show');
  const show = () => results.classList.add('show');

  let timer;
  input.addEventListener('input', function () {
    clearTimeout(timer);
    const q = this.value.trim();
    if (q.length < 2) { results.innerHTML = ''; hide(); return; }

    timer = setTimeout(function () {
      fetch('/navigation/ajax/?q=' + encodeURIComponent(q))
        .then(r => r.json())
        .then(data => {
          if (!data.resultats.length) {
            results.innerHTML =
              '<div style="padding:14px 16px;text-align:center;color:#94a3b8;font-size:13px;">' +
              '<i class="bi bi-search me-1"></i>Aucun résultat pour « ' + q + ' »</div>';
          } else {
            const bats = data.resultats.filter(r => r.type === 'batiment');
            const esps = data.resultats.filter(r => r.type === 'espace');
            let html = '';

            const itemStyle = 'display:flex;align-items:center;gap:10px;padding:9px 14px;color:#1e293b;text-decoration:none;font-size:13px;border-bottom:1px solid #f8fafc;';

            if (bats.length) {
              html += '<div style="padding:6px 14px 3px;font-size:10.5px;font-weight:700;text-transform:uppercase;letter-spacing:.7px;color:#94a3b8;background:#f8fafc;border-bottom:1px solid #f1f5f9;">Bâtiments</div>';
              html += bats.map(r =>
                `<a href="${r.url || '#'}" style="${itemStyle}" class="ac-item"
                    data-lat="${r.lat}" data-lng="${r.lng}" data-nom="${r.nom}">
                  <div style="width:32px;height:32px;border-radius:8px;background:#eff6ff;display:flex;align-items:center;justify-content:center;flex-shrink:0;">
                    <i class="bi bi-building" style="color:#1E3A8A;font-size:14px;"></i>
                  </div>
                  <div style="flex:1;min-width:0;">
                    <div style="font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${r.nom}</div>
                    <div style="font-size:11px;color:#94a3b8;">${r.code}${r.fonction ? ' · ' + r.fonction : ''}${r.superficie ? ' · ' + Number(r.superficie).toLocaleString('fr') + ' m²' : ''}</div>
                  </div>
                  <i class="bi bi-arrow-right" style="color:#cbd5e1;font-size:11px;flex-shrink:0;"></i>
                </a>`
              ).join('');
            }

            if (esps.length) {
              html += '<div style="padding:6px 14px 3px;font-size:10.5px;font-weight:700;text-transform:uppercase;letter-spacing:.7px;color:#94a3b8;background:#f8fafc;border-bottom:1px solid #f1f5f9;' + (bats.length ? 'border-top:1px solid #f1f5f9;' : '') + '">Espaces fonciers</div>';
              html += esps.map(r =>
                `<a href="${r.url || '#'}" style="${itemStyle}border-bottom:none;" class="ac-item"
                    data-lat="${r.lat}" data-lng="${r.lng}" data-nom="${r.nom}">
                  <div style="width:32px;height:32px;border-radius:8px;background:${r.couleur ? r.couleur + '22' : '#f1f5f9'};display:flex;align-items:center;justify-content:center;flex-shrink:0;">
                    <i class="bi bi-grid-3x3-gap" style="color:${r.couleur || '#6b7280'};font-size:14px;"></i>
                  </div>
                  <div style="flex:1;min-width:0;">
                    <div style="font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${r.nom}</div>
                    <div style="font-size:11px;color:#94a3b8;">${r.code}${r.superficie ? ' · ' + Number(r.superficie).toLocaleString('fr') + ' m²' : ''}</div>
                  </div>
                  <i class="bi bi-arrow-right" style="color:#cbd5e1;font-size:11px;flex-shrink:0;"></i>
                </a>`
              ).join('');
            }

            results.innerHTML = html;
            results.querySelectorAll('.ac-item').forEach(function(el) {
              el.addEventListener('mouseover', function() { this.style.background = '#f8fafc'; });
              el.addEventListener('mouseout',  function() { this.style.background = ''; });
            });
          }
          show();
        })
        .catch(() => { results.innerHTML = ''; hide(); });
    }, 280);
  });

  document.addEventListener('click', function (e) {
    if (!results.contains(e.target) && e.target !== input) hide();
  });

  input.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') { hide(); this.blur(); }
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
