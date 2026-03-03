(() => {
  const panel = document.getElementById('companySecurityPanel');
  if (!panel) return;

  const endpoint = panel.dataset.securityEndpoint || '';
  if (!endpoint) return;

  const totalEl = document.getElementById('companySecurityTotal');
  const successEl = document.getElementById('companySecuritySuccess');
  const failedEl = document.getElementById('companySecurityFailed');
  const liveEl = document.getElementById('companySecurityLiveStatus');
  const syncEl = document.getElementById('companySecurityLastSync');
  const tableBody = document.getElementById('companyLoginHistoryBody');
  const sessionList = document.getElementById('companySessionList');

  const POLL_INTERVAL_MS = 10000;
  let isFetching = false;

  const escapeHtml = (value) =>
    String(value ?? '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');

  const updateLiveBadge = (text, tone = 'info') => {
    if (!liveEl) return;
    liveEl.textContent = text;
    liveEl.classList.remove('info', 'success', 'warning', 'danger');
    liveEl.classList.add(tone);
  };

  const renderStats = (stats) => {
    if (!stats) return;
    if (totalEl) totalEl.textContent = String(stats.total ?? 0);
    if (successEl) successEl.textContent = String(stats.success ?? 0);
    if (failedEl) failedEl.textContent = String(stats.failed ?? 0);
  };

  const renderEntries = (entries) => {
    if (!tableBody) return;
    if (!Array.isArray(entries) || !entries.length) {
      tableBody.innerHTML = '<tr><td colspan="5" class="text-center text-muted">No login activity recorded yet.</td></tr>';
      return;
    }
    tableBody.innerHTML = entries
      .map(
        (entry) => `
<tr>
  <td>${escapeHtml(entry.created_at || '--')}</td>
  <td>${escapeHtml(entry.device || '--')}</td>
  <td>${escapeHtml(entry.ip_address || '--')}</td>
  <td><span class="badge ${escapeHtml(entry.status_class || 'info')}">${escapeHtml(entry.status || '--')}</span></td>
  <td>${escapeHtml(entry.note || '--')}</td>
</tr>`,
      )
      .join('');
  };

  const renderSessions = (sessions) => {
    if (!sessionList) return;
    if (!Array.isArray(sessions) || !sessions.length) {
      sessionList.innerHTML = `
        <div class="activity-item">
          <div>
            <strong>No active sessions found</strong>
            <span class="muted">Session data will appear after login history is recorded.</span>
          </div>
        </div>`;
      return;
    }

    sessionList.innerHTML = sessions
      .map((session) => {
        const badge = session.is_current
          ? '<span class="badge success">Current Session</span>'
          : '<span class="badge info">Recent Session</span>';
        return `
<div class="activity-item">
  <div>
    <strong>${escapeHtml(session.device || 'Unknown Device')}</strong>
    <span class="muted">IP: ${escapeHtml(session.ip_address || '--')} | Last seen: ${escapeHtml(session.last_seen || '--')}</span>
  </div>
  ${badge}
</div>`;
      })
      .join('');
  };

  const refreshSecurityData = async () => {
    if (isFetching) return;
    isFetching = true;
    try {
      const response = await fetch(`${endpoint}?limit=25`, { credentials: 'same-origin' });
      const payload = await response.json();
      if (!response.ok || !payload.success) {
        updateLiveBadge('Retrying', 'warning');
        return;
      }

      renderStats(payload.stats);
      renderEntries(payload.entries);
      renderSessions(payload.sessions);
      if (syncEl) {
        syncEl.textContent = `Last sync: ${payload.generated_at || '--'}`;
      }
      updateLiveBadge('Live', 'success');
    } catch (error) {
      updateLiveBadge('Retrying', 'warning');
    } finally {
      isFetching = false;
    }
  };

  refreshSecurityData();
  setInterval(() => {
    if (document.hidden) return;
    refreshSecurityData();
  }, POLL_INTERVAL_MS);
})();
