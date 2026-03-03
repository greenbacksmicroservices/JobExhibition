// Smooth sidebar accordion functionality
document.addEventListener('DOMContentLoaded', () => {
  const toggles = document.querySelectorAll('[data-sidebar-toggle]');
  const overlay = document.getElementById('sidebarOverlay');
  const accordions = document.querySelectorAll('.nav-toggle');
  const subAccordions = document.querySelectorAll('.nav-sub-toggle');
  const darkToggle = document.getElementById('darkModeToggle');
  const fullscreenToggles = document.querySelectorAll('[data-fullscreen-toggle]');
  const messageLinks = document.querySelectorAll('a.icon-btn[aria-label="Messages"]');
  const panelUserName = (
    document.querySelector('.profile-meta strong')?.textContent ||
    document.querySelector('.company-user-meta strong')?.textContent ||
    ''
  )
    .trim()
    .toLowerCase();
  const isSubadminPanel = panelUserName === 'subadmin' || document.body.dataset.panelRole === 'subadmin';

  const isMobile = () => window.matchMedia('(max-width: 900px)').matches;
  const storage = {
    get: (key) => {
      try {
        return window.localStorage.getItem(key);
      } catch {
        return null;
      }
    },
    set: (key, value) => {
      try {
        window.localStorage.setItem(key, String(value));
      } catch {
        // Ignore storage errors and keep UI responsive.
      }
    },
  };

  const iconPaths = {
    menu: 'M4 6h16M4 12h16M4 18h16',
    fullscreen: 'M8 3H3v5M16 3h5v5M8 21H3v-5M21 16v5h-5',
    moon: 'M21 12.8A9 9 0 1 1 11.2 3 7 7 0 0 0 21 12.8z',
    sun: 'M12 3v2m0 14v2m9-9h-2M5 12H3m15.36 6.36-1.41-1.41M7.05 7.05 5.64 5.64m12.72 0-1.41 1.41M7.05 16.95l-1.41 1.41M12 16a4 4 0 1 0 0-8 4 4 0 0 0 0 8z',
    message: 'M4 5h16a1 1 0 0 1 1 1v12l-4-3H4a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1z',
    search: 'M11 19a8 8 0 1 1 5.3-14l.1.1A8 8 0 0 1 11 19zm8 2-4.3-4.3',
    bell: 'M15 17H5l1.4-2.6V10a5 5 0 0 1 10 0v4.4L18 17h-3zm-3 4a2 2 0 0 0 2-2h-4a2 2 0 0 0 2 2z',
    user: 'M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zm-7 9a7 7 0 0 1 14 0',
    briefcase: 'M9 7V5a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2M3 9h18v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V9z',
    chart: 'M4 20h16M7 16V9m5 7V5m5 11v-4',
    calendar: 'M7 3v3m10-3v3M4 8h16M5 6h14a1 1 0 0 1 1 1v13a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V7a1 1 0 0 1 1-1z',
    file: 'M6 3h8l4 4v14H6zM14 3v4h4',
    image: 'M4 5h16a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1zm3 10 3-3 3 4 4-5 2 4',
    key: 'M15 7a4 4 0 1 1-3.9 4.8H3v2h2v2h2v2h2v-2h2.1A4 4 0 0 1 15 7z',
    home: 'M3 11.5 9.5 6 12 4l2.5 2 6.5 5.5M5 10.5V20h14v-9.5',
    card: 'M3 7h18v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7zm0 4h18',
    flag: 'M5 3v18M5 4h10l-1.5 3L15 10H5',
    shield: 'M12 3l7 3v6c0 4.4-2.8 8.4-7 9.9C7.8 20.4 5 16.4 5 12V6l7-3z',
    download: 'M12 4v10m0 0 4-4m-4 4-4-4M4 20h16',
    inbox: 'M4 5h16v10H15l-3 3-3-3H4V5z',
    plus: 'M12 5v14M5 12h14',
    filter: 'M4 5h16l-6 7v6l-4 2v-8L4 5z',
    trash: 'M6 7h12M9 7V5h6v2m-8 3v8m4-8v8m4-8v8M7 20h10a1 1 0 0 0 1-1V7H6v12a1 1 0 0 0 1 1z',
    clock: 'M12 7v5l3 3M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18z',
    eye: 'M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6-10-6-10-6zm10 3a3 3 0 1 0 0-6 3 3 0 0 0 0 6z',
    gift: 'M20 12v8H4v-8m16 0H4m0 0V8h16v4M12 8v12M8 8a2 2 0 1 1 0-4c2 0 4 4 4 4s-2 0-4 0zm8 0a2 2 0 1 0 0-4c-2 0-4 4-4 4s2 0 4 0z',
    pen: 'M4 20h4l10-10-4-4L4 16v4zm9-13 4 4',
    location: 'M12 21s6-5.4 6-10a6 6 0 1 0-12 0c0 4.6 6 10 6 10zm0-7a3 3 0 1 0 0-6 3 3 0 0 0 0 6z',
    bolt: 'M13 2 5 13h6l-1 9 8-11h-6l1-9z',
    wallet: 'M3 7h18v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7zm14 6h3',
    coins: 'M7 7c0 1.7 2.2 3 5 3s5-1.3 5-3-2.2-3-5-3-5 1.3-5 3zm0 5c0 1.7 2.2 3 5 3s5-1.3 5-3m-10 5c0 1.7 2.2 3 5 3s5-1.3 5-3',
    settings: 'M12 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6zm8 3-2 .6a6 6 0 0 1-.6 1.4l1.2 1.7-1.4 1.4-1.7-1.2c-.4.2-.9.4-1.4.6L13 20h-2l-.6-2a6 6 0 0 1-1.4-.6l-1.7 1.2-1.4-1.4 1.2-1.7a6 6 0 0 1-.6-1.4L4 12l2-.6c.1-.5.3-1 .6-1.4L5.4 8.3 6.8 6.9l1.7 1.2c.4-.2.9-.4 1.4-.6L11 4h2l.6 2c.5.1 1 .3 1.4.6l1.7-1.2 1.4 1.4-1.2 1.7c.2.4.4.9.6 1.4L20 12z',
    support: 'M12 3a7 7 0 0 1 7 7v2a5 5 0 0 1-5 5h-1v3h-2v-3H9a5 5 0 0 1-5-5v-2a7 7 0 0 1 7-7z',
    logout: 'M15 4h4v16h-4M10 8l4 4-4 4M14 12H4',
    crown: 'M3 8l4 4 5-6 5 6 4-4-2 11H5L3 8z',
    check: 'M4 12l5 5L20 6',
    close: 'M6 6l12 12M18 6 6 18',
  };

  const buildInlineIcon = (path, extraAttrs = '') =>
    `<svg class="ui-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" ${extraAttrs}><path d="${path}" /></svg>`;

  const hasFontAwesome = () => {
    const sample = document.querySelector('i.fa-solid, i.fa-regular');
    if (!sample) return false;
    const family = (window.getComputedStyle(sample).fontFamily || '').toLowerCase();
    return family.includes('font awesome');
  };

  let useInlineFallbackIcons = false;
  let inlineFallbackApplied = false;
  const faPathMap = {
    'fa-bars': iconPaths.menu,
    'fa-moon': iconPaths.moon,
    'fa-sun': iconPaths.sun,
    'fa-envelope': iconPaths.message,
    'fa-comments': iconPaths.message,
    'fa-magnifying-glass': iconPaths.search,
    'fa-bell': iconPaths.bell,
    'fa-user': iconPaths.user,
    'fa-user-check': iconPaths.user,
    'fa-user-group': iconPaths.user,
    'fa-users': iconPaths.user,
    'fa-house': iconPaths.home,
    'fa-id-badge': iconPaths.user,
    'fa-briefcase': iconPaths.briefcase,
    'fa-chart-line': iconPaths.chart,
    'fa-chart-bar': iconPaths.chart,
    'fa-chart-pie': iconPaths.chart,
    'fa-calendar-check': iconPaths.calendar,
    'fa-file': iconPaths.file,
    'fa-file-lines': iconPaths.file,
    'fa-file-signature': iconPaths.file,
    'fa-file-export': iconPaths.file,
    'fa-image': iconPaths.image,
    'fa-key': iconPaths.key,
    'fa-credit-card': iconPaths.card,
    'fa-flag': iconPaths.flag,
    'fa-shield-halved': iconPaths.shield,
    'fa-download': iconPaths.download,
    'fa-inbox': iconPaths.inbox,
    'fa-plus': iconPaths.plus,
    'fa-filter': iconPaths.filter,
    'fa-trash': iconPaths.trash,
    'fa-clock': iconPaths.clock,
    'fa-eye': iconPaths.eye,
    'fa-gift': iconPaths.gift,
    'fa-pen': iconPaths.pen,
    'fa-location-dot': iconPaths.location,
    'fa-bolt': iconPaths.bolt,
    'fa-wallet': iconPaths.wallet,
    'fa-coins': iconPaths.coins,
    'fa-list-check': iconPaths.check,
    'fa-circle-check': iconPaths.check,
    'fa-check-circle': iconPaths.check,
    'fa-check': iconPaths.check,
    'fa-ban': iconPaths.close,
    'fa-times-circle': iconPaths.close,
    'fa-triangle-exclamation': iconPaths.bell,
    'fa-up-right-and-down-left-from-center': iconPaths.fullscreen,
    'fa-bookmark': iconPaths.file,
    'fa-trophy': iconPaths.crown,
    'fa-handshake': iconPaths.support,
    'fa-gear': iconPaths.settings,
    'fa-headset': iconPaths.support,
    'fa-right-from-bracket': iconPaths.logout,
    'fa-crown': iconPaths.crown,
    'fa-volume-high': iconPaths.bell,
    'fa-volume-xmark': iconPaths.bell,
  };

  const replaceIconWithInline = (button, path, attrs = '') => {
    if (!button) return;
    const existing = button.querySelector('svg.ui-icon');
    if (existing) {
      const currentPath = existing.querySelector('path');
      if (currentPath) {
        currentPath.setAttribute('d', path);
      }
      return;
    }
    const iconEl = button.querySelector('i');
    const inline = buildInlineIcon(path, attrs);
    if (iconEl) {
      iconEl.insertAdjacentHTML('afterend', inline);
      iconEl.remove();
      return;
    }
    button.insertAdjacentHTML('afterbegin', inline);
  };

  const resolveInlinePathForFaIcon = (iconEl) => {
    if (!iconEl) return iconPaths.file;
    const classNames = Array.from(iconEl.classList || []);
    for (let idx = 0; idx < classNames.length; idx += 1) {
      const key = classNames[idx];
      if (faPathMap[key]) {
        return faPathMap[key];
      }
    }
    return iconPaths.file;
  };

  const replaceAnyFaIcon = (iconEl) => {
    if (!iconEl || iconEl.tagName !== 'I') return;
    const path = resolveInlinePathForFaIcon(iconEl);
    const inline = buildInlineIcon(path);
    iconEl.insertAdjacentHTML('afterend', inline);
    iconEl.remove();
  };

  const applyInlineFallbackIcons = () => {
    if (inlineFallbackApplied || hasFontAwesome()) {
      return;
    }
    useInlineFallbackIcons = true;
    inlineFallbackApplied = true;
    toggles.forEach((button) => replaceIconWithInline(button, iconPaths.menu));
    fullscreenToggles.forEach((button) => replaceIconWithInline(button, iconPaths.fullscreen));
    messageLinks.forEach((button) => replaceIconWithInline(button, iconPaths.message));
    document.querySelectorAll('i.fa-solid, i.fa-regular, i.fa-brands').forEach((iconEl) => {
      replaceAnyFaIcon(iconEl);
    });
  };

  const scheduleInlineFallbackDetection = () => {
    const detectAndApply = () => {
      if (!hasFontAwesome()) {
        applyInlineFallbackIcons();
      }
    };
    window.setTimeout(detectAndApply, 900);
    window.addEventListener('load', detectAndApply, { once: true });
  };

  scheduleInlineFallbackDetection();

  const activateLogoFallback = (brandMark) => {
    if (!brandMark || brandMark.classList.contains('logo-fallback')) return;
    brandMark.classList.add('logo-fallback');
  };

  document.querySelectorAll('.brand-mark img').forEach((img) => {
    const brandMark = img.closest('.brand-mark');
    const markAsLoaded = () => {
      if (brandMark) {
        brandMark.classList.add('logo-loaded');
      }
    };
    const onError = () => {
      if (brandMark) {
        brandMark.classList.remove('logo-loaded');
      }
      if (img && img.parentNode) {
        img.remove();
      }
      activateLogoFallback(brandMark);
    };
    if (img.complete && img.naturalWidth > 0) {
      markAsLoaded();
      return;
    }
    if (img.complete && img.naturalWidth === 0) {
      onError();
      return;
    }
    img.addEventListener('load', markAsLoaded, { once: true });
    img.addEventListener('error', onError, { once: true });
    setTimeout(() => {
      if (!img.complete || img.naturalWidth <= 0) {
        onError();
      }
    }, 3000);
  });

  document.querySelectorAll('.company-logo').forEach((logo) => {
    const img = logo.querySelector('img');
    if (!img) return;

    const userName = (
      logo.closest('.company-user')?.querySelector('.company-user-meta strong')?.textContent || 'A'
    )
      .trim()
      .charAt(0)
      .toUpperCase() || 'A';

    const fallbackToInitial = () => {
      if (!logo) return;
      if (logo.querySelector('span')) {
        const existing = logo.querySelector('span');
        existing.textContent = userName;
        if (img && img.parentNode) img.remove();
        return;
      }
      const fallback = document.createElement('span');
      fallback.textContent = userName;
      if (img && img.parentNode) img.remove();
      logo.appendChild(fallback);
    };

    if (img.complete && img.naturalWidth === 0) {
      fallbackToInitial();
      return;
    }
    img.addEventListener('error', fallbackToInitial, { once: true });
  });

  if (isSubadminPanel) {
    document.body.dataset.panelRole = 'subadmin';
    document.body.dataset.canDelete = 'false';

    document.querySelectorAll('.company-user-meta span, .profile-meta span').forEach((node) => {
      node.textContent = 'Platform Sub-Admin';
    });
    document.querySelectorAll('.brand-subtitle').forEach((node) => {
      node.textContent = 'Subadmin Control';
    });

    const isDeleteControl = (element) => {
      if (!element) return false;
      const action = (
        element.dataset.action ||
        element.dataset.subAction ||
        element.dataset.addonAction ||
        ''
      )
        .trim()
        .toLowerCase();
      if (action === 'delete' || action === 'remove') return true;

      const id = (element.id || '').trim().toLowerCase();
      if (id.includes('delete') || id.includes('remove')) return true;

      const text = (element.textContent || '').trim().toLowerCase();
      return text === 'delete' || text.startsWith('delete ') || text.endsWith(' delete') || text.includes('remove');
    };

    const hideDeleteControls = (root = document) => {
      root.querySelectorAll('button, a, [role="button"]').forEach((element) => {
        if (!isDeleteControl(element)) return;
        element.style.display = 'none';
        element.setAttribute('aria-hidden', 'true');
        if ('disabled' in element) {
          element.disabled = true;
        }
      });
    };

    hideDeleteControls(document);
    const observer = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        mutation.addedNodes.forEach((node) => {
          if (!(node instanceof Element)) return;
          hideDeleteControls(node);
        });
      });
    });
    observer.observe(document.body, { childList: true, subtree: true });
  }

  const clearStuckLoadingOverlays = () => {
    document.querySelectorAll('.loading-overlay.active').forEach((overlayEl) => {
      overlayEl.classList.remove('active');
    });
  };
  const cleanupModalArtifacts = () => {
    const hasVisibleModal = Boolean(document.querySelector('.modal.show'));
    if (hasVisibleModal) {
      const backdrops = document.querySelectorAll('.modal-backdrop');
      if (backdrops.length > 1) {
        backdrops.forEach((node, index) => {
          if (index < backdrops.length - 1) {
            node.remove();
          }
        });
      }
      return;
    }
    document.querySelectorAll('.modal-backdrop').forEach((node) => node.remove());
    document.body.classList.remove('modal-open');
    document.body.style.removeProperty('overflow');
    document.body.style.removeProperty('padding-right');
  };

  const scheduleModalCleanup = (delay = 80) => {
    window.setTimeout(() => {
      clearStuckLoadingOverlays();
      cleanupModalArtifacts();
    }, delay);
  };

  document.addEventListener('shown.bs.modal', () => {
    clearStuckLoadingOverlays();
    cleanupModalArtifacts();
  });
  document.addEventListener('hidden.bs.modal', () => {
    scheduleModalCleanup(40);
  });
  document.addEventListener('click', (event) => {
    if (event.target.closest('[data-bs-dismiss="modal"], .btn-close')) {
      scheduleModalCleanup(120);
    }
  });
  document.addEventListener('visibilitychange', () => {
    if (!document.hidden) {
      scheduleModalCleanup(20);
    }
  });
  window.addEventListener('pageshow', () => scheduleModalCleanup(20));
  window.addEventListener('beforeunload', () => scheduleModalCleanup(0));
  window.addEventListener('error', () => scheduleModalCleanup(20));
  window.addEventListener('unhandledrejection', () => scheduleModalCleanup(20));

  const closeMobileSidebar = () => {
    if (!isMobile()) return;
    document.body.classList.remove('sidebar-open');
    toggles.forEach((btn) => btn.setAttribute('aria-expanded', 'false'));
  };

  const applySidebarState = (collapsed) => {
    if (collapsed) {
      document.body.classList.add('sidebar-collapsed');
    } else {
      document.body.classList.remove('sidebar-collapsed');
    }
    storage.set('sidebar-collapsed', collapsed ? 'true' : 'false');
  };

  const toggleSidebar = () => {
    if (isMobile()) {
      document.body.classList.toggle('sidebar-open');
      toggles.forEach((btn) => {
        btn.setAttribute('aria-expanded', document.body.classList.contains('sidebar-open').toString());
      });
      return;
    }
    const collapsed = document.body.classList.toggle('sidebar-collapsed');
    storage.set('sidebar-collapsed', collapsed ? 'true' : 'false');
  };

  // Menu toggle
  toggles.forEach((btn) => btn.addEventListener('click', toggleSidebar));

  // Overlay click handler
  if (overlay) {
    overlay.addEventListener('click', () => {
      closeMobileSidebar();
    });
  }

  const stored = storage.get('sidebar-collapsed');
  if (stored === 'true' && !isMobile()) {
    applySidebarState(true);
  }

  window.addEventListener('resize', () => {
    if (isMobile()) {
      document.body.classList.remove('sidebar-collapsed');
    } else {
      document.body.classList.remove('sidebar-open');
      const saved = storage.get('sidebar-collapsed');
      applySidebarState(saved === 'true');
    }
  });

  const resolveThemeScope = () => {
    const scoped = (document.body?.dataset?.themeScope || '').trim().toLowerCase();
    if (scoped) return scoped;
    if (document.body.classList.contains('candidate-dashboard')) return 'candidate';
    if (document.body.classList.contains('company-dashboard')) return 'company';
    if (document.body.classList.contains('consultancy-dashboard')) return 'consultancy';
    if (document.body.classList.contains('user-management')) return 'admin';
    return 'admin';
  };

  const themeScope = resolveThemeScope();
  const darkStorageKey = `dark-mode-${themeScope}`;
  window.__dashboardThemeManaged = true;

  // Dark mode toggle
  const updateDarkIcon = () => {
    if (!darkToggle) return;
    if (useInlineFallbackIcons) {
      const isDark = document.body.classList.contains('dark-mode');
      replaceIconWithInline(darkToggle, isDark ? iconPaths.sun : iconPaths.moon, 'data-dark-icon="true"');
      return;
    }
    const icon = darkToggle.querySelector('i');
    if (!icon) return;
    if (document.body.classList.contains('dark-mode')) {
      icon.classList.remove('fa-moon');
      icon.classList.add('fa-sun');
    } else {
      icon.classList.remove('fa-sun');
      icon.classList.add('fa-moon');
    }
  };

  const storedTheme = storage.get(darkStorageKey);
  const legacyTheme = storage.get('dark-mode');
  const shouldEnableDark =
    storedTheme === 'true' || (storedTheme === null && themeScope === 'admin' && legacyTheme === 'true');
  document.body.classList.toggle('dark-mode', shouldEnableDark);

  updateDarkIcon();

  if (darkToggle) {
    darkToggle.addEventListener('click', () => {
      document.body.classList.toggle('dark-mode');
      storage.set(darkStorageKey, document.body.classList.contains('dark-mode'));
      updateDarkIcon();
    });
  }

  const animateAccordion = (section, shouldOpen) => {
    const body = section ? section.querySelector('.nav-accordion-body') : null;
    if (!section || !body) return;
    body.style.overflow = 'hidden';
    if (shouldOpen) {
      section.classList.add('open');
      body.style.display = 'block';
      body.style.maxHeight = '0px';
      requestAnimationFrame(() => {
        body.style.maxHeight = `${body.scrollHeight}px`;
      });
      window.setTimeout(() => {
        if (section.classList.contains('open')) {
          body.style.maxHeight = '';
          body.style.overflow = '';
        }
      }, 360);
      return;
    }
    body.style.maxHeight = `${body.scrollHeight}px`;
    requestAnimationFrame(() => {
      body.style.maxHeight = '0px';
    });
    window.setTimeout(() => {
      if (!section.classList.contains('open')) {
        body.style.display = '';
        body.style.maxHeight = '';
        body.style.overflow = '';
      }
    }, 360);
  };

  // Main accordion menu items with smooth animation
  accordions.forEach((button) => {
    button.addEventListener('click', (e) => {
      const navUrl = button.dataset.navUrl;
      const caretClicked = Boolean(e.target.closest('.caret'));
      if (navUrl && !caretClicked) {
        window.location.href = navUrl;
        return;
      }
      e.preventDefault();
      e.stopPropagation();
      
      const section = button.closest('.nav-section');
      if (!section) return;

      // Close other sections (optional - comment out for allow-all-open behavior)
      // accordions.forEach(otherButton => {
      //   const otherSection = otherButton.closest('.nav-section');
      //   if (otherSection !== section && otherSection.classList.contains('open')) {
      //     otherSection.classList.remove('open');
      //     otherButton.setAttribute('aria-expanded', 'false');
      //   }
      // });

      // Toggle current section
      const isOpen = !section.classList.contains('open');
      animateAccordion(section, isOpen);
      section.classList.toggle('open', isOpen);
      button.setAttribute('aria-expanded', String(isOpen));
    });
  });

  // Nested sub-accordion items with smooth animation
  subAccordions.forEach((button) => {
    button.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      
      const isOpen = button.getAttribute('aria-expanded') === 'true';
      button.setAttribute('aria-expanded', String(!isOpen));
    });
  });

  // Smooth scroll for sidebar
  const sidebar = document.querySelector('.sidebar');
  if (sidebar) {
    sidebar.style.scrollBehavior = 'smooth';
    sidebar.style.webkitOverflowScrolling = 'touch';
  }

  // Close mobile sidebar on navigation
  const sidebarLinks = document.querySelectorAll('.sidebar-nav a');
  sidebarLinks.forEach((link) => {
    link.addEventListener('click', () => {
      if (document.body.classList.contains('sidebar-open')) {
        closeMobileSidebar();
      }
    });
  });

  // Lightweight same-origin prefetch for faster panel navigation.
  const prefetchedUrls = new Set();
  const shouldPrefetch = (url) => {
    if (!url) return false;
    if (url.startsWith('#') || url.startsWith('javascript:')) return false;
    if (url.includes('/logout')) return false;
    return true;
  };
  const prefetchUrl = (url) => {
    try {
      const resolved = new URL(url, window.location.origin);
      if (resolved.origin !== window.location.origin) return;
      const finalUrl = resolved.toString();
      if (prefetchedUrls.has(finalUrl)) return;
      prefetchedUrls.add(finalUrl);
      fetch(finalUrl, {
        method: 'GET',
        credentials: 'same-origin',
        headers: {
          'X-Requested-With': 'Prefetch',
        },
      }).catch(() => {});
    } catch {
      // Ignore malformed URLs and keep UI smooth.
    }
  };
  const prefetchLinks = document.querySelectorAll('.sidebar-nav a, .topbar a, .profile-menu a');
  prefetchLinks.forEach((link) => {
    const href = (link.getAttribute('href') || '').trim();
    if (!shouldPrefetch(href)) return;
    link.addEventListener('mouseenter', () => prefetchUrl(href));
    link.addEventListener('focus', () => prefetchUrl(href));
    link.addEventListener('touchstart', () => prefetchUrl(href), { passive: true });
  });

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && document.body.classList.contains('sidebar-open')) {
      closeMobileSidebar();
    }
  });

  const getCookie = (name) => {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
    return '';
  };

  const clearCookie = (name) => {
    document.cookie = `${name}=; Max-Age=0; path=/`;
  };

  const showWelcomeToast = (role) => {
    const toast = document.createElement('div');
    toast.className = 'welcome-toast show';
    toast.textContent = `Welcome back, ${role}!`;
    document.body.appendChild(toast);
    setTimeout(() => {
      toast.remove();
    }, 3200);
  };

  const welcomeRole = getCookie('welcome_role');
  if (welcomeRole) {
    showWelcomeToast(welcomeRole);
    clearCookie('welcome_role');
  }

  fullscreenToggles.forEach((btn) => {
    btn.addEventListener('click', () => {
      if (!document.fullscreenElement) {
        document.documentElement.requestFullscreen().catch(() => {});
      } else if (document.exitFullscreen) {
        document.exitFullscreen().catch(() => {});
      }
    });
  });

  const adVideos = Array.from(document.querySelectorAll('.ad-media video'));
  const safePlay = (video) => {
    if (!video) return;
    const promise = video.play();
    if (promise && typeof promise.catch === 'function') {
      promise.catch(() => {});
    }
  };
  const setMutedState = (video, muted) => {
    video.muted = muted;
    video.defaultMuted = muted;
    if (muted) {
      video.setAttribute('muted', '');
    } else {
      video.removeAttribute('muted');
    }
  };

  adVideos.forEach((video) => {
    setMutedState(video, true);
    const tryPlay = () => {
      safePlay(video);
    };
    if (video.readyState >= 2) {
      tryPlay();
    } else {
      video.addEventListener('canplay', tryPlay, { once: true });
    }
  });

  const hasAudioTrack = (video) => {
    if (typeof video.mozHasAudio === 'boolean') {
      return video.mozHasAudio;
    }
    if (typeof video.webkitAudioDecodedByteCount === 'number') {
      return video.webkitAudioDecodedByteCount > 0;
    }
    if (video.audioTracks && typeof video.audioTracks.length === 'number') {
      return video.audioTracks.length > 0;
    }
    return true;
  };

  const setSoundState = (video, soundEnabled) => {
    setMutedState(video, !soundEnabled);
    if (soundEnabled) {
      video.volume = 1;
      if (video.audioTracks && typeof video.audioTracks.length === 'number') {
        for (let idx = 0; idx < video.audioTracks.length; idx += 1) {
          video.audioTracks[idx].enabled = true;
        }
      }
    }
    safePlay(video);
  };

  const updateSoundButton = (button, video) => {
    const icon = button.querySelector('i');
    const inlineIcon = button.querySelector('svg.ui-icon');
    const label = button.querySelector('span');
    if (!hasAudioTrack(video)) {
      button.setAttribute('aria-pressed', 'false');
      button.setAttribute('aria-label', 'No audio track');
      button.disabled = true;
      if (icon) {
        icon.classList.remove('fa-volume-high');
        icon.classList.add('fa-volume-xmark');
      }
      if (inlineIcon) {
        const pathNode = inlineIcon.querySelector('path');
        if (pathNode) pathNode.setAttribute('d', iconPaths.bell);
      }
      if (label) {
        label.textContent = 'No Audio';
      }
      return;
    }

    button.disabled = false;
    if (video.muted) {
      button.setAttribute('aria-pressed', 'false');
      button.setAttribute('aria-label', 'Enable sound');
      if (icon) {
        icon.classList.remove('fa-volume-high');
        icon.classList.add('fa-volume-xmark');
      }
      if (inlineIcon) {
        const pathNode = inlineIcon.querySelector('path');
        if (pathNode) pathNode.setAttribute('d', iconPaths.bell);
      }
      if (label) {
        label.textContent = 'Sound Off';
      }
    } else {
      button.setAttribute('aria-pressed', 'true');
      button.setAttribute('aria-label', 'Disable sound');
      if (icon) {
        icon.classList.remove('fa-volume-xmark');
        icon.classList.add('fa-volume-high');
      }
      if (inlineIcon) {
        const pathNode = inlineIcon.querySelector('path');
        if (pathNode) pathNode.setAttribute('d', iconPaths.message);
      }
      if (label) {
        label.textContent = 'Sound On';
      }
    }
  };

  const videoToButton = new WeakMap();
  const soundButtons = document.querySelectorAll('[data-ad-sound-toggle]');
  soundButtons.forEach((button) => {
    const container = button.closest('.ad-media');
    const video = container ? container.querySelector('video') : null;
    if (!video) return;
    videoToButton.set(video, button);
    updateSoundButton(button, video);
    button.addEventListener('click', (event) => {
      event.preventDefault();

      const shouldUnmute = video.muted;
      if (shouldUnmute) {
        adVideos.forEach((otherVideo) => {
          if (otherVideo === video) return;
          setSoundState(otherVideo, false);
          const otherButton = videoToButton.get(otherVideo);
          if (otherButton) {
            updateSoundButton(otherButton, otherVideo);
          }
        });
      }

      setSoundState(video, shouldUnmute);
      updateSoundButton(button, video);
    });
  });
});
