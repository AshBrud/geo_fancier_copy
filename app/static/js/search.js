/* ==============================================================================
   GéoFoncier NGOGOM_UAD — Recherche en Temps Réel & Autocomplete (search.js)
   Saisie avec debounce, requête AJAX /navigation/ajax/, rendu catégorisé
   ============================================================================== */

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
