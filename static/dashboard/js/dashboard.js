// Mark theme handling early so secondary scripts don't double-bind toggles.
if (typeof window !== 'undefined') {
  window.__dashboardThemeManaged = true;
}

// Smooth sidebar accordion functionality
document.addEventListener('DOMContentLoaded', () => {
  if (window.__dashboardCoreInitialized) {
    return;
  }
  window.__dashboardCoreInitialized = true;
  const toggles = document.querySelectorAll('[data-sidebar-toggle]');
  const overlay = document.getElementById('sidebarOverlay');
  let accordions = Array.from(document.querySelectorAll('.nav-toggle'));
  let subAccordions = Array.from(document.querySelectorAll('.nav-sub-toggle'));
  const darkToggle = document.getElementById('darkModeToggle');
  const fullscreenToggles = document.querySelectorAll('[data-fullscreen-toggle]');
  const messageLinks = document.querySelectorAll('a.icon-btn[aria-label="Messages"]');
  let panelMessageCountBadges = document.querySelectorAll('[data-panel-message-count]');
  const notificationDropdowns = Array.from(document.querySelectorAll('.notification-dropdown'));
  const panelNotificationRoot = document.querySelector('[data-panel-notification-root]') || notificationDropdowns[0] || null;
  let panelNotificationCountBadges = document.querySelectorAll('[data-panel-notification-count]');
  const sidebarNotificationPlaceholders = document.querySelectorAll('[data-sidebar-notification-count]');
  const panelNotificationsApiUrl = '/api/panel-notifications/';
  const platformBrandingApiUrl = '/api/platform-branding/';
  if (panelNotificationRoot && (!panelNotificationCountBadges || !panelNotificationCountBadges.length)) {
    const summary = panelNotificationRoot.querySelector('summary');
    if (summary) {
      const autoBadge = document.createElement('span');
      autoBadge.className = 'icon-count-badge';
      autoBadge.setAttribute('data-panel-notification-count', '');
      autoBadge.style.display = 'none';
      autoBadge.textContent = '0';
      summary.appendChild(autoBadge);
      panelNotificationCountBadges = document.querySelectorAll('[data-panel-notification-count]');
    }
  }
  if (messageLinks.length) {
    messageLinks.forEach((link) => {
      if (link.querySelector('[data-panel-message-count]')) return;
      const autoBadge = document.createElement('span');
      autoBadge.className = 'icon-count-badge';
      autoBadge.setAttribute('data-panel-message-count', '');
      autoBadge.style.display = 'none';
      autoBadge.textContent = '0';
      link.appendChild(autoBadge);
    });
    panelMessageCountBadges = document.querySelectorAll('[data-panel-message-count]');
  }
  const panelUserName = (
    document.querySelector('.profile-meta strong')?.textContent ||
    document.querySelector('.company-user-meta strong')?.textContent ||
    ''
  )
    .trim()
    .toLowerCase();
  const isSubadminPanel = panelUserName === 'subadmin' || document.body.dataset.panelRole === 'subadmin';
  // Keep only one sidebar accordion open across all panels for cleaner navigation context.
  const isAccordionExclusive = true;

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

  const resolveInitialFromText = (value, fallback = 'A') => {
    const trimmed = String(value || '').trim();
    if (!trimmed) return fallback;
    const first = trimmed.charAt(0).toUpperCase();
    return first || fallback;
  };

  const setAvatarInitial = (avatar, initialChar) => {
    if (!avatar) return;
    avatar.classList.remove('has-image');
    avatar.textContent = resolveInitialFromText(initialChar);
  };

  const setAvatarImage = (avatar, imageUrl, altText, fallbackInitial) => {
    if (!avatar) return false;
    const safeUrl = String(imageUrl || '').trim();
    if (!safeUrl) {
      setAvatarInitial(avatar, fallbackInitial);
      return false;
    }

    avatar.classList.add('has-image');
    avatar.textContent = '';
    const img = document.createElement('img');
    img.src = safeUrl;
    img.alt = altText || 'Profile photo';

    const fallback = () => {
      if (img.parentNode) {
        img.remove();
      }
      setAvatarInitial(avatar, fallbackInitial);
    };

    if (img.complete && img.naturalWidth === 0) {
      fallback();
      return false;
    }

    img.addEventListener('error', fallback, { once: true });
    avatar.appendChild(img);
    return true;
  };

  document.querySelectorAll('.company-logo').forEach((logo) => {
    const progressValue = Number.parseFloat(logo.style.getPropertyValue('--progress') || '0');
    const safeProgress = Number.isFinite(progressValue)
      ? Math.min(100, Math.max(0, progressValue))
      : 0;
    logo.style.setProperty('--progress', String(safeProgress));

    const img = logo.querySelector('img');
    const userName = (
      logo.closest('.company-user')?.querySelector('.company-user-meta strong')?.textContent || 'A'
    );
    const userInitial = resolveInitialFromText(userName);

    if (!img) {
      if (!logo.querySelector('span')) {
        const fallback = document.createElement('span');
        fallback.textContent = userInitial;
        logo.appendChild(fallback);
      }
      return;
    }

    const fallbackToInitial = () => {
      if (logo.querySelector('span')) {
        const existing = logo.querySelector('span');
        existing.textContent = userInitial;
      } else {
        const fallback = document.createElement('span');
        fallback.textContent = userInitial;
        logo.appendChild(fallback);
      }
      if (img.parentNode) {
        img.remove();
      }
    };

    if (img.complete && img.naturalWidth === 0) {
      fallbackToInitial();
      return;
    }
    img.addEventListener('error', fallbackToInitial, { once: true });
  });

  // Admin panel: mirror uploaded photo into header dropdown while keeping sidebar photo visible.
  const adminUserCard = document.querySelector('.company-user.admin-user');
  if (adminUserCard) {
    const adminName =
      adminUserCard.querySelector('.company-user-meta strong')?.textContent ||
      document.querySelector('.profile-meta strong')?.textContent ||
      'A';
    const adminInitial = resolveInitialFromText(adminName);
    const sidebarLogo = adminUserCard.querySelector('.company-logo');
    const sidebarImage = sidebarLogo?.querySelector('img');
    const adminPhotoUrl = String(sidebarImage?.getAttribute('src') || '').trim();

    if (sidebarLogo && adminPhotoUrl) {
      const staleInitial = sidebarLogo.querySelector('span');
      if (staleInitial) {
        staleInitial.remove();
      }
    }

    if (sidebarLogo && !adminPhotoUrl) {
      let sidebarInitial = sidebarLogo.querySelector('span');
      if (!sidebarInitial) {
        sidebarInitial = document.createElement('span');
        sidebarLogo.appendChild(sidebarInitial);
      }
      sidebarInitial.textContent = adminInitial;
    }

    document.querySelectorAll('.profile-summary .profile-avatar').forEach((avatar) => {
      if (adminPhotoUrl) {
        setAvatarImage(avatar, adminPhotoUrl, 'Admin photo', adminInitial);
      } else {
        setAvatarInitial(avatar, adminInitial);
      }
    });
  }

  document.querySelectorAll('.profile-avatar').forEach((avatar) => {
    const fallbackInitial = resolveInitialFromText(
      avatar.dataset.initial ||
        avatar.textContent ||
        avatar.closest('.profile-summary')?.querySelector('.profile-meta strong')?.textContent ||
        avatar.closest('.company-user')?.querySelector('.company-user-meta strong')?.textContent ||
        'A'
    );
    avatar.dataset.initial = fallbackInitial;

    const img = avatar.querySelector('img');
    if (!img) {
      if (!String(avatar.textContent || '').trim()) {
        avatar.textContent = fallbackInitial;
      }
      return;
    }

    const fallbackToInitial = () => {
      setAvatarInitial(avatar, fallbackInitial);
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

  const ensureAdminDeleteDataSidebarLink = () => {
    const sidebarNav = document.querySelector('.sidebar-nav');
    const isAdminPanel = Boolean(
      document.querySelector('.company-user.admin-user') ||
      document.body.classList.contains('user-management')
    );
    if (!sidebarNav || !isAdminPanel) return;

    const normalizePath = (rawValue) => {
      const raw = (rawValue || '').trim();
      if (!raw || raw === '#') return '';
      try {
        const resolved = new URL(raw, window.location.origin);
        const pathname = (resolved.pathname || '').replace(/\/+$/, '');
        return pathname || '/';
      } catch {
        return '';
      }
    };

    const basePath = '/admin-dashboard/delete-data/company/';
    const currentPath = normalizePath(window.location.pathname);
    const isDeleteDataPath = currentPath.startsWith('/admin-dashboard/delete-data');

    const legacySection = sidebarNav.querySelector('.nav-section[data-delete-data-nav]');
    if (legacySection) {
      legacySection.remove();
    }

    let link = sidebarNav.querySelector('a.nav-item[data-delete-data-nav]');
    if (!link) {
      link = document.createElement('a');
      link.className = 'nav-item';
      link.setAttribute('data-delete-data-nav', '');
      link.href = basePath;
      link.innerHTML = `
        <span class="nav-icon"><i class="fa-solid fa-trash"></i></span>
        <span>Delete Data</span>
      `;

      const anchorNode =
        sidebarNav.querySelector('.nav-item[href*="/settings/"]') ||
        sidebarNav.querySelector('.nav-item[href*="/security/"]') ||
        sidebarNav.lastElementChild;
      if (anchorNode) {
        sidebarNav.insertBefore(link, anchorNode);
      } else {
        sidebarNav.appendChild(link);
      }
    }

    link.classList.toggle('active', isDeleteDataPath);
  };

  ensureAdminDeleteDataSidebarLink();
  accordions = Array.from(document.querySelectorAll('.nav-toggle'));
  subAccordions = Array.from(document.querySelectorAll('.nav-sub-toggle'));

  const closeMobileSidebar = () => {
    if (!isMobile()) return;
    document.body.classList.remove('sidebar-open');
    toggles.forEach((btn) => btn.setAttribute('aria-expanded', 'false'));
  };

  const setSidebarPeekOpen = (enabled) => {
    const shouldOpen = Boolean(enabled);
    if (!document.body.classList.contains('sidebar-collapsed') || isMobile()) {
      document.body.classList.remove('sidebar-peek-open');
      return;
    }
    document.body.classList.toggle('sidebar-peek-open', shouldOpen);
  };

  const closeCollapsedAccordions = () => {
    if (isMobile() || !document.body.classList.contains('sidebar-collapsed')) return;
    const openedSections = Array.from(document.querySelectorAll('.nav-section.open'));
    openedSections.forEach((section) => {
      const toggleButton = section.querySelector('.nav-toggle');
      section.classList.remove('open');
      if (toggleButton) {
        toggleButton.setAttribute('aria-expanded', 'false');
      }
      const body = section.querySelector('.nav-accordion-body');
      if (body) {
        body.style.display = '';
        body.style.maxHeight = '';
        body.style.overflow = '';
      }
    });
    document.body.classList.remove('sidebar-peek-open');
  };

  const applySidebarState = (collapsed) => {
    if (collapsed) {
      document.body.classList.add('sidebar-collapsed');
      closeCollapsedAccordions();
    } else {
      document.body.classList.remove('sidebar-collapsed');
      document.body.classList.remove('sidebar-peek-open');
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
    if (collapsed) {
      closeCollapsedAccordions();
    } else {
      document.body.classList.remove('sidebar-peek-open');
    }
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
      document.body.classList.remove('sidebar-peek-open');
    } else {
      document.body.classList.remove('sidebar-open');
      const saved = storage.get('sidebar-collapsed');
      applySidebarState(saved === 'true');
      if (saved !== 'true') {
        closeCollapsedAccordions();
      }
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

  const normalizeAccordionState = () => {
    const sections = Array.from(document.querySelectorAll('.nav-section'));
    if (!sections.length) return;
    const activeSection = sections.find((section) => section.querySelector('.nav-sub.active'));
    const collapsedDesktop = document.body.classList.contains('sidebar-collapsed') && !isMobile();
    const preferredOpenSection = collapsedDesktop ? null : activeSection || null;
    sections.forEach((section) => {
      const shouldOpen = Boolean(preferredOpenSection && section === preferredOpenSection);
      const toggleButton = section.querySelector('.nav-toggle');
      const body = section.querySelector('.nav-accordion-body');
      section.classList.toggle('open', shouldOpen);
      if (toggleButton) {
        toggleButton.setAttribute('aria-expanded', String(shouldOpen));
      }
      if (body) {
        body.style.display = shouldOpen ? 'block' : '';
        body.style.maxHeight = '';
        body.style.overflow = '';
      }
    });
  };

  const closeSiblingAccordions = (currentSection) => {
    if (!isAccordionExclusive || !currentSection) return;
    const sections = Array.from(document.querySelectorAll('.nav-section'));
    sections.forEach((section) => {
      if (section === currentSection || !section.classList.contains('open')) return;
      const toggleButton = section.querySelector('.nav-toggle');
      animateAccordion(section, false);
      section.classList.remove('open');
      if (toggleButton) {
        toggleButton.setAttribute('aria-expanded', 'false');
      }
    });
  };

  normalizeAccordionState();

  // Main accordion menu items with smooth animation
  accordions.forEach((button) => {
    button.addEventListener('click', (e) => {
      const navUrl = button.dataset.navUrl;
      const caretClicked = Boolean(e.target.closest('.caret'));
      const section = button.closest('.nav-section');
      const hasSubmenu = Boolean(section?.querySelector('.nav-accordion-body .nav-sub'));
      const isCollapsedMode = document.body.classList.contains('sidebar-collapsed') || isMobile();
      if (navUrl && !caretClicked && (!hasSubmenu || !isCollapsedMode)) {
        window.location.href = navUrl;
        return;
      }
      e.preventDefault();
      e.stopPropagation();
      
      if (!section) return;

      // Toggle current section
      const isOpen = !section.classList.contains('open');
      if (isOpen) {
        closeSiblingAccordions(section);
      }
      animateAccordion(section, isOpen);
      section.classList.toggle('open', isOpen);
      button.setAttribute('aria-expanded', String(isOpen));
      if (document.body.classList.contains('sidebar-collapsed') && !isMobile()) {
        setSidebarPeekOpen(isOpen);
      }
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
      if (document.body.classList.contains('sidebar-collapsed') && !isMobile()) {
        closeCollapsedAccordions();
      }
    });
  });

  document.addEventListener('click', (event) => {
    if (isMobile() || !document.body.classList.contains('sidebar-collapsed')) return;
    if (event.target.closest('.sidebar')) return;
    closeCollapsedAccordions();
  });

  const closeAllNotificationDropdowns = () => {
    notificationDropdowns.forEach((dropdown) => {
      dropdown.removeAttribute('open');
    });
  };

  if (notificationDropdowns.length) {
    document.addEventListener('click', (event) => {
      notificationDropdowns.forEach((dropdown) => {
        if (!dropdown.contains(event.target)) {
          dropdown.removeAttribute('open');
        }
      });
    });
    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape') {
        closeAllNotificationDropdowns();
      }
    });
  }

  const escapeHtml = (value) =>
    String(value ?? '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');

  const setCountBadges = (nodes, count) => {
    nodes.forEach((node) => {
      if (!node) return;
      const numeric = Number(count || 0);
      node.textContent = String(Math.max(0, numeric));
      node.style.display = numeric > 0 ? '' : 'none';
    });
  };

  const resolveShareUrl = (rawUrl) => {
    const value = String(rawUrl || '').trim();
    if (!value) return '';
    try {
      return new URL(value, window.location.origin).toString();
    } catch {
      return '';
    }
  };

  const copyTextFallback = async (value) => {
    if (!value) return false;
    if (navigator.clipboard && window.isSecureContext) {
      try {
        await navigator.clipboard.writeText(value);
        return true;
      } catch {
        // continue to legacy fallback
      }
    }
    const textArea = document.createElement('textarea');
    textArea.value = value;
    textArea.setAttribute('readonly', 'readonly');
    textArea.style.position = 'fixed';
    textArea.style.top = '-9999px';
    document.body.appendChild(textArea);
    textArea.select();
    const isCopied = document.execCommand('copy');
    document.body.removeChild(textArea);
    return Boolean(isCopied);
  };

  const showShareState = (button, text) => {
    if (!button) return;
    const original = button.dataset.originalText || button.textContent || 'Share';
    button.dataset.originalText = original;
    button.textContent = text;
    window.setTimeout(() => {
      button.textContent = button.dataset.originalText || 'Share';
    }, 1200);
  };

  let shareSheetState = null;

  const openExternalShare = (url) => {
    if (!url) return;
    window.open(url, '_blank', 'noopener,noreferrer');
  };

  const getShareMessage = (title, url) => `${String(title || 'Job').trim()}\n${url}`;

  const ensureShareSheet = () => {
    if (shareSheetState) return shareSheetState;

    const overlay = document.createElement('div');
    overlay.className = 'share-sheet-overlay';
    overlay.setAttribute('aria-hidden', 'true');
    overlay.innerHTML = `
      <div class="share-sheet" role="dialog" aria-modal="true" aria-label="Share job">
        <div class="share-sheet-header">
          <h4 class="share-sheet-title">Share Job</h4>
          <button type="button" class="share-sheet-close" data-share-close aria-label="Close share options">x</button>
        </div>
        <div class="share-sheet-meta" data-share-meta></div>
        <div class="share-sheet-grid">
          <button type="button" class="share-sheet-action" data-share-action="whatsapp"><span class="share-icon">WA</span><span>WhatsApp</span></button>
          <button type="button" class="share-sheet-action" data-share-action="copy"><span class="share-icon">CP</span><span>Copy Link</span></button>
          <button type="button" class="share-sheet-action" data-share-action="google"><span class="share-icon">G</span><span>Google Mail</span></button>
          <button type="button" class="share-sheet-action" data-share-action="instagram"><span class="share-icon">IG</span><span>Instagram</span></button>
          <button type="button" class="share-sheet-action" data-share-action="more"><span class="share-icon">+</span><span>More Apps</span></button>
        </div>
      </div>
    `;
    document.body.appendChild(overlay);

    const titleNode = overlay.querySelector('.share-sheet-title');
    const metaNode = overlay.querySelector('[data-share-meta]');
    const closeButton = overlay.querySelector('[data-share-close]');

    const closeSheet = () => {
      overlay.classList.remove('open');
      overlay.setAttribute('aria-hidden', 'true');
      if (shareSheetState) {
        shareSheetState.currentButton = null;
        shareSheetState.currentTitle = '';
        shareSheetState.currentUrl = '';
      }
    };

    overlay.addEventListener('click', (event) => {
      if (event.target === overlay || event.target.closest('[data-share-close]')) {
        closeSheet();
      }
    });

    if (closeButton) {
      closeButton.addEventListener('click', () => closeSheet());
    }

    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape' && overlay.classList.contains('open')) {
        closeSheet();
      }
    });

    overlay.querySelectorAll('[data-share-action]').forEach((actionButton) => {
      actionButton.addEventListener('click', async () => {
        if (!shareSheetState || !shareSheetState.currentUrl) return;

        const currentUrl = shareSheetState.currentUrl;
        const currentTitle = shareSheetState.currentTitle || 'Job';
        const currentButton = shareSheetState.currentButton;
        const shareMessage = getShareMessage(currentTitle, currentUrl);
        const action = actionButton.getAttribute('data-share-action');

        if (action === 'whatsapp') {
          openExternalShare(`https://wa.me/?text=${encodeURIComponent(shareMessage)}`);
          showShareState(currentButton, 'Shared');
          closeSheet();
          return;
        }

        if (action === 'copy') {
          const copied = await copyTextFallback(currentUrl);
          showShareState(currentButton, copied ? 'Copied' : 'Copy Failed');
          closeSheet();
          return;
        }

        if (action === 'google') {
          openExternalShare(
            `https://mail.google.com/mail/?view=cm&fs=1&su=${encodeURIComponent(currentTitle)}&body=${encodeURIComponent(shareMessage)}`
          );
          showShareState(currentButton, 'Shared');
          closeSheet();
          return;
        }

        if (action === 'instagram') {
          const copied = await copyTextFallback(currentUrl);
          openExternalShare('https://www.instagram.com/');
          showShareState(currentButton, copied ? 'Copied + Opened' : 'Opened');
          closeSheet();
          return;
        }

        if (action === 'more') {
          if (navigator.share) {
            try {
              await navigator.share({ title: currentTitle, text: currentTitle, url: currentUrl });
              showShareState(currentButton, 'Shared');
            } catch {
              const copied = await copyTextFallback(currentUrl);
              showShareState(currentButton, copied ? 'Copied' : 'Share');
            }
          } else {
            const copied = await copyTextFallback(currentUrl);
            showShareState(currentButton, copied ? 'Copied' : 'Share');
          }
          closeSheet();
        }
      });
    });

    shareSheetState = {
      overlay,
      titleNode,
      metaNode,
      closeSheet,
      currentButton: null,
      currentTitle: '',
      currentUrl: '',
    };

    return shareSheetState;
  };

  const openShareSheet = (button, title, url) => {
    const sheet = ensureShareSheet();
    sheet.currentButton = button;
    sheet.currentTitle = title;
    sheet.currentUrl = url;
    if (sheet.titleNode) {
      sheet.titleNode.textContent = title || 'Share Job';
    }
    if (sheet.metaNode) {
      sheet.metaNode.textContent = url;
    }
    sheet.overlay.classList.add('open');
    sheet.overlay.setAttribute('aria-hidden', 'false');
  };

  document.addEventListener('click', (event) => {
    const shareButton = event.target.closest('[data-share-url]');
    if (!shareButton) return;
    event.preventDefault();
    const shareUrl = resolveShareUrl(shareButton.getAttribute('data-share-url'));
    if (!shareUrl) return;
    const shareTitle = (shareButton.getAttribute('data-share-title') || document.title || 'Job').trim();
    openShareSheet(shareButton, shareTitle, shareUrl);
  });

  const normalizePanelPath = (rawUrl) => {
    const rawValue = String(rawUrl || '').trim();
    if (!rawValue || rawValue.startsWith('#') || rawValue.startsWith('javascript:')) {
      return '';
    }
    try {
      const resolved = new URL(rawValue, window.location.origin);
      const pathname = (resolved.pathname || '').replace(/\/+$/, '');
      return pathname || '/';
    } catch {
      return '';
    }
  };

  const buildPathPrefixes = (pathValue) => {
    const normalizedPath = normalizePanelPath(pathValue);
    if (!normalizedPath) {
      return [];
    }
    if (normalizedPath === '/') {
      return ['/'];
    }
    const segments = normalizedPath.split('/').filter(Boolean);
    const prefixes = [];
    const minimumDepth = segments.length > 1 ? 2 : 1;
    for (let index = segments.length; index >= minimumDepth; index -= 1) {
      prefixes.push(`/${segments.slice(0, index).join('/')}`);
    }
    if (!prefixes.length) {
      prefixes.push(normalizedPath);
    }
    return Array.from(new Set(prefixes));
  };

  const buildSidebarNotificationTargets = () => {
    const sidebarNav = document.querySelector('.sidebar-nav');
    if (!sidebarNav) {
      return [];
    }

    const targetsByKey = new Map();
    let hostCounter = 0;

    const pushTarget = (host, rawUrl, role = 'section') => {
      if (!host) return;
      const normalizedPath = normalizePanelPath(rawUrl);
      if (!normalizedPath) {
        return;
      }
      if (!host.dataset.notificationHostId) {
        hostCounter += 1;
        host.dataset.notificationHostId = `panel-notification-host-${hostCounter}`;
      }
      const targetKey = `${host.dataset.notificationHostId}:${role}`;
      if (!targetsByKey.has(targetKey)) {
        targetsByKey.set(targetKey, {
          host,
          role,
          prefixSet: new Set(),
        });
      }
      const target = targetsByKey.get(targetKey);
      buildPathPrefixes(normalizedPath).forEach((prefix) => {
        if (prefix) {
          target.prefixSet.add(prefix);
        }
      });
    };

    const sections = Array.from(sidebarNav.querySelectorAll(':scope > .nav-section'));
    sections.forEach((section) => {
      const toggle = section.querySelector(':scope > .nav-toggle');
      const submenuLinks = Array.from(section.querySelectorAll(':scope > .nav-accordion-body a[href]'));
      if (toggle && submenuLinks.length) {
        submenuLinks.forEach((link) => {
          const linkUrl = link.getAttribute('href');
          pushTarget(toggle, linkUrl, 'section');
          pushTarget(link, linkUrl, 'submenu');
        });
        return;
      }
      if (toggle) {
        pushTarget(toggle, toggle.getAttribute('data-nav-url'), 'section');
      }
    });

    const directLinks = Array.from(sidebarNav.querySelectorAll(':scope > a.nav-item[href]'));
    directLinks.forEach((link) => {
      pushTarget(link, link.getAttribute('href'), 'section');
    });

    return Array.from(targetsByKey.values()).map((target) => ({
      host: target.host,
      role: target.role,
      prefixes: Array.from(target.prefixSet),
    }));
  };

  const sidebarNotificationTargets = buildSidebarNotificationTargets();

  const resolveSidebarNotificationHosts = (noteUrl) => {
    const normalizedPath = normalizePanelPath(noteUrl);
    if (!normalizedPath || !sidebarNotificationTargets.length) {
      return [];
    }

    let bestSectionTarget = null;
    let bestSectionScore = -1;
    let bestSubmenuTarget = null;
    let bestSubmenuScore = -1;

    sidebarNotificationTargets.forEach((target) => {
      let targetBestScore = -1;
      target.prefixes.forEach((prefix) => {
        if (!prefix) return;
        if (normalizedPath === prefix || normalizedPath.startsWith(`${prefix}/`)) {
          const score = prefix.length;
          if (score > targetBestScore) {
            targetBestScore = score;
          }
        }
      });
      if (targetBestScore < 0) return;
      if (target.role === 'submenu') {
        if (targetBestScore > bestSubmenuScore) {
          bestSubmenuScore = targetBestScore;
          bestSubmenuTarget = target;
        }
        return;
      }
      if (targetBestScore > bestSectionScore) {
        bestSectionScore = targetBestScore;
        bestSectionTarget = target;
      }
    });

    const hosts = [];
    if (bestSectionTarget?.host) {
      hosts.push(bestSectionTarget.host);
    }
    if (bestSubmenuTarget?.host && !hosts.includes(bestSubmenuTarget.host)) {
      hosts.push(bestSubmenuTarget.host);
    }
    return hosts;
  };

  const clearSidebarSectionBadges = () => {
    sidebarNotificationPlaceholders.forEach((badge) => {
      if (!badge) return;
      badge.textContent = '0';
      badge.style.display = 'none';
    });
    document.querySelectorAll('[data-dynamic-sidebar-badge]').forEach((badge) => {
      badge.remove();
    });
  };

  const setSidebarHostBadgeCount = (host, count) => {
    if (!host || count < 1) {
      return;
    }
    let badge = host.querySelector('[data-sidebar-notification-count]');
    if (!badge) {
      badge = host.querySelector('[data-dynamic-sidebar-badge]');
    }
    if (!badge) {
      badge = document.createElement('span');
      badge.className = 'nav-count-badge nav-section-count-badge';
      badge.setAttribute('data-dynamic-sidebar-badge', '');
      const badgeContainer = host.querySelector('.nav-label') || host;
      badgeContainer.appendChild(badge);
    }
    badge.textContent = String(count);
    badge.style.display = '';
  };

  const updateSidebarSectionBadges = (items) => {
    clearSidebarSectionBadges();
    // Sidebar notification counters are intentionally disabled across all panels.
    void items;
  };

  const renderPanelNotificationItems = (items) => {
    if (!panelNotificationRoot) return;
    const menu = panelNotificationRoot.querySelector('.notification-menu');
    if (!menu) return;

    let list = menu.querySelector('[data-panel-notification-list]');
    if (!list) {
      list = document.createElement('ul');
      list.className = 'notification-list';
      list.setAttribute('data-panel-notification-list', '');
      const heading = menu.querySelector('h4');
      if (heading && heading.nextSibling) {
        menu.insertBefore(list, heading.nextSibling);
      } else {
        menu.appendChild(list);
      }
    }

    let empty = menu.querySelector('[data-panel-notification-empty]');
    if (!empty) {
      empty = document.createElement('p');
      empty.className = 'muted';
      empty.setAttribute('data-panel-notification-empty', '');
      empty.textContent = 'No notifications yet.';
      menu.appendChild(empty);
    }

    const rows = Array.isArray(items) ? items : [];
    if (!rows.length) {
      list.innerHTML = '';
      list.style.display = 'none';
      empty.style.display = '';
      return;
    }

    list.innerHTML = rows
      .map((item) => {
        const noteId = escapeHtml(String(item.id || '').trim());
        const title = escapeHtml(item.title || 'Notification');
        const message = escapeHtml(item.message || '');
        const meta = item.created_label
          ? `<div class="notification-card-meta">${escapeHtml(item.created_label)}</div>`
          : '';
        const unreadDot = item.unread ? '<span class="notification-card-dot" aria-hidden="true"></span>' : '';
        const body = `<div class="notification-card-body"><div class="notification-card-title-row">${unreadDot}<strong class="notification-card-title">${title}</strong></div><div class="notification-card-message">${message}</div>${meta}</div>`;
        if (item.url) {
          return `<li class="notification-item" data-note-id="${noteId}"><a href="${escapeHtml(item.url)}" class="notification-card action-link" data-note-id="${noteId}">${body}</a></li>`;
        }
        return `<li class="notification-item" data-note-id="${noteId}"><div class="notification-card notification-card-static">${body}</div></li>`;
      })
      .join('');
    list.style.display = 'grid';
    empty.style.display = 'none';
  };

  const ensurePanelNotificationActions = () => {
    if (!panelNotificationRoot) return {};
    const menu = panelNotificationRoot.querySelector('.notification-menu');
    if (!menu) return {};

    let actions = menu.querySelector('[data-panel-notification-actions]');
    if (!actions) {
      actions = document.createElement('div');
      actions.className = 'panel-notification-actions';
      actions.setAttribute('data-panel-notification-actions', '');
      menu.appendChild(actions);
    }

    let viewAllLink = actions.querySelector('[data-panel-notification-view-all]');
    if (!viewAllLink) {
      const existingLink = Array.from(menu.querySelectorAll('a.action-link')).find(
        (link) => !link.closest('[data-panel-notification-list]')
      );
      if (existingLink) {
        const previousParent = existingLink.parentElement;
        existingLink.setAttribute('data-panel-notification-view-all', '');
        actions.appendChild(existingLink);
        if (
          previousParent &&
          previousParent !== menu &&
          previousParent.children.length === 0
        ) {
          previousParent.remove();
        }
        viewAllLink = existingLink;
      }
    }

    let readAllButton = actions.querySelector('[data-panel-notification-read-all]');
    if (!readAllButton) {
      readAllButton = document.createElement('button');
      readAllButton.type = 'button';
      readAllButton.className = 'notification-action-btn';
      readAllButton.textContent = 'Read all';
      readAllButton.setAttribute('data-panel-notification-read-all', '');
      actions.appendChild(readAllButton);
    }

    return { actions, viewAllLink, readAllButton };
  };

  let panelNotificationPollHandle = null;
  const markNotificationItemsSeen = (ids) => {
    const cleaned = Array.from(
      new Set(
        (Array.isArray(ids) ? ids : [])
          .map((value) => String(value || '').trim())
          .filter((value) => Boolean(value))
      )
    );
    if (!cleaned.length) {
      return Promise.resolve(null);
    }
    const query = `?mark_item_ids=${encodeURIComponent(cleaned.join(','))}`;
    return fetch(`${panelNotificationsApiUrl}${query}`, {
      credentials: 'same-origin',
      keepalive: true,
      headers: {
        'X-Requested-With': 'XMLHttpRequest',
      },
    }).catch(() => null);
  };

  const refreshPanelNotifications = (markSeen = false) => {
    const query = markSeen ? '?mark_seen=1' : '';
    return fetch(`${panelNotificationsApiUrl}${query}`, {
      credentials: 'same-origin',
      headers: {
        'X-Requested-With': 'XMLHttpRequest',
      },
    })
      .then((response) => (response.ok ? response.json() : null))
      .then((data) => {
        if (!data || !data.success) return;
        const notificationUnread = Number(data.unread_count || 0);
        const messageUnread = Number(data.message_unread_count || 0);
        const rows = Array.isArray(data.items) ? data.items : [];
        setCountBadges(panelNotificationCountBadges, notificationUnread);
        setCountBadges(panelMessageCountBadges, messageUnread);
        if (panelNotificationRoot) {
          renderPanelNotificationItems(rows);
        }
        updateSidebarSectionBadges(rows);
        return data;
      })
      .catch(() => null);
  };

  const applyPlatformLogo = (logoUrl) => {
    const normalizedUrl = String(logoUrl || '').trim();
    const brandImages = document.querySelectorAll('.brand-mark img');
    if (!brandImages.length) return;
    brandImages.forEach((img) => {
      if (!img) return;
      if (!img.dataset.defaultSrc) {
        img.dataset.defaultSrc = img.getAttribute('src') || '';
      }
      if (normalizedUrl) {
        if (img.getAttribute('src') !== normalizedUrl) {
          img.setAttribute('src', normalizedUrl);
        }
      } else if (img.dataset.defaultSrc && img.getAttribute('src') !== img.dataset.defaultSrc) {
        img.setAttribute('src', img.dataset.defaultSrc);
      }
    });
  };

  const refreshPlatformBranding = () =>
    fetch(platformBrandingApiUrl, {
      credentials: 'same-origin',
      headers: {
        'X-Requested-With': 'XMLHttpRequest',
      },
    })
      .then((response) => (response.ok ? response.json() : null))
      .then((data) => {
        if (!data || !data.success) return;
        applyPlatformLogo(data.logo_url || '');
      })
      .catch(() => null);

  const shouldEnablePanelNotifications = Boolean(
    panelNotificationRoot ||
      (panelNotificationCountBadges && panelNotificationCountBadges.length) ||
      (panelMessageCountBadges && panelMessageCountBadges.length) ||
      (sidebarNotificationPlaceholders && sidebarNotificationPlaceholders.length) ||
      (sidebarNotificationTargets && sidebarNotificationTargets.length)
  );

  refreshPlatformBranding();
  setInterval(() => {
    if (document.hidden) return;
    refreshPlatformBranding();
  }, 45000);

  if (shouldEnablePanelNotifications) {
    const { readAllButton } = panelNotificationRoot ? ensurePanelNotificationActions() : {};
    if (readAllButton) {
      readAllButton.addEventListener('click', () => {
        const originalText = readAllButton.textContent;
        readAllButton.disabled = true;
        readAllButton.textContent = 'Marking...';
        refreshPanelNotifications(true).finally(() => {
          readAllButton.disabled = false;
          readAllButton.textContent = originalText;
        });
      });
    }

    if (panelNotificationRoot) {
      panelNotificationRoot.addEventListener('click', (event) => {
        const actionLink = event.target.closest('[data-panel-notification-list] a[href][data-note-id]');
        if (!actionLink) return;
        const noteId = String(actionLink.getAttribute('data-note-id') || '').trim();
        if (noteId) {
          markNotificationItemsSeen([noteId]);
        }
      });
      panelNotificationRoot.addEventListener('toggle', () => {
        if (panelNotificationRoot.open) {
          refreshPanelNotifications(false);
        }
      });
    }

    const startPanelNotificationPolling = () => {
      if (panelNotificationPollHandle) return;
      panelNotificationPollHandle = setInterval(() => {
        if (!document.hidden) {
          refreshPanelNotifications(false);
        }
      }, 15000);
    };
    const stopPanelNotificationPolling = () => {
      if (!panelNotificationPollHandle) return;
      clearInterval(panelNotificationPollHandle);
      panelNotificationPollHandle = null;
    };

    refreshPanelNotifications(false);
    startPanelNotificationPolling();
    document.addEventListener('visibilitychange', () => {
      if (document.hidden) {
        stopPanelNotificationPolling();
      } else {
        refreshPanelNotifications(false);
        startPanelNotificationPolling();
      }
    });
  }

  const tourDescriptionMap = {
    dashboard:
      'Use this dashboard to monitor platform activity at a glance. You can review key KPIs, check trend charts, and jump to the most-used actions without opening multiple pages.',
    'job search':
      'Search jobs using role, skills, experience, location, and salary filters. Open each result to review details, save it for later, or continue directly to the application flow.',
    'saved jobs':
      'This section keeps your shortlisted opportunities in one place. It is useful for comparing roles, tracking priorities, and applying when your profile is ready.',
    'my applications':
      'Track every submitted application with its current stage. You can quickly identify pending responses, interview calls, selected outcomes, and rejected entries.',
    interviews:
      'Review upcoming and completed interviews, along with dates and statuses. Use it to stay prepared, avoid missed schedules, and follow outcomes after each round.',
    messages:
      'Manage your hiring conversations in a single inbox. You can respond to recruiters, share updates, and keep communication history organized by thread.',
    'my profile':
      'Update your personal information, headline, bio, preferences, and contact details. A complete profile improves visibility and increases trust with recruiters.',
    'resume manager':
      'Upload, replace, and maintain multiple resume versions for different roles. You can keep documents current and switch to the most relevant version quickly.',
    feedbacks:
      'Read structured feedback from users and internal teams. This helps you spot quality issues, prioritize fixes, and improve hiring outcomes over time.',
    subscription:
      'Check your current plan, usage limits, renewal timeline, and upgrade options. You can also verify billing status and avoid service interruptions.',
    settings:
      'Control account preferences, privacy behavior, notification settings, and security options. Use this section to personalize your panel experience safely.',
    support:
      'Create and track support requests with clear status updates. You can follow resolution progress, add context, and continue communication in one place.',
    'company profile':
      'Maintain company branding, business details, and public profile information. Keeping this section accurate improves trust and application quality.',
    'job management':
      'This is your central workspace for creating, editing, and monitoring jobs. You can manage lifecycle states, review responses, and keep hiring pipelines active.',
    'post new job':
      'Create a new vacancy by defining role details, requirements, and screening information. Clear and complete job data improves candidate relevance.',
    'all jobs':
      'Review your complete job inventory across all statuses. Use filters and quick actions to inspect performance, edit details, or update job state.',
    'all posted jobs':
      'See every published job in one list with status and response signals. This helps you compare campaigns and decide where immediate action is needed.',
    'active jobs':
      'Focus on currently live jobs receiving applications. Monitor engagement and update content to keep hiring momentum strong.',
    'draft jobs':
      'Continue incomplete job drafts before publishing. This section is useful when multiple stakeholders review job details before launch.',
    'paused jobs':
      'Manage paused openings and restart them whenever hiring resumes. It helps preserve previous setup without rebuilding the job from scratch.',
    'rejected jobs':
      'Review rejected listings with remarks and required corrections. Update details as suggested and submit again for approval.',
    'expired jobs':
      'Check jobs that ended due to timeline or plan limits. Re-open relevant roles or duplicate them for a fresh campaign.',
    'closed jobs':
      'Access closed positions for historical review and audit. Useful when comparing hiring timelines and documenting completed mandates.',
    'archived jobs':
      'Store inactive jobs for compliance and reporting reference. Archived records remain available without cluttering active lists.',
    applications:
      'Review candidate applications with profile data, notes, and status actions. This is where you move applicants through each hiring stage.',
    'communication center':
      'Launch outbound communication campaigns from one place. Manage email, SMS, and WhatsApp outreach with trackable delivery flow.',
    'bulk email':
      'Create and send rich email campaigns to selected audiences. Ideal for interview invites, announcements, and structured hiring updates.',
    'bulk sms':
      'Send concise SMS messages for urgent alerts and reminders. Great for time-sensitive communication when instant visibility is needed.',
    notifications:
      'Publish in-panel notifications so users see updates after login. Use this for product changes, operational alerts, or important announcements.',
    'whatsapp alerts':
      'Deliver candidate and user updates through approved WhatsApp messaging flows. This channel improves reach for high-priority reminders.',
    'in-app notifications':
      'Manage alerts displayed inside the product interface. You can target specific audiences and control messaging frequency.',
    'message templates':
      'Create reusable communication templates for faster execution and consistency. Templates reduce manual effort and lower messaging errors.',
    'sent history':
      'Audit previously sent campaigns with time, channel, and delivery context. Use it for compliance checks and campaign optimization.',
    'scheduled messages':
      'Plan campaigns in advance and trigger them at the ideal time. This improves coordination and keeps outreach consistent.',
    reports:
      'Analyze recruitment trends, funnel movement, and operational performance. Use report insights to make data-backed decisions.',
    'reports & analytics':
      'Deep-dive into conversion metrics, source quality, and hiring bottlenecks. This section supports strategic planning and performance reviews.',
    'billing / subscription':
      'Manage invoices, plan status, payment cycles, and billing history. Keep billing details current to ensure uninterrupted platform access.',
    grievance:
      'Track reported issues from users and monitor investigation progress. This helps maintain platform safety and policy adherence.',
    security:
      'Review account access patterns, login signals, and security controls. Use this area to strengthen account protection and audit readiness.',
    'customer support':
      'Handle support workflows from ticket intake to closure. Prioritize urgent requests and maintain response quality with clear ownership.',
    'assigned jobs':
      'Review jobs assigned to your team and update progress quickly. This view helps coordinate responsibilities across hiring partners.',
    'candidate pool':
      'Manage candidate records, shortlist quality talent, and prepare submissions. Keep profiles updated to improve placement speed.',
    shortlisted:
      'Access shortlisted candidates ready for evaluation or interview scheduling. This reduces search time during active hiring phases.',
    placements:
      'Track selected candidates through offer, joining, and final placement status. Use this to monitor delivery performance end to end.',
    'earnings / commission':
      'Monitor commission entries, payout timelines, and earnings summaries. Useful for finance tracking and reconciliation.',
    'profile & settings':
      'Update organization profile details, branding, and operational preferences. This keeps your panel accurate and aligned with team needs.',
    'user management':
      'Manage all registered user segments from a single section. You can review account status, take admin actions, and maintain data quality.',
    companies:
      'View all registered company accounts with their key details and activity context. Use this page for account oversight and verification.',
    consultancies:
      'Review consultancy accounts, partnership status, and profile completeness. This helps maintain a strong and compliant partner network.',
    candidates:
      'Access candidate account records, profile quality, and engagement status. Use it to support users and maintain a healthy talent database.',
    'application management':
      'Track platform-wide application flow from submission to final outcome. This gives you a complete view of hiring pipeline health.',
    'all applications':
      'See every application in one queue with status and user context. Filter quickly to process approvals, follow-ups, and escalations.',
    'interview scheduled':
      'Focus on applications with confirmed interview timelines. Use this view to monitor no-shows, reschedules, and candidate progression.',
    selected:
      'Review candidates marked as selected in the hiring workflow. Verify final actions and move forward with onboarding or offers.',
    rejected:
      'Track rejected applications and maintain proper records for audit. You can also use trends here to improve future shortlisting quality.',
    'offer issued':
      'Monitor applications where offers have been generated and shared. This helps track conversion from selection to joining.',
    'subscription & billing':
      'Control subscription plans, pricing structures, and billing policies across the platform. Keep plan logic aligned with business strategy.',
    overview:
      'Get a summary of plan distribution, billing health, and top-level subscription metrics. Use this as the starting point for billing reviews.',
    'who is free / paid':
      'Segment users by plan type to understand monetization coverage. This helps identify upgrade opportunities and retention focus areas.',
    'expiry alerts':
      'Track upcoming subscription expiries to trigger timely reminders. Proactive follow-up reduces churn and service disruption.',
    'revenue charts':
      'Analyze revenue trends and recurring income performance with visual breakdowns. Useful for monthly and quarterly reviews.',
    'manual plan assign':
      'Assign or adjust subscription plans manually in approved scenarios. Use carefully to support operations and exceptions.',
    'advertisement management':
      'Manage advertisement inventory, visibility rules, and campaign activity from one place. This supports promotion strategy and monetization.',
    'communication management':
      'Control communication tools, delivery workflows, and reusable messaging resources. Keep outbound communication consistent and compliant.',
    'support center':
      'This section groups all support workflows, queues, and service insights. Use it to manage load, response time, and quality.',
    'support dashboard':
      'Monitor live support health with ticket volume, SLA posture, and queue movement. It gives a quick operational snapshot.',
    'all tickets':
      'View the complete support ticket list with filters and status controls. Useful for bulk review and team coordination.',
    'high priority':
      'Focus on urgent tickets that need immediate attention. This helps reduce critical delays and escalation risk.',
    'assigned tickets':
      'Track tickets currently owned by support team members. Use this to balance workload and avoid missed follow-up.',
    unassigned:
      'Review tickets waiting for ownership and route them quickly. Fast assignment improves first response performance.',
    closed:
      'Access resolved tickets for audits, quality review, and knowledge reuse. Closed history helps improve support playbooks.',
    'support analytics':
      'Analyze support performance trends, resolution times, and customer outcomes. Use insights to refine staffing and workflows.',
    'grievance reports':
      'Review sensitive reports and policy violations in a structured queue. This section supports fair investigation and resolution tracking.',
    'grievance / reports':
      'Handle complaints and abuse reports with clear status movement and audit traceability. This protects user trust and platform integrity.',
    'user complaints':
      'Review complaints submitted by users and update each case with actions taken. Keep communication and resolution notes clear.',
    'job reports':
      'Investigate jobs reported for policy issues, spam, or misleading content. Take corrective action and document outcomes.',
    'abuse / fraud':
      'Track abuse and fraud signals requiring stricter review. This section supports rapid enforcement and risk reduction.',
    'resolution log':
      'Maintain an auditable record of grievance decisions and closure notes. Useful for compliance and internal review.',
    'security & audit':
      'Monitor security signals and admin actions across the platform. This section helps enforce governance and maintain accountability.',
    'login history':
      'Review login timelines and device patterns to detect unusual access. Use this for proactive account safety checks.',
    'ip logs':
      'Inspect IP-level activity records for diagnostics and security monitoring. Useful during investigations and access validation.',
    'admin activity logs':
      'Track who changed what and when at the admin level. This supports transparent operations and forensic auditing.',
    'role permissions':
      'Manage role-based access controls for sub-admins and internal teams. Keep permissions least-privilege and role-appropriate.',
    'platform settings':
      'Configure global platform behavior, defaults, and governance options. Changes here affect broad system behavior, so review carefully.',
    'job categories':
      'Maintain standardized job category taxonomy used across postings and filters. Clean categories improve search accuracy.',
    locations:
      'Manage location master data for jobs and user preferences. Accurate locations improve matching and reporting quality.',
    'skills library':
      'Curate the central skills catalog used in profiles and job requirements. A clean skills library improves matching precision.',
    'experience levels':
      'Define experience bands for consistent role tagging and candidate screening. This improves filtering and decision quality.',
    'sub-admin':
      'Manage sub-admin setup and access governance from this section. It keeps delegated operations controlled and auditable.',
    'add new sub-admin':
      'Create a new sub-admin account with the correct role and permissions. Use this for controlled delegation of admin responsibilities.',
    'sub-admin table':
      'Review existing sub-admin users, assigned roles, and access posture. This helps maintain permission hygiene over time.',
    'delete data':
      'Use controlled data cleanup tools for approved privacy and maintenance tasks. Always verify scope before executing deletion actions.',
  };

  const normalizeTourKey = (value) =>
    (value || '')
      .toString()
      .trim()
      .toLowerCase()
      .replace(/\s+/g, ' ');

  const sidebarTourDescription = (label, node) => {
    const normalized = normalizeTourKey(label);
    if (tourDescriptionMap[normalized]) {
      return tourDescriptionMap[normalized];
    }
    if (node?.classList?.contains('nav-toggle')) {
      const sectionBody = node.closest('.nav-section')?.querySelector(':scope > .nav-accordion-body');
      const sectionLinks = sectionBody
        ? Array.from(sectionBody.querySelectorAll(':scope > .nav-sub'))
            .map((link) => (link.textContent || '').replace(/\s+/g, ' ').trim())
            .filter(Boolean)
        : [];
      if (sectionLinks.length) {
        const preview = sectionLinks.slice(0, 3).join(', ');
        const extraCount = Math.max(0, sectionLinks.length - 3);
        const suffix = extraCount > 0 ? `, and ${extraCount} more pages` : '';
        return `This section groups related tools under ${label}. Open it to access ${preview}${suffix}, then manage tasks without leaving the sidebar workflow.`;
      }
      return `This section groups related tools under ${label}. Expand it to review all available actions and quickly open the page you need.`;
    }
    if (node?.classList?.contains('nav-sub')) {
      return `Open ${label} to manage this workflow with full controls, filters, and status updates. This page is designed for detailed operations rather than quick shortcuts.`;
    }
    return `Open ${label} to access the complete workspace for this feature. You can review data, take actions, and continue related tasks from this section.`;
  };

  const getSidebarTourLabel = (node) => {
    if (!node) return '';
    if (node.classList.contains('nav-sub')) {
      return (node.textContent || '').replace(/\s+/g, ' ').trim();
    }
    if (node.classList.contains('nav-toggle')) {
      const labelNode = node.querySelector('.nav-label > span:not(.nav-icon):not(.nav-count-badge)');
      return (labelNode?.textContent || node.textContent || '').replace(/\s+/g, ' ').trim();
    }
    const directLabel = node.querySelector(':scope > span:not(.nav-icon):not(.nav-count-badge)');
    return (directLabel?.textContent || node.textContent || '').replace(/\s+/g, ' ').trim();
  };

  const buildProfileTourDescription = () => {
    const sidebarProfileNode = document.querySelector('.sidebar .company-user');
    const profileSummaryNode = document.querySelector('.profile-summary');
    const profileName = (
      sidebarProfileNode?.querySelector('.company-user-meta strong')?.textContent ||
      profileSummaryNode?.querySelector('.profile-meta strong')?.textContent ||
      ''
    )
      .replace(/\s+/g, ' ')
      .trim();
    const profileRole = (
      sidebarProfileNode?.querySelector('.company-user-meta span')?.textContent ||
      profileSummaryNode?.querySelector('.profile-meta span')?.textContent ||
      ''
    )
      .replace(/\s+/g, ' ')
      .trim();
    const profileCompletion = (sidebarProfileNode?.querySelector('.profile-progress-text')?.textContent || '')
      .replace(/\s+/g, ' ')
      .trim();
    const profileMenuActions = Array.from(document.querySelectorAll('.profile-menu .menu-item'))
      .map((node) => (node.textContent || '').replace(/\s+/g, ' ').trim())
      .filter(Boolean)
      .slice(0, 4);

    const details = [
      profileName
        ? `Welcome ${profileName}! This profile area is your personal control center where you can verify account identity, monitor profile completeness, and access account-level actions securely.`
        : 'Welcome to your profile! This profile area is your personal control center where you can verify account identity, monitor profile completeness, and access account-level actions securely.',
    ];
    if (profileRole) {
      details.push(`Your current role is shown as ${profileRole}, so you always know which panel permissions are active.`);
    }
    if (profileCompletion) {
      details.push(`The completion indicator currently shows ${profileCompletion}, which helps you understand how ready your account setup is.`);
    }
    if (profileMenuActions.length) {
      details.push(`From the profile menu you can quickly use options like ${profileMenuActions.join(', ')} without searching in multiple pages.`);
    }
    details.push(
      'Start the tour from here to understand every section in order, then use the sidebar menu to move between modules with full context.'
    );
    return details.join(' ');
  };

  const collectProfileTourStep = () => {
    const targetNode =
      document.querySelector('.sidebar .company-user') ||
      document.querySelector('.topbar .profile-summary') ||
      document.querySelector('.profile-summary');
    if (!targetNode) return null;
    return {
      node: targetNode,
      label: 'Explore Your Profile',
      description: buildProfileTourDescription(),
    };
  };

  const collectSidebarTourSteps = () => {
    const sidebarNav = document.querySelector('.sidebar .sidebar-nav');
    const steps = [];
    const profileStep = collectProfileTourStep();
    if (profileStep) {
      steps.push(profileStep);
    }
    if (!sidebarNav) return steps;
    const nodes = Array.from(sidebarNav.querySelectorAll('.nav-item, .nav-sub'));
    nodes.forEach((node) => {
      const label = getSidebarTourLabel(node);
      if (!label) return;
      if (label.toLowerCase() === 'v') return;
      steps.push({
        node,
        label,
        description: sidebarTourDescription(label, node),
      });
    });
    return steps;
  };

  const ensureTakeTourButton = () => {
    const actionBar = document.querySelector('.top-actions');
    if (!actionBar) return null;
    let button = actionBar.querySelector('[data-take-tour-trigger]');
    if (button) return button;
    button = document.createElement('button');
    button.type = 'button';
    button.className = 'take-tour-btn';
    button.setAttribute('data-take-tour-trigger', '');
    button.setAttribute('aria-label', 'Take a Tour');
    button.textContent = 'Take a Tour';
    const anchor = actionBar.querySelector('.fullscreen-toggle') || actionBar.firstElementChild || null;
    if (anchor && anchor.nextSibling) {
      actionBar.insertBefore(button, anchor.nextSibling);
    } else {
      actionBar.appendChild(button);
    }
    return button;
  };

  const ensureTourOverlay = () => {
    let overlayNode = document.querySelector('[data-sidebar-tour-overlay]');
    if (overlayNode) return overlayNode;
    overlayNode = document.createElement('div');
    overlayNode.className = 'sidebar-tour-overlay';
    overlayNode.setAttribute('data-sidebar-tour-overlay', '');
    overlayNode.setAttribute('hidden', '');
    overlayNode.innerHTML = `
      <div class="sidebar-tour-modal" role="dialog" aria-modal="true" aria-live="polite">
        <button type="button" class="sidebar-tour-close" data-tour-close aria-label="Close tour">&times;</button>
        <h3 class="sidebar-tour-title" data-tour-title>Section Title</h3>
        <p class="sidebar-tour-text" data-tour-text>Section details</p>
        <div class="sidebar-tour-progress-track">
          <span data-tour-progress></span>
        </div>
        <div class="sidebar-tour-footer">
          <button type="button" class="sidebar-tour-skip" data-tour-skip>Skip tour</button>
          <span class="sidebar-tour-step" data-tour-step>1/1</span>
          <div class="sidebar-tour-actions">
            <button type="button" class="tour-btn tour-btn-ghost" data-tour-prev>Previous</button>
            <button type="button" class="tour-btn tour-btn-primary" data-tour-next>Next</button>
          </div>
        </div>
      </div>
    `;
    document.body.appendChild(overlayNode);
    return overlayNode;
  };

  const startSidebarTour = (() => {
    let steps = [];
    let index = 0;
    let overlayNode = null;
    let highlightedNode = null;
    let openedPeekByTour = false;
    let openedMobileSidebarByTour = false;
    let sectionStateSnapshot = [];
    const tourPlacementClasses = ['placement-right', 'placement-left', 'placement-top', 'placement-bottom', 'placement-mobile'];

    const clamp = (value, minimum, maximum) => Math.min(maximum, Math.max(minimum, value));

    const clearTourModalPlacement = () => {
      if (!overlayNode) return;
      const modalNode = overlayNode.querySelector('.sidebar-tour-modal');
      if (!modalNode) return;
      modalNode.classList.remove(...tourPlacementClasses);
      modalNode.style.removeProperty('left');
      modalNode.style.removeProperty('top');
      modalNode.style.removeProperty('bottom');
      modalNode.style.removeProperty('--tour-arrow-offset');
    };

    const positionTourModal = (targetNode) => {
      if (!overlayNode || !targetNode) return;
      const modalNode = overlayNode.querySelector('.sidebar-tour-modal');
      if (!modalNode) return;

      modalNode.classList.remove(...tourPlacementClasses);
      modalNode.style.removeProperty('left');
      modalNode.style.removeProperty('top');
      modalNode.style.removeProperty('bottom');
      modalNode.style.removeProperty('--tour-arrow-offset');

      const viewportWidth = window.innerWidth;
      const viewportHeight = window.innerHeight;
      const viewportPadding = 14;
      const gap = 18;

      if (isMobile()) {
        modalNode.classList.add('placement-mobile');
        modalNode.style.left = `${viewportPadding}px`;
        modalNode.style.bottom = `${viewportPadding}px`;
        return;
      }

      const targetRect = targetNode.getBoundingClientRect();
      const modalRect = modalNode.getBoundingClientRect();
      const modalWidth = modalRect.width;
      const modalHeight = modalRect.height;

      const availableSpace = {
        right: viewportWidth - targetRect.right - viewportPadding - gap,
        left: targetRect.left - viewportPadding - gap,
        bottom: viewportHeight - targetRect.bottom - viewportPadding - gap,
        top: targetRect.top - viewportPadding - gap,
      };
      const fits = {
        right: availableSpace.right >= modalWidth,
        left: availableSpace.left >= modalWidth,
        bottom: availableSpace.bottom >= modalHeight,
        top: availableSpace.top >= modalHeight,
      };

      const preferredPlacements = ['right', 'left', 'bottom', 'top'];
      let placement = preferredPlacements.find((candidate) => fits[candidate]);
      if (!placement) {
        placement = preferredPlacements.reduce((best, current) =>
          availableSpace[current] > availableSpace[best] ? current : best
        );
      }

      let left = viewportPadding;
      let top = viewportPadding;
      if (placement === 'right') {
        left = targetRect.right + gap;
        top = targetRect.top + targetRect.height / 2 - modalHeight / 2;
      } else if (placement === 'left') {
        left = targetRect.left - modalWidth - gap;
        top = targetRect.top + targetRect.height / 2 - modalHeight / 2;
      } else if (placement === 'bottom') {
        left = targetRect.left + targetRect.width / 2 - modalWidth / 2;
        top = targetRect.bottom + gap;
      } else {
        left = targetRect.left + targetRect.width / 2 - modalWidth / 2;
        top = targetRect.top - modalHeight - gap;
      }

      const maxLeft = Math.max(viewportPadding, viewportWidth - modalWidth - viewportPadding);
      const maxTop = Math.max(viewportPadding, viewportHeight - modalHeight - viewportPadding);
      left = clamp(left, viewportPadding, maxLeft);
      top = clamp(top, viewportPadding, maxTop);

      modalNode.style.left = `${left}px`;
      modalNode.style.top = `${top}px`;
      modalNode.classList.add(`placement-${placement}`);

      if (placement === 'right' || placement === 'left') {
        const arrowOffset = clamp(targetRect.top + targetRect.height / 2 - top, 24, modalHeight - 24);
        modalNode.style.setProperty('--tour-arrow-offset', `${arrowOffset}px`);
      } else {
        const arrowOffset = clamp(targetRect.left + targetRect.width / 2 - left, 24, modalWidth - 24);
        modalNode.style.setProperty('--tour-arrow-offset', `${arrowOffset}px`);
      }
    };

    const handleTourViewportChange = () => {
      if (!steps.length) return;
      const step = steps[index];
      if (!step) return;
      positionTourModal(step.node);
    };

    const captureSectionState = () => {
      sectionStateSnapshot = Array.from(document.querySelectorAll('.nav-section')).map((section) => ({
        section,
        open: section.classList.contains('open'),
      }));
    };

    const restoreSectionState = () => {
      sectionStateSnapshot.forEach(({ section, open }) => {
        if (!section || !section.isConnected) return;
        const toggleButton = section.querySelector(':scope > .nav-toggle');
        const body = section.querySelector(':scope > .nav-accordion-body');
        section.classList.toggle('open', open);
        if (toggleButton) {
          toggleButton.setAttribute('aria-expanded', String(open));
        }
        if (body) {
          body.style.display = open ? 'block' : '';
          body.style.maxHeight = '';
          body.style.overflow = '';
        }
      });
    };

    const clearHighlight = () => {
      if (!highlightedNode) return;
      highlightedNode.classList.remove('tour-highlight-target');
      highlightedNode = null;
    };

    const closeTour = () => {
      clearHighlight();
      if (overlayNode) {
        overlayNode.classList.remove('open');
        overlayNode.setAttribute('hidden', '');
      }
      window.removeEventListener('resize', handleTourViewportChange);
      window.removeEventListener('orientationchange', handleTourViewportChange);
      document.removeEventListener('scroll', handleTourViewportChange, true);
      clearTourModalPlacement();
      if (openedPeekByTour) {
        setSidebarPeekOpen(false);
      }
      if (openedMobileSidebarByTour) {
        closeMobileSidebar();
      }
      restoreSectionState();
      openedPeekByTour = false;
      openedMobileSidebarByTour = false;
      document.body.classList.remove('sidebar-tour-active');
      steps = [];
      index = 0;
    };

    const ensureNodeVisible = (node) => {
      if (!node) return;
      const parentSection = node.closest('.nav-section');
      if (parentSection && !parentSection.classList.contains('open')) {
        const toggleButton = parentSection.querySelector(':scope > .nav-toggle');
        parentSection.classList.add('open');
        if (toggleButton) {
          toggleButton.setAttribute('aria-expanded', 'true');
        }
        animateAccordion(parentSection, true);
      }
      node.scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'nearest' });
    };

    const renderStep = () => {
      if (!overlayNode || !steps.length) return;
      const step = steps[index];
      const titleEl = overlayNode.querySelector('[data-tour-title]');
      const textEl = overlayNode.querySelector('[data-tour-text]');
      const stepEl = overlayNode.querySelector('[data-tour-step]');
      const progressEl = overlayNode.querySelector('[data-tour-progress]');
      const prevBtn = overlayNode.querySelector('[data-tour-prev]');
      const nextBtn = overlayNode.querySelector('[data-tour-next]');
      if (!step || !titleEl || !textEl || !stepEl || !progressEl || !prevBtn || !nextBtn) return;

      clearHighlight();
      ensureNodeVisible(step.node);
      step.node.classList.add('tour-highlight-target');
      highlightedNode = step.node;

      titleEl.textContent = step.label;
      textEl.textContent = step.description;
      stepEl.textContent = `${index + 1}/${steps.length}`;
      progressEl.style.width = `${((index + 1) / steps.length) * 100}%`;
      prevBtn.disabled = index === 0;
      nextBtn.textContent = index === steps.length - 1 ? 'Finish' : 'Next';
      positionTourModal(step.node);
      window.setTimeout(() => {
        const activeStep = steps[index];
        if (!activeStep || activeStep.node !== step.node) return;
        positionTourModal(step.node);
      }, 260);
    };

    const goNext = () => {
      if (!steps.length) return;
      if (index >= steps.length - 1) {
        closeTour();
        return;
      }
      index += 1;
      renderStep();
    };

    const goPrev = () => {
      if (!steps.length || index === 0) return;
      index -= 1;
      renderStep();
    };

    return () => {
      steps = collectSidebarTourSteps();
      if (!steps.length) return;
      overlayNode = ensureTourOverlay();
      if (!overlayNode) return;

      captureSectionState();
      document.body.classList.add('sidebar-tour-active');
      if (isMobile() && !document.body.classList.contains('sidebar-open')) {
        document.body.classList.add('sidebar-open');
        toggles.forEach((btn) => btn.setAttribute('aria-expanded', 'true'));
        openedMobileSidebarByTour = true;
      }
      if (!isMobile() && document.body.classList.contains('sidebar-collapsed') && !document.body.classList.contains('sidebar-peek-open')) {
        setSidebarPeekOpen(true);
        openedPeekByTour = true;
      }

      overlayNode.removeAttribute('hidden');
      overlayNode.classList.add('open');
      index = 0;
      window.addEventListener('resize', handleTourViewportChange);
      window.addEventListener('orientationchange', handleTourViewportChange);
      document.addEventListener('scroll', handleTourViewportChange, true);
      renderStep();

      const closeBtn = overlayNode.querySelector('[data-tour-close]');
      const skipBtn = overlayNode.querySelector('[data-tour-skip]');
      const nextBtn = overlayNode.querySelector('[data-tour-next]');
      const prevBtn = overlayNode.querySelector('[data-tour-prev]');
      if (closeBtn) closeBtn.onclick = closeTour;
      if (skipBtn) skipBtn.onclick = closeTour;
      if (nextBtn) nextBtn.onclick = goNext;
      if (prevBtn) prevBtn.onclick = goPrev;

      overlayNode.onclick = (event) => {
        if (event.target === overlayNode) {
          closeTour();
        }
      };
    };
  })();

  const takeTourButton = ensureTakeTourButton();
  if (takeTourButton) {
    takeTourButton.addEventListener('click', () => {
      startSidebarTour();
    });
  }

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
    if (event.key !== 'Escape') return;
    if (document.body.classList.contains('sidebar-open')) {
      closeMobileSidebar();
      return;
    }
    if (document.body.classList.contains('sidebar-peek-open')) {
      closeCollapsedAccordions();
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
