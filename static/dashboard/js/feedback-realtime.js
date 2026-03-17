(() => {
  const table = document.querySelector('[data-feedback-table]');
  if (!table) return;

  const endpoint = table.dataset.endpoint;
  if (!endpoint) return;

  const scope = table.dataset.scope || 'panel';
  const tbody = table.querySelector('tbody');
  const updatedEl = document.getElementById('feedbackUpdatedAt');
  const totalCountEl = document.getElementById('feedbackTotalCount');
  const averageRatingEl = document.getElementById('feedbackAverageRating');
  const averageScoreEl = document.getElementById('feedbackAverageScore');
  const averageLabelEl = document.getElementById('feedbackAverageLabel');
  const gaugePath = document.getElementById('feedbackAverageGauge');
  const volumeBars = document.getElementById('feedbackVolumeBars');

  const escapeHtml = (value) => {
    if (value === null || value === undefined) return '';
    return String(value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  };

  const renderStars = (rating) => {
    const safeRating = Math.max(0, Math.min(5, Number(rating || 0)));
    let stars = '<div class="rating-stars">';
    for (let i = 1; i <= 5; i += 1) {
      stars += `<i class="fa-solid fa-star ${i > safeRating ? 'muted-star' : ''}"></i>`;
    }
    stars += '</div>';
    return stars;
  };

  const renderPanelRow = (item) => {
    const createdAt = escapeHtml(item.created_at || '--');
    const context = escapeHtml(item.context_label || item.application_title || item.job_title || '--');
    const message = escapeHtml(item.message || '--');
    const ratingValue = Number(item.rating || 0);
    const ratingHtml = ratingValue ? renderStars(ratingValue) : '<span class="muted">--</span>';
    return `
      <tr data-rating="${ratingValue}" data-created-at="${createdAt}">
        <td>${createdAt}</td>
        <td>${context}</td>
        <td>${ratingHtml}</td>
        <td class="muted">${message}</td>
      </tr>`;
  };

  const renderAdminRow = (item) => {
    const feedbackId = escapeHtml(item.feedback_id || '--');
    const role = escapeHtml(item.role_label || item.role || '--');
    const name = escapeHtml(item.display_name || item.submitted_by || item.name || '--');
    const designation = item.designation ? escapeHtml(item.designation) : '';
    const organization = (item.organization || item.company_name) ? escapeHtml(item.organization || item.company_name) : '';
    const metaLine = [designation, organization].filter(Boolean).join(' &middot; ');
    const safePhoto = item.photo_url ? escapeHtml(item.photo_url) : '';
    const initial = name && name !== '--' ? name.trim().charAt(0).toUpperCase() : '--';
    const avatarHtml = safePhoto
      ? `<img src="${safePhoto}" alt="${name}" />`
      : `<span>${escapeHtml(initial)}</span>`;
    const profileHtml = `
      <div class="feedback-user">
        <div class="avatar">${avatarHtml}</div>
        <div class="feedback-meta">
          <strong>${name}</strong>
          ${metaLine ? `<span>${metaLine}</span>` : ''}
        </div>
      </div>`;
    const context = escapeHtml(item.context_label || item.application_title || item.job_title || '--');
    const message = escapeHtml(item.message || '--');
    const createdAt = escapeHtml(item.created_at || '--');
    const ratingValue = Number(item.rating || 0);
    const ratingHtml = ratingValue ? renderStars(ratingValue) : '<span class="muted">--</span>';
    return `
      <tr data-rating="${ratingValue}" data-created-at="${createdAt}">
        <td>${feedbackId}</td>
        <td>${role}</td>
        <td>${profileHtml}</td>
        <td>${context}</td>
        <td>${ratingHtml}</td>
        <td class="muted">${message}</td>
        <td>${createdAt}</td>
      </tr>`;
  };

  const readItemsFromDom = () => {
    if (!tbody) return [];
    const rows = Array.from(tbody.querySelectorAll('tr'));
    return rows
      .map((row) => {
        const rating = Number(row.dataset.rating || 0);
        const createdAt = row.dataset.createdAt || row.getAttribute('data-created-at') || '';
        return { rating, created_at: createdAt };
      })
      .filter((item) => item.created_at || item.rating);
  };

  const renderRows = (items) => {
    if (!Array.isArray(items) || items.length === 0) {
      const colspan = scope === 'admin' ? 7 : 4;
      return `<tr><td colspan="${colspan}" class="muted" style="text-align:center; padding: 16px;">No feedback submitted yet.</td></tr>`;
    }
    return items.map((item) => (scope === 'admin' ? renderAdminRow(item) : renderPanelRow(item))).join('');
  };

  const updateTimestamp = (value) => {
    if (!updatedEl || !value) return;
    const parsed = new Date(value);
    if (!Number.isNaN(parsed.getTime())) {
      try {
        updatedEl.textContent = parsed.toLocaleString(undefined, {
          dateStyle: 'medium',
          timeStyle: 'short',
        });
      } catch (error) {
        updatedEl.textContent = parsed.toLocaleString();
      }
      return;
    }
    updatedEl.textContent = value;
  };

  const parseCreatedAt = (value) => {
    if (!value) return null;
    const match = String(value).match(/(\d{4})-(\d{2})-(\d{2})(?:[ T](\d{2}):(\d{2}))?/);
    if (!match) return null;
    const year = Number(match[1]);
    const month = Number(match[2]) - 1;
    const day = Number(match[3]);
    const hour = Number(match[4] || 0);
    const minute = Number(match[5] || 0);
    return new Date(year, month, day, hour, minute);
  };

  const updateVolumeBars = (items) => {
    if (!volumeBars) return;
    const bars = Array.from(volumeBars.querySelectorAll('.bar'));
    if (!bars.length) return;

    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const windowSize = bars.length;
    const start = new Date(today);
    start.setDate(today.getDate() - (windowSize - 1));

    const counts = new Array(windowSize).fill(0);
    (items || []).forEach((item) => {
      const created = parseCreatedAt(item.created_at);
      if (!created) return;
      created.setHours(0, 0, 0, 0);
      const diffDays = Math.round((created - start) / (1000 * 60 * 60 * 24));
      if (diffDays >= 0 && diffDays < windowSize) {
        counts[diffDays] += 1;
      }
    });

    const maxCount = Math.max(...counts, 1);
    bars.forEach((bar, index) => {
      const ratio = counts[index] / maxCount;
      bar.style.setProperty('--bar', (ratio < 0.15 ? 0.15 : ratio).toFixed(2));
    });
  };

  const updateAverageGauge = (average) => {
    if (!gaugePath) return;
    const total = gaugePath.getTotalLength();
    const ratio = Math.max(0, Math.min(1, average / 5));
    gaugePath.style.strokeDasharray = total;
    gaugePath.style.strokeDashoffset = total * (1 - ratio);

    if (average >= 4) {
      gaugePath.style.stroke = '#16a34a';
    } else if (average >= 3) {
      gaugePath.style.stroke = '#f59e0b';
    } else {
      gaugePath.style.stroke = '#ef4444';
    }
  };

  const updateSummary = (items) => {
    const total = Array.isArray(items) ? items.length : 0;
    const rated = (items || []).filter((item) => Number(item.rating || 0) > 0);
    const ratingCount = rated.length;
    const ratingSum = rated.reduce((sum, item) => sum + Number(item.rating || 0), 0);
    const average = ratingCount ? ratingSum / ratingCount : 0;

    if (totalCountEl) {
      totalCountEl.textContent = total.toLocaleString();
    }

    const averageLabel = ratingCount ? average.toFixed(1) : '--';
    if (averageRatingEl) {
      averageRatingEl.textContent = averageLabel;
    }
    if (averageScoreEl) {
      averageScoreEl.textContent = averageLabel;
    }
    if (averageLabelEl) {
      averageLabelEl.textContent = ratingCount
        ? `Based on ${ratingCount} reviews`
        : 'Based on -- reviews';
    }

    updateAverageGauge(average);
    updateVolumeBars(items || []);
  };

  const refresh = async () => {
    try {
      const response = await fetch(endpoint, { headers: { 'X-Requested-With': 'XMLHttpRequest' } });
      if (!response.ok) return;
      const data = await response.json();
      if (!tbody) return;
      const feedbacks = data.feedbacks || [];
      tbody.innerHTML = renderRows(feedbacks);
      updateTimestamp(data.updated_at);
      updateSummary(feedbacks);
    } catch (error) {
      // Silent fail to avoid disrupting the page.
    }
  };

  const initialItems = readItemsFromDom();
  if (initialItems.length) {
    updateSummary(initialItems);
  }

  refresh();
  setInterval(() => {
    if (document.hidden) return;
    refresh();
  }, 15000);
})();
