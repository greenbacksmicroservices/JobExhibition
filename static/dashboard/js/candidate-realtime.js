document.addEventListener('DOMContentLoaded', () => {
  const endpoint = '/candidate/api/metrics/';
  const metricTargets = [
    'metricProfileCompletion',
    'metricTotalApplications',
    'metricShortlisted',
    'metricInterviews',
    'metricSavedJobs',
    'metricRecommendedJobs',
    'profileCompletionBar',
  ];
  const shouldPoll = metricTargets.some((id) => document.getElementById(id));
  if (!shouldPoll) {
    return;
  }

  const updateText = (id, value) => {
    const el = document.getElementById(id);
    if (el) {
      el.textContent = value;
    }
  };

  const updateProfileBar = (value) => {
    const bar = document.getElementById('profileCompletionBar');
    if (bar) {
      bar.style.width = `${Math.min(Math.max(value, 0), 100)}%`;
    }
  };

  const updateMetricBars = (data) => {
    const keys = [
      'total_applications',
      'shortlisted',
      'interviews',
      'saved_jobs',
      'recommended_jobs',
    ];
    const max = Math.max(...keys.map((key) => Number(data[key] ?? 0)), 1);
    keys.forEach((key) => {
      const value = Number(data[key] ?? 0);
      const width = Math.max(8, Math.round((value / max) * 100));
      const fill = document.querySelector(`.metric-fill[data-metric-key="${key}"]`);
      if (fill) {
        fill.style.width = `${width}%`;
      }
    });
  };

  const refreshMetrics = () => {
    fetch(endpoint, { credentials: 'same-origin' })
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (!data) return;
        updateText('metricProfileCompletion', `${data.profile_completion ?? 0}%`);
        updateText('metricTotalApplications', data.total_applications ?? 0);
        updateText('metricShortlisted', data.shortlisted ?? 0);
        updateText('metricInterviews', data.interviews ?? 0);
        updateText('metricSavedJobs', data.saved_jobs ?? 0);
        updateText('metricRecommendedJobs', data.recommended_jobs ?? 0);
        updateProfileBar(data.profile_completion ?? 0);
        updateMetricBars(data);
      })
      .catch(() => {});
  };

  let pollHandle = null;
  const startPolling = () => {
    if (pollHandle) return;
    pollHandle = setInterval(refreshMetrics, 12000);
  };
  const stopPolling = () => {
    if (!pollHandle) return;
    clearInterval(pollHandle);
    pollHandle = null;
  };

  refreshMetrics();
  startPolling();

  document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
      stopPolling();
      return;
    }
    refreshMetrics();
    startPolling();
  });
});
