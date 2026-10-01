/* ==============================================================================
   GéoFoncier NGOGOM_UAD — Couches Vectorielles SIG (layers.js)
   Chargement des API GeoJSON : Espaces, Bâtiments, Terrains, Espaces verts,
   Voiries et Points d'intérêt avec popups GPS
   ============================================================================== */

/* =====================================================
   Formatage des coordonnées GPS
   ===================================================== */
function formatCoords(latlng) {
  return `<span style="font-family:monospace;font-size:11px;color:#64748b;">`
    + `GPS : ${latlng.lat.toFixed(6)}, ${latlng.lng.toFixed(6)}</span>`;
}

/* =====================================================
   Charger les Espaces fonciers (libres, occupés, réservés)
   ===================================================== */
function loadEspaces(map, layerGroup, options) {
  options = options || {};
  layerGroup = layerGroup || L.layerGroup().addTo(map);
  const url = '/api/espaces/' + (options.type ? '?type=' + encodeURIComponent(options.type) : '');
  fetch(url)
    .then(r => r.json())
    .then(data => {
      layerGroup.clearLayers();
      L.geoJSON(data, {
        style: function (feature) {
          if (feature.properties.type_espace === 'libre') {
            return {
              fillOpacity: 0,
              color:       feature.properties.couleur || '#16A34A',
              weight:      2,
            };
          }
          return {
            fillColor:   feature.properties.couleur || '#6b7280',
            color:       '#fff',
            weight:      1.5,
            fillOpacity: 0.55,
          };
        },
        onEachFeature: function (feature, layer) {
          const p = feature.properties;
          const sup_batie = p.superficie_batie || 0;
          const sup_dispo = Math.max(0, (p.superficie || 0) - sup_batie);
          const batieLigne = p.type_espace === 'libre'
            ? `<br>Bâti: ${sup_batie.toFixed(0)} m² · Disponible: ${sup_dispo.toFixed(0)} m²`
            : '';
          const descLigne = p.description ? `<br>${p.description}` : '';
          layer.bindPopup('');
          layer.on('click', function (e) {
            layer.setPopupContent(
              `<strong>${p.nom}</strong><br>
               Code: ${p.code}<br>
               Type: ${p.type_display}<br>
               Superficie: ${p.superficie ? (p.superficie / 10000).toFixed(2) + ' ha' : 'N/A'}${batieLigne}${descLigne}
               <br>${formatCoords(e.latlng)}`
            );
          });
        }
      }).addTo(layerGroup);
    })
    .catch(err => console.warn('Espaces non chargés:', err));
  return layerGroup;
}

/* =====================================================
   Charger les Bâtiments
   ===================================================== */
function loadBatiments(map, layerGroup) {
  layerGroup = layerGroup || L.layerGroup().addTo(map);
  fetch('/api/batiments/')
    .then(r => r.json())
    .then(data => {
      layerGroup.clearLayers();
      L.geoJSON(data, {
        style: {
          fillOpacity: 0,
          color: '#78350F',
          weight: 1.5,
        },
        onEachFeature: function (feature, layer) {
          const p = feature.properties;
          layer.bindTooltip(p.nom, {
            permanent: true, direction: 'center', className: 'batiment-label',
          });
          layer.bindPopup('');
          layer.on('click', function (e) {
            layer.setPopupContent(
              `<strong>${p.nom}</strong><br>
               Code: ${p.code}<br>
               Fonction: ${p.fonction_nom || 'N/A'}<br>
               Étages: ${p.etages}<br>
               Superficie: ${p.superficie ? p.superficie.toFixed(0) + ' m²' : 'N/A'}
               ${p.description ? '<br>' + p.description : ''}
               <br>${formatCoords(e.latlng)}`
            );
          });
        }
      }).addTo(layerGroup);
    })
    .catch(err => console.warn('Bâtiments non chargés:', err));
  return layerGroup;
}

/* =====================================================
   Charger les Terrains
   ===================================================== */
function loadTerrains(map, layerGroup, options) {
  options = options || {};
  layerGroup = layerGroup || L.layerGroup().addTo(map);
  const url = '/api/terrains/' + (options.sport !== undefined ? '?sport=' + (options.sport ? '1' : '0') : '');
  const fillColor = options.sport ? '#F97316' : '#2563EB';
  fetch(url)
    .then(r => r.json())
    .then(data => {
      layerGroup.clearLayers();
      L.geoJSON(data, {
        style: {
          fillColor: fillColor,
          color: '#fff',
          weight: 1.5,
          fillOpacity: 0.5,
        },
        onEachFeature: function (feature, layer) {
          const p = feature.properties;
          layer.bindPopup('');
          layer.on('click', function (e) {
            layer.setPopupContent(
              `<strong>${p.nom}</strong><br>
               Type: ${p.type_terrain || 'N/A'}<br>
               État: ${p.etat || 'N/A'}<br>
               Superficie: ${p.superficie ? (p.superficie / 10000).toFixed(2) + ' ha' : 'N/A'}
               ${p.observation ? '<br>' + p.observation : ''}
               <br>${formatCoords(e.latlng)}`
            );
          });
        }
      }).addTo(layerGroup);
    })
    .catch(err => console.warn('Terrains non chargés:', err));
  return layerGroup;
}

/* =====================================================
   Charger les Espaces verts
   ===================================================== */
function loadEspacesVerts(map, layerGroup) {
  layerGroup = layerGroup || L.layerGroup().addTo(map);
  fetch('/api/espaces-verts/')
    .then(r => r.json())
    .then(data => {
      layerGroup.clearLayers();
      L.geoJSON(data, {
        style: {
          fillColor: '#22C55E',
          color: '#fff',
          weight: 1.5,
          fillOpacity: 0.6,
        },
        onEachFeature: function (feature, layer) {
          const p = feature.properties;
          layer.bindPopup('');
          layer.on('click', function (e) {
            layer.setPopupContent(
              `<strong>${p.nom}</strong><br>
               Type: ${p.type_espace_vert || 'N/A'}<br>
               État: ${p.etat || 'N/A'}<br>
               Superficie: ${p.superficie ? (p.superficie / 10000).toFixed(2) + ' ha' : 'N/A'}
               ${p.observation ? '<br>' + p.observation : ''}
               <br>${formatCoords(e.latlng)}`
            );
          });
        }
      }).addTo(layerGroup);
    })
    .catch(err => console.warn('Espaces verts non chargés:', err));
  return layerGroup;
}

/* =====================================================
   Charger les Voiries
   ===================================================== */
function loadVoiries(map, layerGroup) {
  layerGroup = layerGroup || L.layerGroup().addTo(map);
  fetch('/api/voiries/')
    .then(r => r.json())
    .then(data => {
      layerGroup.clearLayers();
      L.geoJSON(data, {
        style: {
          color: '#A16207',
          weight: 3,
        },
        onEachFeature: function (feature, layer) {
          const p = feature.properties;
          layer.bindPopup('');
          layer.on('click', function (e) {
            layer.setPopupContent(
              `<strong>${p.nom}</strong><br>
               Type: ${p.type_voirie || 'N/A'}<br>
               Revêtement: ${p.revetement || 'N/A'}<br>
               État: ${p.etat || 'N/A'}<br>
               Longueur: ${p.longueur ? p.longueur.toFixed(0) + ' m' : 'N/A'}
               ${p.observation ? '<br>' + p.observation : ''}
               <br>${formatCoords(e.latlng)}`
            );
          });
        }
      }).addTo(layerGroup);
    })
    .catch(err => console.warn('Voiries non chargées:', err));
  return layerGroup;
}

/* =====================================================
   Charger les Points d'intérêt
   ===================================================== */
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
