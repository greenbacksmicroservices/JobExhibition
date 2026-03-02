(() => {
  const tableBody = document.getElementById('loginHistoryTableBody');
  if (!tableBody) {
    return;
  }

  const totalEl = document.getElementById('loginTotalCount');
  const successEl = document.getElementById('loginSuccessCount');
  const failedEl = document.getElementById('loginFailedCount');
  const recentEl = document.getElementById('loginRecentRows');
  const syncEl = document.getElementById('loginHistoryLastSync');
  const liveBadge = document.getElementById('auditLiveStatus');

  const POLL_INTERVAL_MS = 8000;
  const LIMIT = 100;

  const escapeHtml = (value) =>
    String(value ?? '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');

  const formatText = (value, fallback = '--') => {
    const normalized = String(value ?? '').trim();
    return normalized ? escapeHtml(normalized) : fallback;
  };

  const updateLiveState = (statusText, badgeClass) => {
    if (!liveBadge) return;
    liveBadge.textContent = statusText;
    liveBadge.classList.remove('success', 'danger', 'warning', 'info');
    liveBadge.classList.add(badgeClass || 'info');
  };

  const updateStats = (stats) => {
    if (!stats) return;
    if (totalEl) totalEl.textContent = String(stats.total_logins ?? 0);
    if (successEl) successEl.textContent = String(stats.success_count ?? 0);
    if (failedEl) failedEl.textContent = String(stats.failed_count ?? 0);
    if (recentEl) recentEl.textContent = String(stats.recent_rows ?? 0);
  };

  const renderRows = (rows) => {
    if (!Array.isArray(rows) || !rows.length) {
      tableBody.innerHTML =
        '<tr><td colspan="7" class="text-center text-muted">No login history available yet.</td></tr>';
      return;
    }

    tableBody.innerHTML = rows
      .map((row) => {
        const status = row.is_success
          ? '<span class="badge success">Success</span>'
          : '<span class="badge danger">Failed</span>';
        const agent = String(row.user_agent || '');
        const agentShort = agent.length > 60 ? `${agent.slice(0, 57)}...` : agent;
        return `
<tr>
  <td>${formatText(row.account_type_label)}</td>
  <td>${formatText(row.username_or_email)}</td>
  <td>${formatText(row.created_at)}</td>
  <td>${formatText(row.ip_address)}</td>
  <td>${formatText(agentShort)}</td>
  <td>${formatText(row.note)}</td>
  <td>${status}</td>
</tr>`;
      })
      .join('');
  };

  const fetchHistory = async () => {
    try {
      const response = await fetch(`/api/security/login-history/?limit=${LIMIT}`);
      const payload = await response.json();
      if (!response.ok || payload.error || !payload.success) {
        updateLiveState('Retrying', 'warning');
        return;
      }

      updateStats(payload.stats || {});
      renderRows(payload.entries || []);
      if (syncEl) {
        syncEl.textContent = `Last sync: ${formatText(payload.generated_at, '--')}`;
      }
      updateLiveState('Live', 'success');
    } catch (error) {
      updateLiveState('Retrying', 'warning');
    }
  };

  fetchHistory();
  setInterval(() => {
    if (document.hidden) return;
    fetchHistory();
  }, POLL_INTERVAL_MS);
})();
