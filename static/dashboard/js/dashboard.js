// Smooth sidebar accordion functionality
document.addEventListener('DOMContentLoaded', () => {
  const toggles = document.querySelectorAll('[data-sidebar-toggle]');
  const overlay = document.getElementById('sidebarOverlay');
  const accordions = document.querySelectorAll('.nav-toggle');
  const subAccordions = document.querySelectorAll('.nav-sub-toggle');
  const darkToggle = document.getElementById('darkModeToggle');
  const fullscreenToggles = document.querySelectorAll('[data-fullscreen-toggle]');
  const messageLinks = document.querySelectorAll('a.icon-btn[aria-label="Messages"]');

  const isMobile = () => window.matchMedia('(max-width: 900px)').matches;

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
    settings: 'M12 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6zm8 3-2 .6a6 6 0 0 1-.6 1.4l1.2 1.7-1.4 1.4-1.7-1.2c-.4.2-.9.4-1.4.6L13 20h-2l-.6-2a6 6 0 0 1-1.4-.6l-1.7 1.2-1.4-1.4 1.2-1.7a6 6 0 0 1-.6-1.4L4 12l2-.6c.1-.5.3-1 .6-1.4L5.4 8.3 6.8 6.9l1.7 1.2c.4-.2.9-.4 1.4-.6L11 4h2l.6 2c.5.1 1 .3 1.4.6l1.7-1.2 1.4 1.4-1.2 1.7c.2.4.4.9.6 1.4L20 12z',
    support: 'M12 3a7 7 0 0 1 7 7v2a5 5 0 0 1-5 5h-1v3h-2v-3H9a5 5 0 0 1-5-5v-2a7 7 0 0 1 7-7z',
    logout: 'M15 4h4v16h-4M10 8l4 4-4 4M14 12H4',
    crown: 'M3 8l4 4 5-6 5 6 4-4-2 11H5L3 8z',
    check: 'M4 12l5 5L20 6',
    close: 'M6 6l12 12M18 6 6 18',
  };

  const buildInlineIcon = (path, extraAttrs = '') =>
    `<svg class="ui-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" ${extraAttrs}><path d="${path}" /></svg>`;

  const hasFontAwesome = (() => {
    const sample = document.querySelector('i.fa-solid, i.fa-regular');
    if (!sample) return false;
    const family = (window.getComputedStyle(sample).fontFamily || '').toLowerCase();
    return family.includes('font awesome');
  })();

  const useInlineFallbackIcons = !hasFontAwesome;
  const faPathMap = {
    'fa-bars': iconPaths.menu,
    'fa-moon': iconPaths.moon,
    'fa-sun': iconPaths.sun,
    'fa-envelope': iconPaths.message,
    'fa-magnifying-glass': iconPaths.search,
    'fa-bell': iconPaths.bell,
    'fa-user': iconPaths.user,
    'fa-user-check': iconPaths.user,
    'fa-users': iconPaths.user,
    'fa-briefcase': iconPaths.briefcase,
    'fa-chart-line': iconPaths.chart,
    'fa-chart-pie': iconPaths.chart,
    'fa-calendar-check': iconPaths.calendar,
    'fa-file': iconPaths.file,
    'fa-file-lines': iconPaths.file,
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
    if (!iconEl) return iconPaths.check;
    const classNames = Array.from(iconEl.classList || []);
    for (let idx = 0; idx < classNames.length; idx += 1) {
      const key = classNames[idx];
      if (faPathMap[key]) {
        return faPathMap[key];
      }
    }
    return iconPaths.check;
  };

  const replaceAnyFaIcon = (iconEl) => {
    if (!iconEl || iconEl.tagName !== 'I') return;
    const path = resolveInlinePathForFaIcon(iconEl);
    const inline = buildInlineIcon(path);
    iconEl.insertAdjacentHTML('afterend', inline);
    iconEl.remove();
  };

  if (useInlineFallbackIcons) {
    toggles.forEach((button) => replaceIconWithInline(button, iconPaths.menu));
    fullscreenToggles.forEach((button) => replaceIconWithInline(button, iconPaths.fullscreen));
    messageLinks.forEach((button) => replaceIconWithInline(button, iconPaths.message));
    document.querySelectorAll('i.fa-solid, i.fa-regular, i.fa-brands').forEach((iconEl) => {
      replaceAnyFaIcon(iconEl);
    });
  }

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
    localStorage.setItem('sidebar-collapsed', collapsed ? 'true' : 'false');
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
    localStorage.setItem('sidebar-collapsed', collapsed ? 'true' : 'false');
  };

  // Menu toggle
  toggles.forEach((btn) => btn.addEventListener('click', toggleSidebar));

  // Overlay click handler
  if (overlay) {
    overlay.addEventListener('click', () => {
      closeMobileSidebar();
    });
  }

  const stored = localStorage.getItem('sidebar-collapsed');
  if (stored === 'true' && !isMobile()) {
    applySidebarState(true);
  }

  window.addEventListener('resize', () => {
    if (isMobile()) {
      document.body.classList.remove('sidebar-collapsed');
    } else {
      document.body.classList.remove('sidebar-open');
      const saved = localStorage.getItem('sidebar-collapsed');
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

  const storedTheme = localStorage.getItem(darkStorageKey);
  const legacyTheme = localStorage.getItem('dark-mode');
  const shouldEnableDark =
    storedTheme === 'true' || (storedTheme === null && themeScope === 'admin' && legacyTheme === 'true');
  document.body.classList.toggle('dark-mode', shouldEnableDark);

  updateDarkIcon();

  if (darkToggle) {
    darkToggle.addEventListener('click', () => {
      document.body.classList.toggle('dark-mode');
      localStorage.setItem(darkStorageKey, document.body.classList.contains('dark-mode'));
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
