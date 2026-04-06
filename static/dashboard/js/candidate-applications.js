document.addEventListener('DOMContentLoaded', () => {
  const tableBody = document.getElementById('candidateApplicationsBody');
  if (!tableBody) return;

  const timelineSection = document.getElementById('applicationTimelineSection');
  const timelineGrid = document.getElementById('applicationTimelineGrid');
  const timelineSummary = document.getElementById('applicationTimelineSummary');
  const liveStatus = document.getElementById('candidateApplicationsLiveStatus');
  const detailModalEl = document.getElementById('candidateApplicationDetailModal');
  const detailTitle = document.getElementById('candidateApplicationDetailTitle');
  const detailGrid = document.getElementById('candidateApplicationDetailGrid');

  const detailModal = window.bootstrap && detailModalEl
    ? new bootstrap.Modal(detailModalEl, { backdrop: true, keyboard: true, focus: true })
    : null;

  const endpoint = '/candidate/api/applications/';
  const fallbackStatusFlow = (timelineSection?.dataset.statusFlow || '')
    .split('|')
    .map((value) => value.trim())
    .filter(Boolean);
  let statusFlow = fallbackStatusFlow.length
    ? fallbackStatusFlow
    : ['Applied', 'Under Review', 'Shortlisted', 'Interview Scheduled', 'Selected', 'Offer Received', 'Rejected'];
  let selectedApplicationId = timelineGrid?.dataset.selectedApplication || '';
  const queryParams = new URLSearchParams(window.location.search);
  const requestedApplicationId = (queryParams.get('application_id') || '').trim();
  const requestedMode = (queryParams.get('mode') || '').trim().toLowerCase();
  const requestedHashApplicationId = (window.location.hash || '').replace('#candidate-app-', '').trim();
  if (requestedApplicationId) {
    selectedApplicationId = requestedApplicationId;
  } else if (requestedHashApplicationId) {
    selectedApplicationId = requestedHashApplicationId;
  }
  let initialFocusHandled = false;
  let timelineVisible = false;
  let applicationsById = new Map();
  let isFetching = false;

  const escapeHtml = (value) =>
    String(value ?? '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');

  const normalizeStatus = (status) => {
    const raw = String(status || '').trim();
    if (raw === 'Interview') return 'Interview Scheduled';
    if (raw === 'Offer Issued') return 'Offer Received';
    return raw || 'Applied';
  };

  const getStatusBadgeClass = (status) => {
    const normalized = normalizeStatus(status);
    if (normalized === 'Applied') return 'info';
    if (normalized === 'Under Review') return 'warning';
    if (normalized === 'Shortlisted') return 'success';
    if (normalized === 'Interview Scheduled') return 'neutral';
    if (normalized === 'Selected') return 'info';
    if (normalized === 'Offer Received') return 'success';
    if (normalized === 'Rejected') return 'danger';
    return 'neutral';
  };

  const formatDate = (value) => {
    if (!value) return '--';
    const parsed = new Date(`${value}T00:00:00`);
    if (Number.isNaN(parsed.getTime())) return '--';
    return parsed.toLocaleDateString('en-IN', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    });
  };

  const setLiveStatus = (text, isError = false) => {
    if (!liveStatus) return;
    liveStatus.textContent = text;
    liveStatus.classList.toggle('live-error', isError);
  };

  const setTimelineVisible = (visible, { scroll = false } = {}) => {
    timelineVisible = Boolean(visible);
    if (!timelineSection) return;
    timelineSection.hidden = !timelineVisible;
    if (timelineVisible && scroll) {
      timelineSection.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  };

  const highlightActiveRow = (applicationId) => {
    tableBody.querySelectorAll('tr[data-application-id]').forEach((row) => {
      row.classList.toggle('candidate-app-row-active', row.dataset.applicationId === applicationId);
    });
  };

  const buildTableRow = (app, isActive) => {
    const status = normalizeStatus(app.status);
    const viewAction = app.job_url
      ? `<a class="action-btn" href="${escapeHtml(app.job_url)}" data-action="view" data-application-id="${escapeHtml(app.application_id)}">View</a>`
      : `<button class="action-btn" type="button" data-action="view" data-application-id="${escapeHtml(app.application_id)}">View</button>`;

    return `
      <tr id="candidate-app-${escapeHtml(app.application_id)}" data-application-id="${escapeHtml(app.application_id)}"${isActive ? ' class="candidate-app-row-active"' : ''}>
        <td><strong>${escapeHtml(app.job_title || 'N/A')}</strong></td>
        <td>${escapeHtml(app.company || '--')}</td>
        <td>${escapeHtml(formatDate(app.applied_date))}</td>
        <td><span class="badge ${getStatusBadgeClass(status)}">${escapeHtml(status)}</span></td>
        <td>
          <div class="table-actions">
            ${viewAction}
            <button class="action-btn" type="button" data-action="timeline" data-application-id="${escapeHtml(app.application_id)}">Timeline</button>
          </div>
        </td>
      </tr>
    `;
  };

  const renderTable = (applications) => {
    if (!applications.length) {
      tableBody.innerHTML = `
        <tr>
          <td colspan="5" class="muted" style="text-align:center; padding: 16px;">No applications found yet.</td>
        </tr>
      `;
      return;
    }
    tableBody.innerHTML = applications
      .map((app) => buildTableRow(app, app.application_id === selectedApplicationId))
      .join('');
  };

  const renderTimeline = (app) => {
    if (!timelineGrid) return;
    if (!app) {
      timelineGrid.classList.add('is-empty');
      timelineGrid.innerHTML = '<div class="candidate-app-empty">No application timeline yet.</div>';
      if (timelineSummary) {
        timelineSummary.textContent = 'Apply to jobs to unlock your timeline.';
      }
      return;
    }

    const currentStep = Number(app.current_step || 1);
    timelineGrid.classList.remove('is-empty');
    timelineGrid.innerHTML = statusFlow
      .map((step, index) => {
        const activeClass = index + 1 <= currentStep ? ' active' : '';
        return `
          <div class="timeline-step${activeClass}">
            <span class="timeline-dot"></span>
            <span class="timeline-label">${escapeHtml(step)}</span>
          </div>
        `;
      })
      .join('');
    if (timelineSummary) {
      timelineSummary.textContent = `Tracking ${app.job_title || 'N/A'} at ${app.company || '--'}.`;
    }
  };

  const renderDetail = (app) => {
    if (!detailGrid || !app) return;
    if (detailTitle) {
      detailTitle.textContent = `${app.job_title || 'Application'} - ${app.company || 'Company'}`;
    }
    const status = normalizeStatus(app.status);
    const rows = [
      { label: 'Application ID', value: app.application_id || '--' },
      { label: 'Status', value: status || '--' },
      { label: 'Rejection Remark', value: app.rejection_remark || '--', hidden: status !== 'Rejected' && !app.rejection_remark },
      { label: 'Applied Date', value: formatDate(app.applied_date) },
      { label: 'Interview Date', value: formatDate(app.interview_date) },
      { label: 'Interview Time', value: app.interview_time || '--' },
      { label: 'Interviewer', value: app.interviewer || '--' },
      { label: 'Offer Package', value: app.offer_package || '--' },
      { label: 'Current Stage', value: `${app.current_step || 1} / ${statusFlow.length}` },
    ];
    if (app.job_url) {
      rows.push({
        label: 'Job Post',
        value: `<a href="${escapeHtml(app.job_url)}">Open job details</a>`,
        isHtml: true,
      });
    }
    detailGrid.innerHTML = rows
      .filter((item) => !item.hidden)
      .map((item) => {
        const content = item.isHtml ? item.value : escapeHtml(item.value);
        return `<div><span>${escapeHtml(item.label)}</span><strong>${content}</strong></div>`;
      })
      .join('');
  };

  const selectApplication = (applicationId, { scrollToTimeline = false } = {}) => {
    if (!applicationId || !applicationsById.has(applicationId)) return;
    selectedApplicationId = applicationId;
    const app = applicationsById.get(applicationId);
    highlightActiveRow(applicationId);
    renderTimeline(app);
    if (scrollToTimeline) {
      setTimelineVisible(true, { scroll: true });
    }
  };

  tableBody.addEventListener('click', (event) => {
    const target = event.target.closest('[data-action]');
    if (!target) return;
    const action = target.dataset.action || '';
    const applicationId = target.dataset.applicationId || '';
    if (!applicationId) return;

    if (action === 'timeline') {
      event.preventDefault();
      selectApplication(applicationId, { scrollToTimeline: true });
      return;
    }

    if (action === 'view' && target.tagName !== 'A') {
      event.preventDefault();
      const app = applicationsById.get(applicationId);
      if (!app) return;
      renderDetail(app);
      if (detailModal) {
        detailModal.show();
      }
    }
  });

  const refreshApplications = async () => {
    if (isFetching) return;
    isFetching = true;
    try {
      const response = await fetch(endpoint, { credentials: 'same-origin' });
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      const data = await response.json();
      const applications = Array.isArray(data.applications) ? data.applications : [];
      const nextStatusFlow = Array.isArray(data.status_flow) ? data.status_flow.filter(Boolean) : [];
      if (nextStatusFlow.length) {
        statusFlow = nextStatusFlow;
      }

      applicationsById = new Map(
        applications.map((app) => [String(app.application_id || ''), app]).filter(([id]) => id)
      );

      if (!selectedApplicationId || !applicationsById.has(selectedApplicationId)) {
        selectedApplicationId = applications.length ? String(applications[0].application_id || '') : '';
      }

      renderTable(applications);
      const selected = selectedApplicationId ? applicationsById.get(selectedApplicationId) : null;
      renderTimeline(selected || (applications.length ? applications[0] : null));
      if (selectedApplicationId) {
        highlightActiveRow(selectedApplicationId);
      }

      if (!initialFocusHandled && selectedApplicationId) {
        const targetRow = document.getElementById(`candidate-app-${selectedApplicationId}`);
        if (targetRow && (requestedApplicationId || requestedHashApplicationId)) {
          targetRow.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
        if (requestedMode === 'timeline') {
          setTimelineVisible(true, { scroll: true });
        }
        initialFocusHandled = true;
      }

      const stamp = data.generated_at ? new Date(data.generated_at) : new Date();
      const timeLabel = Number.isNaN(stamp.getTime())
        ? 'Live'
        : `Live ${stamp.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })}`;
      setLiveStatus(timeLabel, false);
    } catch (error) {
      setLiveStatus('Reconnect...', true);
    } finally {
      isFetching = false;
    }
  };

  let pollHandle = null;
  const startPolling = () => {
    if (pollHandle) return;
    pollHandle = setInterval(refreshApplications, 12000);
  };
  const stopPolling = () => {
    if (!pollHandle) return;
    clearInterval(pollHandle);
    pollHandle = null;
  };

  setTimelineVisible(false);
  refreshApplications();
  startPolling();
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
      stopPolling();
      return;
    }
    refreshApplications();
    startPolling();
  });
});
