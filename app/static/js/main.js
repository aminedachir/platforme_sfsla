/**
 * PSFSLA — Main JavaScript
 * Global interactivity: sidebar toggle, counter animations, utilities
 */

'use strict';

/* ── Sidebar mobile toggle ───────────────────────────────── */
function initSidebar() {
  const toggle = document.getElementById('sidebar-toggle');
  const sidebar = document.getElementById('psf-sidebar');
  const overlay = document.getElementById('sidebar-overlay');
  if (!toggle || !sidebar) return;

  toggle.addEventListener('click', () => {
    sidebar.classList.toggle('open');
    overlay && overlay.classList.toggle('active');
  });

  overlay && overlay.addEventListener('click', () => {
    sidebar.classList.remove('open');
    overlay.classList.remove('active');
  });
}

/* ── Animated counter for stats ─────────────────────────── */
function animateCounter(el) {
  const target = parseInt(el.dataset.target, 10);
  const duration = 1800;
  const step = target / (duration / 16);
  let current = 0;

  const timer = setInterval(() => {
    current += step;
    if (current >= target) {
      current = target;
      clearInterval(timer);
    }
    el.textContent = Math.floor(current).toLocaleString('ar-DZ');
  }, 16);
}

function initCounters() {
  const counters = document.querySelectorAll('[data-counter]');
  if (!counters.length) return;

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        animateCounter(entry.target);
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.3 });

  counters.forEach(el => observer.observe(el));
}

/* ── Smooth active nav highlighting ─────────────────────── */
function initActiveNav() {
  const links = document.querySelectorAll('.psf-sidebar .nav-item-link');
  const currentPath = window.location.pathname;
  links.forEach(link => {
    if (link.getAttribute('href') === currentPath) {
      link.classList.add('active');
    }
  });
}

/* ── Confirm delete modals ───────────────────────────────── */
function confirmDelete(message, formId) {
  if (confirm(message || 'هل أنت متأكد من حذف هذا العنصر؟')) {
    document.getElementById(formId)?.submit();
  }
}

/* ── File input preview (profile photo / uploads) ────────── */
function initFilePreview() {
  document.querySelectorAll('[data-preview-target]').forEach(input => {
    const targetId = input.dataset.previewTarget;
    const img = document.getElementById(targetId);
    if (!img) return;
    input.addEventListener('change', () => {
      const file = input.files[0];
      if (file) {
        const reader = new FileReader();
        reader.onload = e => { img.src = e.target.result; };
        reader.readAsDataURL(file);
      }
    });
  });
}

/* ── Bootstrap tooltips ─────────────────────────────────── */
function initTooltips() {
  document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(el => {
    new bootstrap.Tooltip(el);
  });
}

/* ── Init all ────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  initSidebar();
  initCounters();
  initActiveNav();
  initFilePreview();
  initTooltips();
});
