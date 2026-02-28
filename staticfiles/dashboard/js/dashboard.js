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

  if (useInlineFallbackIcons) {
    toggles.forEach((button) => replaceIconWithInline(button, iconPaths.menu));
    fullscreenToggles.forEach((button) => replaceIconWithInline(button, iconPaths.fullscreen));
    messageLinks.forEach((button) => replaceIconWithInline(button, iconPaths.message));
  }

  const activateLogoFallback = (brandMark) => {
    if (!brandMark || brandMark.classList.contains('logo-fallback')) return;
    brandMark.classList.add('logo-fallback');
    const fallback = document.createElement('span');
    fallback.className = 'brand-fallback-text';
    fallback.textContent = 'JE';
    brandMark.appendChild(fallback);
  };

  document.querySelectorAll('.brand-mark img').forEach((img) => {
    const brandMark = img.closest('.brand-mark');
    const onError = () => {
      img.remove();
      activateLogoFallback(brandMark);
    };
    if (img.complete && img.naturalWidth === 0) {
      onError();
      return;
    }
    img.addEventListener('error', onError, { once: true });
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

  // Main accordion menu items with smooth animation
  accordions.forEach((button) => {
    button.addEventListener('click', (e) => {
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
      const isOpen = section.classList.toggle('open');
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
    const label = button.querySelector('span');
    if (!hasAudioTrack(video)) {
      button.setAttribute('aria-pressed', 'false');
      button.setAttribute('aria-label', 'No audio track');
      button.disabled = true;
      if (icon) {
        icon.classList.remove('fa-volume-high');
        icon.classList.add('fa-volume-xmark');
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
