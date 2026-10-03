/* ==============================================================================
   GéoFoncier NGOGOM_UAD — Scripts Globaux & Interface Utilisateur (global.js)
   Gestion de la sidebar, des alertes, confirmations et tooltips Bootstrap
   ============================================================================== */

document.addEventListener('DOMContentLoaded', function () {

  // --- Sidebar Mobile & Tablette (Flottante off-canvas) ---
  const sidebar      = document.getElementById('sidebar');
  const toggleBtn    = document.getElementById('sidebarToggle');

  // Overlay mobile
  let overlay = document.querySelector('.sidebar-overlay');
  if (!overlay) {
    overlay = document.createElement('div');
    overlay.className = 'sidebar-overlay';
    document.body.appendChild(overlay);
  }

  function closeMobileSidebar() {
    if (sidebar) sidebar.classList.remove('mobile-open');
    if (overlay) overlay.classList.remove('show');
    document.body.style.overflow = '';
  }

  function openMobileSidebar() {
    if (sidebar) sidebar.classList.add('mobile-open');
    if (overlay) overlay.classList.add('show');
    document.body.style.overflow = 'hidden';
  }

  if (toggleBtn && sidebar) {
    toggleBtn.addEventListener('click', function (e) {
      e.stopPropagation();
      if (sidebar.classList.contains('mobile-open')) {
        closeMobileSidebar();
      } else {
        openMobileSidebar();
      }
    });
  }

  overlay.addEventListener('click', closeMobileSidebar);

  // Fermer la sidebar sur mobile au clic sur un lien
  if (sidebar) {
    sidebar.querySelectorAll('.nav-link, .nav-sublink').forEach(function (link) {
      link.addEventListener('click', function () {
        if (window.innerWidth < 992) {
          closeMobileSidebar();
        }
      });
    });
  }

  // Fermer la sidebar sur resize desktop
  window.addEventListener('resize', function () {
    if (window.innerWidth >= 992) {
      closeMobileSidebar();
    }
  });

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

// --- Dynamic Sidebar Accordion (V2) ---
window.toggleSidebarGroup = function (btn) {
  const group = btn.closest('.nav-accordion-group');
  if (!group) return;

  const wasExpanded = group.classList.contains('is-expanded');

  // Replier les autres accordéons pour une vue propre
  document.querySelectorAll('.nav-accordion-group.is-expanded').forEach(function(other) {
    if (other !== group) {
      other.classList.remove('is-expanded');
    }
  });

  group.classList.toggle('is-expanded', !wasExpanded);
};
