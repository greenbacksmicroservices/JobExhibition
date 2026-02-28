(() => {
  const metricActiveJobsEl = document.getElementById('metricActiveJobs');
  if (!metricActiveJobsEl) {
    return;
  }

  const metricCandidatesEl = document.getElementById('metricCandidates');
  const metricRecruitersEl = document.getElementById('metricRecruiters');
  const metricConsultanciesEl = document.getElementById('metricConsultancies');
  const metricTodayRegsEl = document.getElementById('metricTodayRegistrations');
  const metricRevenueEl = document.getElementById('metricRevenueMonth');

  const chartJobsTrend = document.getElementById('chartJobsTrend');
  const chartJobCategories = document.getElementById('chartJobCategories');
  const chartSubscriptionConversion = document.getElementById('chartSubscriptionConversion');
  const chartUserTotals = document.getElementById('chartUserTotals');
  const chartApprovalTrend = document.getElementById('chartApprovalTrend');

  const alertJobsPending = document.getElementById('alertJobsPending');
  const alertComplaints = document.getElementById('alertComplaints');
  const alertExpiringToday = document.getElementById('alertExpiringToday');
  const alertSuspicious = document.getElementById('alertSuspicious');

  const recentActivityList = document.getElementById('recentActivityList');

  const STORAGE_KEY = 'jobex_jobs';
  const pollInterval = 20000;
  const palette = ['#6366f1', '#06b6d4', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#22c55e'];

  const formatNumber = (value) => {
    const number = Number(value || 0);
    return Number.isNaN(number) ? '0' : number.toLocaleString();
  };

  const formatCurrency = (value) => `INR ${formatNumber(value)}`;

  const formatPercent = (value, total) => {
    if (!total) return 0;
    return Math.round((Number(value) / total) * 100);
  };

  const escapeHtml = (value) =>
    String(value ?? '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');

  const escapeAttr = (value) => escapeHtml(value).replace(/`/g, '&#96;');

  const fetchJson = async (url, options = {}) => {
    try {
      const response = await fetch(url, options);
      const text = await response.text();
      let data = {};
      try {
        data = text ? JSON.parse(text) : {};
      } catch (error) {
        data = { error: 'Server error. Please check server logs.' };
      }
      if (!response.ok) {
        data.error = data.error || 'Server error. Please check server logs.';
      }
      return data;
    } catch (error) {
      return { error: 'Network error. Please check connection.' };
    }
  };

  const loadLocalJobs = () => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) return JSON.parse(raw);
    } catch (error) {
      return [];
    }
    return [];
  };

  const computeLocalJobStats = (jobs) => {
    const total = jobs.length;
    const approved = jobs.filter((job) => job.status === 'Approved').length;
    const pending = jobs.filter((job) => job.status === 'Pending').length;
    const rejected = jobs.filter((job) => job.status === 'Rejected').length;
    const reported = jobs.filter((job) => job.status === 'Reported').length;
    return { total, approved, pending, rejected, reported };
  };

  const computeLocalCategories = (jobs) => {
    const counts = {};
    jobs.forEach((job) => {
      const key = (job.category || 'Other').trim() || 'Other';
      counts[key] = (counts[key] || 0) + 1;
    });
    return Object.entries(counts)
      .map(([category, count]) => ({ category, count }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 5);
  };

  const setText = (el, value) => {
    if (el) el.textContent = value;
  };

  const renderEmpty = (container, message) => {
    if (container) {
      container.innerHTML = `<p class="muted">${message}</p>`;
    }
  };

  const buildConicGradient = (segments) => {
    const total = segments.reduce((sum, segment) => sum + segment.value, 0);
    if (!total) {
      return { total: 0, gradient: '#e5e7eb', segments: [] };
    }
    let start = 0;
    const normalized = segments.map((segment, index) => {
      const isLast = index === segments.length - 1;
      const percent = isLast ? Math.max(0, 100 - start) : Math.floor((segment.value / total) * 100);
      const end = start + percent;
      const slice = `${segment.color} ${start}% ${end}%`;
      start = end;
      return { ...segment, percent, slice };
    });
    return {
      total,
      gradient: normalized.map((segment) => segment.slice).join(', '),
      segments: normalized,
    };
  };

  const buildLegend = (segments, total) => {
    return segments
      .map((segment) => {
        return `
<li>
  <span class="legend-label"><span class="legend-dot" style="background:${segment.color}"></span>${segment.label}</span>
  <span class="legend-value">${formatNumber(segment.value)} (${formatPercent(segment.value, total)}%)</span>
</li>`;
      })
      .join('');
  };

  const renderBarChart = (container, items) => {
    if (!container) return;
    if (!Array.isArray(items) || !items.length) {
      renderEmpty(container, 'No data yet.');
      return;
    }
    const maxValue = Math.max(...items.map((item) => item.count), 1);
    container.innerHTML = `
<div class="bar-chart-grid">
  ${items
    .map((item) => {
      const height = Math.round((item.count / maxValue) * 100);
      const barStyle = item.color ? `background:${item.color}` : '';
      return `
  <div class="bar-chart-item">
    <span class="bar-chart-value">${formatNumber(item.count)}</span>
    <span class="bar-chart-bar" style="height: ${height}%; ${barStyle}"></span>
    <span class="bar-chart-label">${item.label}</span>
  </div>`;
    })
    .join('')}
</div>`;
  };

  const renderLineChart = (container, items) => {
    if (!container) return;
    if (!Array.isArray(items) || !items.length) {
      renderEmpty(container, 'No data yet.');
      return;
    }

    const values = items.map((item) => Number(item.count) || 0);
    const maxValue = Math.max(...values, 1);
    const minValue = Math.min(...values, 0);

    const width = 320;
    const height = 160;
    const padding = 24;
    const usableWidth = width - padding * 2;
    const usableHeight = height - padding * 2;

    const xStep = items.length > 1 ? usableWidth / (items.length - 1) : 0;
    const getX = (index) => (items.length === 1 ? width / 2 : padding + index * xStep);
    const getY = (value) => {
      if (maxValue === minValue) return height / 2;
      const ratio = (value - minValue) / (maxValue - minValue);
      return height - padding - ratio * usableHeight;
    };

    const points = values.map((value, index) => [getX(index), getY(value)]);
    const path = points
      .map((point, index) => `${index === 0 ? 'M' : 'L'} ${point[0]} ${point[1]}`)
      .join(' ');
    const areaPath = `${path} L ${points[points.length - 1][0]} ${height - padding} L ${points[0][0]} ${height - padding} Z`;
    const circles = points
      .map((point, index) => {
        return `<circle class="line-point" cx="${point[0]}" cy="${point[1]}" r="3.5"><title>${items[index].label}: ${formatNumber(values[index])}</title></circle>`;
      })
      .join('');

    container.innerHTML = `
<div class="line-chart-wrapper">
  <svg class="line-chart-svg" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" aria-hidden="true">
    <path class="line-area" d="${areaPath}"></path>
    <path class="line-path" d="${path}"></path>
    ${circles}
  </svg>
  <div class="line-chart-labels">${items.map((item) => `<span>${item.label}</span>`).join('')}</div>
</div>`;
  };

  const renderPieChart = (container, items, totalLabel) => {
    if (!container) return;
    if (!Array.isArray(items) || !items.length) {
      renderEmpty(container, 'No category data yet.');
      return;
    }

    const segments = items.map((item, index) => {
      const rawLabel = item.category ?? item.label ?? 'Other';
      const label = String(rawLabel).trim() || 'Other';
      return {
      label,
      value: Number(item.count) || 0,
      color: palette[index % palette.length],
      };
    });

    const { total, gradient, segments: normalized } = buildConicGradient(segments);
    if (!total) {
      renderEmpty(container, 'No category data yet.');
      return;
    }

    container.innerHTML = `
<div class="pie-wrap">
  <div class="pie-chart" style="background: conic-gradient(${gradient});">
    <div class="pie-center">
      <strong>${formatNumber(total)}</strong>
      <span>${totalLabel}</span>
    </div>
  </div>
</div>
<ul class="chart-legend">
  ${buildLegend(normalized, total)}
</ul>`;
  };

  const renderHistogramChart = (container, items) => {
    if (!container) return;
    if (!Array.isArray(items) || !items.length) {
      renderEmpty(container, 'No approval data yet.');
      return;
    }
    const total = items.reduce((sum, item) => sum + (Number(item.count) || 0), 0);
    if (!total) {
      renderEmpty(container, 'No approval data yet.');
      return;
    }
    const legendItems = items.map((item) => ({
      label: item.label,
      value: Number(item.count) || 0,
      color: item.color,
    }));
    container.innerHTML = `
<div class="bar-chart-grid histogram-grid">
  ${items
    .map((item) => {
      const height = total ? Math.round((Number(item.count) / total) * 100) : 0;
      return `
  <div class="bar-chart-item">
    <span class="bar-chart-value">${formatNumber(item.count)}</span>
    <span class="bar-chart-bar" style="height: ${height}%; background:${item.color}"></span>
    <span class="bar-chart-label">${item.label}</span>
  </div>`;
    })
    .join('')}
</div>
<ul class="chart-legend">
  ${buildLegend(legendItems, total)}
</ul>`;
  };

  const renderAlerts = (alerts = {}) => {
    setText(alertJobsPending, formatNumber(alerts.jobs_pending || 0));
    setText(alertComplaints, formatNumber(alerts.complaints_waiting || 0));
    setText(alertExpiringToday, formatNumber(alerts.expiring_today || 0));
    setText(alertSuspicious, formatNumber(alerts.suspicious_users || 0));
  };

  const renderActivity = (items = []) => {
    if (!recentActivityList) return;
    if (!Array.isArray(items) || !items.length) {
      recentActivityList.innerHTML = '<div class="activity-item"><div><strong>No recent activity</strong><span class="muted">Check back later</span></div><span class="activity-time">--</span></div>';
      return;
    }
    recentActivityList.innerHTML = items
      .map((item) => {
        const title = escapeHtml(item.title || 'Update');
        const value = escapeHtml(item.value || '-');
        const time = escapeHtml(item.time || '-');
        const url = typeof item.url === 'string' ? item.url.trim() : '';
        const safeUrl = url ? escapeAttr(url) : '';
        const openTag = safeUrl ? `<a class="activity-item activity-item-link" href="${safeUrl}">` : '<div class="activity-item">';
        const closeTag = safeUrl ? '</a>' : '</div>';
        return `
${openTag}
  <div>
    <strong>${title}</strong>
    <span class="muted">${value}</span>
  </div>
  <span class="activity-time">${time}</span>
${closeTag}`;
      })
      .join('');
  };

  const renderLocalFallback = () => {
    const jobs = loadLocalJobs();
    const stats = computeLocalJobStats(jobs);
    const categories = computeLocalCategories(jobs);
    setText(metricActiveJobsEl, formatNumber(stats.approved));
    setText(metricCandidatesEl, '0');
    setText(metricRecruitersEl, '0');
    setText(metricConsultanciesEl, '0');
    setText(metricTodayRegsEl, '0');
    setText(metricRevenueEl, formatCurrency(0));
    renderBarChart(chartJobsTrend, []);
    renderPieChart(chartJobCategories, categories, 'Jobs');
    renderBarChart(chartSubscriptionConversion, [
      { label: 'Paid', count: 0, color: '#10b981' },
      { label: 'Free', count: 0, color: '#6366f1' },
    ]);
    renderBarChart(chartUserTotals, [
      { label: 'Companies', count: 0, color: '#0ea5e9' },
      { label: 'Consultancies', count: 0, color: '#8b5cf6' },
      { label: 'Candidates', count: 0, color: '#22c55e' },
    ]);
    renderHistogramChart(chartApprovalTrend, [
      { label: 'Approved', count: stats.approved, color: '#22c55e' },
      { label: 'Rejected', count: stats.rejected, color: '#ef4444' },
    ]);
    renderAlerts({
      jobs_pending: stats.pending,
      complaints_waiting: 0,
      expiring_today: 0,
      suspicious_users: 0,
    });
    renderActivity([]);
  };

  const refreshData = async () => {
    const data = await fetchJson('/api/dashboard/metrics/');
    if (data.error) {
      renderLocalFallback();
      return;
    }

    const overview = data.overview || {};
    setText(metricActiveJobsEl, formatNumber(overview.active_jobs || 0));
    setText(metricCandidatesEl, formatNumber(overview.candidates || 0));
    setText(metricRecruitersEl, formatNumber(overview.recruiters || 0));
    setText(metricConsultanciesEl, formatNumber(overview.consultancies || 0));
    setText(metricTodayRegsEl, formatNumber(overview.todays_registrations || 0));
    setText(metricRevenueEl, formatCurrency(overview.revenue_month || 0));

    const trends = data.trends || {};
    const jobTrend = trends.job_postings || [];
    renderBarChart(chartJobsTrend, jobTrend);

    const approval = data.approval_ratio || {};
    renderHistogramChart(chartApprovalTrend, [
      { label: 'Approved', count: approval.approved || 0, color: '#22c55e' },
      { label: 'Rejected', count: approval.rejected || 0, color: '#ef4444' },
    ]);

    const categories = data.jobs && Array.isArray(data.jobs.categories) ? data.jobs.categories : [];
    renderPieChart(chartJobCategories, categories, 'Jobs');

    const conversion = data.conversion || {};
    renderBarChart(chartSubscriptionConversion, [
      { label: 'Paid', count: conversion.paid || 0, color: '#10b981' },
      { label: 'Free', count: conversion.free || 0, color: '#6366f1' },
    ]);

    const overviewTotals = data.overview || {};
    renderBarChart(chartUserTotals, [
      { label: 'Companies', count: overviewTotals.companies || 0, color: '#0ea5e9' },
      { label: 'Consultancies', count: overviewTotals.consultancies || 0, color: '#8b5cf6' },
      { label: 'Candidates', count: overviewTotals.candidates || 0, color: '#22c55e' },
    ]);

    renderAlerts(data.alerts || {});
    renderActivity(data.recent_activity || []);
  };

  window.addEventListener('storage', (event) => {
    if (event.key === STORAGE_KEY) {
      renderLocalFallback();
    }
  });

  refreshData();

  setInterval(() => {
    if (document.hidden) return;
    refreshData();
  }, pollInterval);
})();
