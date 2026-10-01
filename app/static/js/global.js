/* ==============================================================================
   GéoFoncier NGOGOM_UAD — Scripts Globaux & Interface Utilisateur (global.js)
   Gestion de la sidebar, des alertes, confirmations et tooltips Bootstrap
   ============================================================================== */

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
