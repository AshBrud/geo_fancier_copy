/**
 * GéoFoncier — FilterManager
 * Contrôleur JavaScript réactif pour barres de filtres (Desktop & Mobile Offcanvas)
 *
 * Fonctionnalités :
 * - Déclenchement automatique et debounce (~400ms) sur le champ de recherche textuelle
 * - Validation immédiate sur touche Entrée et effacement rapide sur Échap / bouton clear
 * - Synchronisation bidirectionnelle instantanée entre le formulaire Desktop et Mobile
 * - Comptage dynamique et mise à jour des badges de filtres actifs
 */

const FilterManager = (function () {
  'use strict';

  let debounceTimer = null;

  /**
   * Calcule le nombre de filtres actifs dans un formulaire
   */
  function countActiveFilters(form) {
    if (!form) return 0;
    let count = 0;
    const elements = form.querySelectorAll('input:not([type="hidden"]), select');
    elements.forEach(function (el) {
      const val = (el.value || '').trim();
      if (val !== '') {
        count++;
      }
    });
    return count;
  }

  /*
   * Met à jour le badge visuel des filtres actifs
   */
  function updateBadges(count) {
    const badges = document.querySelectorAll('.badge-filter-count');
    badges.forEach(function (badge) {
      if (count > 0) {
        badge.textContent = count;
        badge.style.display = 'flex';
      } else {
        badge.style.display = 'none';
      }
    });

    const resetButtons = document.querySelectorAll('.btn-filter-reset');
    resetButtons.forEach(function (btn) {
      btn.style.display = count > 0 ? 'inline-flex' : 'none';
    });
  }

  /**
   * Synchronise les valeurs d'un formulaire source vers un formulaire cible
   */
  function syncForms(sourceForm, targetForm, changedName) {
    if (!sourceForm || !targetForm) return;

    const sourceEl = sourceForm.querySelector(`[name="${changedName}"]`);
    const targetEl = targetForm.querySelector(`[name="${changedName}"]`);

    if (sourceEl && targetEl) {
      targetEl.value = sourceEl.value;
    }
  }

  /**
   * Initialise le contrôleur sur une page donnée
   * @param {Object} options - { desktopFormSelector, mobileFormSelector, debounceMs }
   */
  function init(options) {
    const opts = Object.assign({
      desktopFormSelector: '#filterFormDesktop',
      mobileFormSelector: '#filterFormMobile',
      debounceMs: 400
    }, options);

    const desktopForm = document.querySelector(opts.desktopFormSelector);
    const mobileForm = document.querySelector(opts.mobileFormSelector);

    // Initialisation du comptage au chargement
    const initialCount = countActiveFilters(desktopForm || mobileForm);
    updateBadges(initialCount);

    // Liaison du formulaire Desktop
    if (desktopForm) {
      setupFormListeners(desktopForm, mobileForm, opts.debounceMs);
    }

    // Liaison du formulaire Mobile
    if (mobileForm) {
      setupFormListeners(mobileForm, desktopForm, opts.debounceMs);
    }

    // Gestion des boutons de suppression rapide dans les inputs recherche
    setupSearchClearButtons();
  }

  /**
   * Configure les écouteurs d'événements sur un formulaire
   */
  function setupFormListeners(form, counterpartForm, debounceMs) {
    // Événement sur la frappe (input)
    form.addEventListener('input', function (e) {
      const target = e.target;
      if (!target.name) return;

      // Synchronisation vers l'autre formulaire
      if (counterpartForm) {
        syncForms(form, counterpartForm, target.name);
      }

      // Mise à jour visuelle des badges
      const currentCount = countActiveFilters(form);
      updateBadges(currentCount);

      // Gestion du debounce pour la recherche textuelle
      if (target.type === 'text' || target.type === 'search') {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(function () {
          form.submit();
        }, debounceMs);
      }
    });

    // Événement sur le changement de sélection (select)
    form.addEventListener('change', function (e) {
      const target = e.target;
      if (target.tagName.toLowerCase() === 'select') {
        if (counterpartForm) {
          syncForms(form, counterpartForm, target.name);
        }
        form.submit();
      }
    });

    // Événement clavier (Enter et Escape)
    form.addEventListener('keydown', function (e) {
      const target = e.target;
      if (e.key === 'Enter') {
        e.preventDefault();
        clearTimeout(debounceTimer);
        form.submit();
      } else if (e.key === 'Escape' && (target.type === 'text' || target.type === 'search')) {
        target.value = '';
        if (counterpartForm) {
          syncForms(form, counterpartForm, target.name);
        }
        clearTimeout(debounceTimer);
        form.submit();
      }
    });
  }

  /**
   * Gère les boutons d'effacement rapide (croix) dans les champs de recherche
   */
  function setupSearchClearButtons() {
    const clearButtons = document.querySelectorAll('.filter-search-clear');
    clearButtons.forEach(function (btn) {
      btn.addEventListener('click', function (e) {
        e.preventDefault();
        const wrapper = btn.closest('.filter-search-wrapper');
        if (!wrapper) return;
        const input = wrapper.querySelector('input');
        if (input) {
          input.value = '';
          const form = input.form;
          if (form) {
            clearTimeout(debounceTimer);
            form.submit();
          }
        }
      });
    });
  }

  return {
    init: init,
    updateBadges: updateBadges,
    countActiveFilters: countActiveFilters
  };
})();
