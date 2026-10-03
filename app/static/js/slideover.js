/**
 * SLIDEOVER DRAWER CONTROLLER
 * Moteur d'inspection latérale sans rechargement de page pour GéoFoncier V2.
 */

(function (window) {
  'use strict';

  let backdrop = null;
  let drawer = null;
  let titleEl = null;
  let badgeEl = null;
  let bodyEl = null;
  let footerEl = null;
  let closeBtn = null;
  let activeRow = null;
  let currentOnClose = null;

  function initDOM() {
    if (backdrop) return;

    backdrop = document.getElementById('global-slideover-backdrop');
    if (!backdrop) {
      backdrop = document.createElement('div');
      backdrop.id = 'global-slideover-backdrop';
      backdrop.className = 'slideover-backdrop';
      backdrop.innerHTML = `
        <div class="slideover-drawer" role="dialog" aria-modal="true">
          <div class="slideover-header">
            <div class="slideover-title-group">
              <h3 class="slideover-title" id="slideover-title">Détails</h3>
              <span id="slideover-badge"></span>
            </div>
            <button type="button" class="slideover-close-btn" id="slideover-close" aria-label="Fermer">
              <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <line x1="18" y1="6" x2="6" y2="18"></line>
                <line x1="6" y1="6" x2="18" y2="18"></line>
              </svg>
            </button>
          </div>
          <div class="slideover-body" id="slideover-body"></div>
          <div class="slideover-footer" id="slideover-footer"></div>
        </div>
      `;
      document.body.appendChild(backdrop);
    }

    drawer = backdrop.querySelector('.slideover-drawer');
    titleEl = document.getElementById('slideover-title');
    badgeEl = document.getElementById('slideover-badge');
    bodyEl = document.getElementById('slideover-body');
    footerEl = document.getElementById('slideover-footer');
    closeBtn = document.getElementById('slideover-close');

    // Écouteur fermeture
    closeBtn.addEventListener('click', SlideOver.close);
    backdrop.addEventListener('click', function (e) {
      if (e.target === backdrop) {
        SlideOver.close();
      }
    });

    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && backdrop.classList.contains('active')) {
        SlideOver.close();
      }
    });
  }

  const SlideOver = {
    open: function (options) {
      initDOM();

      const opts = options || {};
      titleEl.textContent = opts.title || 'Détails';

      const badgeContent = opts.badgeHtml || opts.badge;
      if (badgeContent) {
        badgeEl.innerHTML = badgeContent;
        badgeEl.style.display = 'inline-block';
      } else {
        badgeEl.innerHTML = '';
        badgeEl.style.display = 'none';
      }

      const bodyContent = opts.bodyHtml || opts.body;
      bodyEl.innerHTML = bodyContent || '<p class="text-muted">Aucun détail disponible.</p>';

      const footerContent = opts.footerHtml || opts.footer;
      if (footerContent) {
        footerEl.innerHTML = footerContent;
        footerEl.style.display = 'flex';
      } else {
        footerEl.innerHTML = '';
        footerEl.style.display = 'none';
      }

      currentOnClose = opts.onClose || null;

      // Gestion de la sélection visuelle de ligne
      if (opts.triggerRow) {
        if (activeRow) activeRow.classList.remove('selected');
        activeRow = opts.triggerRow;
        activeRow.classList.add('selected');
      }

      // Affichage fluide
      requestAnimationFrame(() => {
        backdrop.classList.add('active');
        document.body.style.overflow = 'hidden';
      });

      if (typeof opts.onOpen === 'function') {
        opts.onOpen(bodyEl);
      }
    },

    close: function () {
      if (!backdrop || !backdrop.classList.contains('active')) return;

      backdrop.classList.remove('active');
      document.body.style.overflow = '';

      if (activeRow) {
        activeRow.classList.remove('selected');
        activeRow = null;
      }

      if (typeof currentOnClose === 'function') {
        currentOnClose();
        currentOnClose = null;
      }
    },

    /**
     * Attache automatiquement le SlideOver à un tableau de données cliquable.
     * @param {string} selector Sélecteur CSS du tableau (ex: '#table-constructions')
     * @param {Function} dataResolver Callback appelée avec la ligne (tr) qui renvoie { title, badgeHtml, bodyHtml, footerHtml }
     */
    bindTable: function (selector, dataResolver) {
      initDOM();
      const table = document.querySelector(selector);
      if (!table) return;

      table.addEventListener('click', function (e) {
        // Ignorer si le clic provient d'un bouton ou d'un lien d'action direct
        if (e.target.closest('button, a, input, select')) return;

        const row = e.target.closest('.table-row-clickable');
        if (!row) return;

        const data = dataResolver(row);
        if (data) {
          data.triggerRow = row;
          SlideOver.open(data);
        }
      });
    }
  };

  window.SlideOver = SlideOver;

  // Auto-init au chargement du DOM
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initDOM);
  } else {
    initDOM();
  }

})(window);
