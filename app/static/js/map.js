/* ==============================================================================
   GéoFoncier NGOGOM_UAD — Moteur Cartographique Leaflet (map.js)
   Initialisation de la carte, fonds OSM/Esri, panes et orthophotos
   ============================================================================== */

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

  // Les serveurs OSM refusent (403 « Access blocked ») les tuiles demandées sans
  // en-tête Referer ; or Django impose « Referrer-Policy: same-origin » à toutes
  // les pages. On rétablit donc l'envoi de l'origine pour cette seule couche.
  const osm = L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    referrerPolicy: 'strict-origin-when-cross-origin',
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

  // options.base = 'satellite' : fond image par défaut (cartes communales rurales)
  const base = options.base === 'satellite' ? 'satellite' : 'osm';
  (base === 'satellite' ? satellite : osm).addTo(map);

  // Référence aux fonds de carte pour le panneau custom
  map._baseLayers = { osm: osm, satellite: satellite };
  map._activeBase = base;

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
    attribution: 'Orthophoto GéoFoncier NGOGOM_UAD — WebODM/QGIS',
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

// Alias canoniques V2 pour la compatibilité cartographique tous territoires
window.initTerritoireMap = initCampusMap;
window.initGeoMap = initCampusMap;
