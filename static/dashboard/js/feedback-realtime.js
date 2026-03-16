(() => {
  const table = document.querySelector('[data-feedback-table]');
  if (!table) return;

  const endpoint = table.dataset.endpoint;
  if (!endpoint) return;

  const scope = table.dataset.scope || 'panel';
  const tbody = table.querySelector('tbody');
  const updatedEl = document.getElementById('feedbackUpdatedAt');

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
    const ratingHtml = item.rating ? renderStars(item.rating) : '<span class="muted">--</span>';
    return `
      <tr>
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
    const metaLine = [designation, organization].filter(Boolean).join(' · ');
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
    const ratingHtml = item.rating ? renderStars(item.rating) : '<span class="muted">--</span>';
    return `
      <tr>
        <td>${feedbackId}</td>
        <td>${role}</td>
        <td>${profileHtml}</td>
        <td>${context}</td>
        <td>${ratingHtml}</td>
        <td class="muted">${message}</td>
        <td>${createdAt}</td>
      </tr>`;
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
      updatedEl.textContent = parsed.toLocaleString();
    } else {
      updatedEl.textContent = value;
    }
  };

  const refresh = async () => {
    try {
      const response = await fetch(endpoint, { headers: { 'X-Requested-With': 'XMLHttpRequest' } });
      if (!response.ok) return;
      const data = await response.json();
      if (!tbody) return;
      tbody.innerHTML = renderRows(data.feedbacks || []);
      updateTimestamp(data.updated_at);
    } catch (error) {
      // Silent fail to avoid disrupting the page.
    }
  };

  refresh();
  setInterval(() => {
    if (document.hidden) return;
    refresh();
  }, 15000);
})();
