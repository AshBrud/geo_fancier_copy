/* ==============================================================================
   GéoFoncier V2 — Sélecteur Cartographique Immersif Plein Écran (map_picker.js)
   Tracé vectoriel interactif, calcul de surface métrique en direct et
   validation explicite GeoJSON vers les formulaires modaux.
   ============================================================================== */

window.MapPicker = (function () {
  'use strict';

  let map = null;
  let drawnItems = null;
  let drawControl = null;
  let currentGeoJson = null;
  let currentAreaM2 = 0;
  let currentCentroid = null;
  let activeOptions = {};
  let isInitialized = false;

  // Calcul d'aire géodésique sphérique WGS84 en m²
  function computePolygonArea(latLngs) {
    if (!latLngs || latLngs.length < 3) return 0;
    if (Array.isArray(latLngs[0]) && latLngs[0].length >= 3) {
      latLngs = latLngs[0];
    }
    const R = 6378137;
    let area = 0;
    const len = latLngs.length;
    for (let i = 0; i < len; i++) {
      const p1 = latLngs[i];
      const p2 = latLngs[(i + 1) % len];
      const rad1 = (p1.lat * Math.PI) / 180;
      const rad2 = (p2.lat * Math.PI) / 180;
      const dLng = ((p2.lng - p1.lng) * Math.PI) / 180;
      area += dLng * (2 + Math.sin(rad1) + Math.sin(rad2));
    }
    return Math.abs((area * R * R) / 2.0);
  }

  // Calcul du centroïde moyen
  function computeCentroid(latLngs) {
    if (!latLngs || latLngs.length === 0) return { lat: 0, lng: 0 };
    if (Array.isArray(latLngs[0])) latLngs = latLngs[0];
    let latSum = 0, lngSum = 0;
    latLngs.forEach(p => {
      latSum += p.lat;
      lngSum += p.lng;
    });
    return {
      lat: latSum / latLngs.length,
      lng: lngSum / latLngs.length
    };
  }

  function initMap() {
    if (isInitialized) return;
    const canvas = document.getElementById('map-picker-canvas');
    if (!canvas) return;

    map = L.map('map-picker-canvas', {
      zoomControl: false,
      maxZoom: 28
    }).setView([14.6963, -16.4774], 16);

    L.control.zoom({ position: 'bottomright' }).addTo(map);

    const osm = L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      referrerPolicy: 'strict-origin-when-cross-origin',
      attribution: '&copy; OpenStreetMap',
      maxZoom: 28,
      maxNativeZoom: 19
    }).addTo(map);

    const satellite = L.tileLayer(
      'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
      attribution: 'Tiles &copy; Esri',
      maxZoom: 28,
      maxNativeZoom: 19
    });

    L.control.layers(
      { 'Plan OSM': osm, 'Satellite': satellite },
      {},
      { position: 'topright', collapsed: true }
    ).addTo(map);

    drawnItems = new L.FeatureGroup().addTo(map);

    drawControl = new L.Control.Draw({
      position: 'topleft',
      draw: {
        polygon: {
          allowIntersection: false,
          showArea: true,
          shapeOptions: {
            color: '#0f172a',
            fillColor: '#1e3a8a',
            fillOpacity: 0.45,
            weight: 3
          }
        },
        rectangle: {
          shapeOptions: {
            color: '#0f172a',
            fillColor: '#1e3a8a',
            fillOpacity: 0.45,
            weight: 3
          }
        },
        polyline: false,
        circle: false,
        marker: false,
        circlemarker: false
      },
      edit: {
        featureGroup: drawnItems,
        remove: true
      }
    });
    map.addControl(drawControl);

    // Événement : Nouveau tracé
    map.on(L.Draw.Event.CREATED, function (e) {
      drawnItems.clearLayers();
      const layer = e.layer;
      drawnItems.addLayer(layer);
      updateFromLayer(layer);
    });

    // Événement : Sommets édités
    map.on(L.Draw.Event.EDITED, function (e) {
      const layers = e.layers;
      layers.eachLayer(function (layer) {
        updateFromLayer(layer);
      });
    });

    // Événement : Tracé supprimé
    map.on(L.Draw.Event.DELETED, function () {
      resetConfirmationCard();
    });

    // Recherche d'adresse
    const searchBtn = document.getElementById('mapPickerSearchBtn');
    const searchInput = document.getElementById('mapPickerSearchInput');
    if (searchBtn && searchInput) {
      searchBtn.addEventListener('click', performSearch);
      searchInput.addEventListener('keydown', function (e) {
        if (e.key === 'Enter') {
          e.preventDefault();
          performSearch();
        }
      });
    }

    // Boutons de confirmation et d'annulation
    const confirmBtn = document.getElementById('mapPickerConfirmBtn');
    const cancelBtn = document.getElementById('mapPickerCancelBtn');
    if (confirmBtn) confirmBtn.addEventListener('click', confirmSelection);
    if (cancelBtn) cancelBtn.addEventListener('click', close);

    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') {
        const overlay = document.getElementById('mapPickerOverlay');
        if (overlay && overlay.classList.contains('is-active')) {
          close();
        }
      }
    });

    isInitialized = true;
  }

  function updateFromLayer(layer) {
    const latLngs = layer.getLatLngs();
    currentAreaM2 = computePolygonArea(latLngs);
    currentCentroid = computeCentroid(latLngs);
    currentGeoJson = layer.toGeoJSON().geometry;

    const titleEl = document.getElementById('mapPickerTitle');
    const coordsEl = document.getElementById('mapPickerCoords');
    const confirmBtn = document.getElementById('mapPickerConfirmBtn');

    if (titleEl) {
      const ha = (currentAreaM2 / 10000).toFixed(4);
      const m2Formatted = Math.round(currentAreaM2).toLocaleString('fr-FR');
      titleEl.innerHTML = `<strong>${m2Formatted} m²</strong> <span class="text-muted fw-normal">(${ha} ha)</span>`;
    }

    if (coordsEl && currentCentroid) {
      coordsEl.textContent = `${currentCentroid.lat.toFixed(6)}, ${currentCentroid.lng.toFixed(6)}`;
    }

    if (confirmBtn) {
      confirmBtn.disabled = false;
    }
  }

  function resetConfirmationCard() {
    currentGeoJson = null;
    currentAreaM2 = 0;
    currentCentroid = null;

    const titleEl = document.getElementById('mapPickerTitle');
    const coordsEl = document.getElementById('mapPickerCoords');
    const confirmBtn = document.getElementById('mapPickerConfirmBtn');

    if (titleEl) titleEl.textContent = "Tracez un polygone avec l'outil à gauche";
    if (coordsEl) coordsEl.textContent = "--.------, --.------";
    if (confirmBtn) confirmBtn.disabled = true;
  }

  function performSearch() {
    const input = document.getElementById('mapPickerSearchInput');
    if (!input || !input.value.trim()) return;
    const query = input.value.trim();

    fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query)}&limit=1`)
      .then(r => r.json())
      .then(results => {
        if (results && results.length > 0) {
          const res = results[0];
          const lat = parseFloat(res.lat);
          const lon = parseFloat(res.lon);
          map.setView([lat, lon], 17);
        } else {
          alert('Aucun résultat trouvé pour cette recherche.');
        }
      })
      .catch(() => {
        alert('Erreur lors de la recherche géographique.');
      });
  }

  function confirmSelection() {
    if (!currentGeoJson) return;

    // Mise à jour du champ hidden dans le formulaire parent
    if (activeOptions.targetInputId) {
      const input = document.getElementById(activeOptions.targetInputId);
      if (input) {
        input.value = JSON.stringify(currentGeoJson);
        input.dispatchEvent(new Event('change', { bubbles: true }));
      }
    }

    // Mise à jour du label de statut dans la modale parente
    if (activeOptions.statusElementId) {
      const statusEl = document.getElementById(activeOptions.statusElementId);
      if (statusEl) {
        const m2 = Math.round(currentAreaM2).toLocaleString('fr-FR');
        statusEl.textContent = `✓ Emprise définie (${m2} m²)`;
      }
    }

    // Mise à jour du conteneur widget
    if (activeOptions.widgetElementId) {
      const widget = document.getElementById(activeOptions.widgetElementId);
      if (widget) {
        widget.classList.add('is-defined');
      }
    }

    if (activeOptions.buttonTextElementId) {
      const btnText = document.getElementById(activeOptions.buttonTextElementId);
      if (btnText) btnText.textContent = "Modifier le tracé";
    }

    if (typeof activeOptions.onConfirm === 'function') {
      activeOptions.onConfirm(currentGeoJson, currentAreaM2);
    }

    close();
  }

  function open(opts) {
    activeOptions = opts || {};
    const overlay = document.getElementById('mapPickerOverlay');
    if (!overlay) return;

    overlay.classList.add('is-active');

    // Initialisation carto retardée pour bon calcul de taille
    if (!isInitialized) {
      initMap();
    }

    setTimeout(function () {
      if (map) {
        map.invalidateSize();
      }
    }, 150);

    // Titre / Eyebrow contextuel
    const eyebrowEl = document.getElementById('mapPickerEyebrow');
    if (eyebrowEl && activeOptions.title) {
      eyebrowEl.textContent = activeOptions.title.toUpperCase();
    }

    resetConfirmationCard();
    drawnItems.clearLayers();

    // Pré-chargement d'une géométrie existante (création avec saisie antérieure ou modification)
    let initialGeom = activeOptions.initialGeoJson;
    if (typeof initialGeom === 'string' && initialGeom.trim() !== '') {
      try {
        initialGeom = JSON.parse(initialGeom);
      } catch (e) {
        initialGeom = null;
      }
    }

    if (initialGeom && (initialGeom.type === 'Polygon' || initialGeom.type === 'MultiPolygon')) {
      try {
        const geoLayer = L.geoJSON(initialGeom, {
          style: {
            color: '#0f172a',
            fillColor: '#1e3a8a',
            fillOpacity: 0.45,
            weight: 3
          }
        });

        geoLayer.eachLayer(function (l) {
          drawnItems.addLayer(l);
          updateFromLayer(l);
        });

        const b = drawnItems.getBounds();
        if (b && b.isValid && b.isValid()) {
          setTimeout(function () {
            map.fitBounds(b, { padding: [80, 80], maxZoom: 19 });
          }, 200);
        }
      } catch (err) {
        console.warn('Erreur lors du pré-chargement de la géométrie:', err);
      }
    } else if (activeOptions.territoryBounds) {
      try {
        map.fitBounds(activeOptions.territoryBounds, { padding: [40, 40] });
      } catch (e) {}
    }
  }

  function close() {
    const overlay = document.getElementById('mapPickerOverlay');
    if (overlay) {
      overlay.classList.remove('is-active');
    }
  }

  return {
    init: initMap,
    open: open,
    close: close
  };
})();
