document.addEventListener('DOMContentLoaded', () => {
  const endpointNode = document.getElementById('consultancyMetricsEndpoint');
  const endpoint = (endpointNode && endpointNode.dataset.endpoint) || '/consultancy/api/metrics/';

  const toNumber = (value) => {
    const parsed = parseInt(String(value || '').replace(/[^0-9]/g, ''), 10);
    return Number.isNaN(parsed) ? 0 : parsed;
  };

  const formatNumber = (value) => {
    return value.toLocaleString('en-IN');
  };

  const setMetricValue = (id, value, options = {}) => {
    const el = document.getElementById(id);
    if (!el) return;
    const numeric = Number(value || 0);
    el.dataset.count = String(numeric);
    if (options.currency) {
      el.textContent = `INR ${formatNumber(numeric)}`;
      return;
    }
    el.textContent = formatNumber(numeric);
  };

  const animateCounts = () => {
    const elements = document.querySelectorAll('[data-count]');
    elements.forEach((el) => {
      const raw = el.getAttribute('data-count') || el.textContent;
      const target = toNumber(raw);
      const originalText = el.textContent || '';
      const prefixMatch = originalText.match(/^[^\d]+/);
      const suffixMatch = originalText.match(/[^\d]+$/);
      const prefix = prefixMatch ? prefixMatch[0].trim() : '';
      const suffix = suffixMatch && suffixMatch[0].trim() !== prefix ? suffixMatch[0].trim() : '';
      const duration = 900;
      const start = 0;
      const startTime = performance.now();

      const tick = (now) => {
        const progress = Math.min((now - startTime) / duration, 1);
        const value = Math.round(start + (target - start) * progress);
        const formatted = `${prefix ? `${prefix}` : ''}${formatNumber(value)}${suffix ? `${suffix}` : ''}`;
        el.textContent = formatted;
        if (progress < 1) {
          requestAnimationFrame(tick);
        }
      };

      requestAnimationFrame(tick);
    });
  };

  const updateBarChart = () => {
    const rows = document.querySelectorAll('.bar-row');
    if (!rows.length) return;

    let max = 0;
    rows.forEach((row) => {
      const valueEl = row.querySelector('[data-bar-value]');
      const value = toNumber(valueEl ? valueEl.textContent : row.dataset.value);
      row.dataset.value = value;
      if (value > max) max = value;
    });

    rows.forEach((row) => {
      const fill = row.querySelector('.bar-fill');
      if (!fill) return;
      fill.style.width = '0%';
      const value = toNumber(row.dataset.value);
      const percent = max ? (value / max) * 100 : 0;
      const minPercent = value > 0 ? 10 : 0;
      requestAnimationFrame(() => {
        fill.style.width = `${Math.max(percent, minPercent)}%`;
      });
    });
  };

  const updateTrendChart = () => {
    const bars = document.querySelectorAll('.trend-bar');
    if (!bars.length) return;

    let max = 0;
    bars.forEach((bar) => {
      const value = toNumber(bar.dataset.count || bar.querySelector('.trend-count')?.textContent);
      bar.dataset.count = value;
      if (value > max) max = value;
    });

    bars.forEach((bar) => {
      const fill = bar.querySelector('.trend-fill');
      if (!fill) return;
      fill.style.height = '0%';
      const value = toNumber(bar.dataset.count);
      const percent = max ? (value / max) * 100 : 0;
      const minPercent = value > 0 ? 12 : 0;
      requestAnimationFrame(() => {
        fill.style.height = `${Math.max(percent, minPercent)}%`;
      });
    });
  };

  const refreshMetrics = () => {
    fetch(endpoint, { credentials: 'same-origin' })
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (!data) return;
        const metrics = data.metrics || {};
        setMetricValue('metricConsultancyAssignedJobs', metrics.assigned_jobs);
        setMetricValue('metricConsultancyActiveJobs', metrics.active_jobs);
        setMetricValue('metricConsultancyCandidates', metrics.candidates);
        setMetricValue('metricConsultancyInterviews', metrics.interviews);
        setMetricValue('metricConsultancyPlacements', metrics.placements);
        setMetricValue('metricConsultancyPendingPayments', metrics.pending_payments, { currency: true });

        const pipeline = Array.isArray(data.pipeline) ? data.pipeline : [];
        pipeline.forEach((item) => {
          if (!item || !item.key) return;
          const value = Number(item.value || 0);
          const valueEl = document.querySelector(`[data-pipeline-key="${item.key}"]`);
          if (!valueEl) return;
          valueEl.textContent = formatNumber(value);
          const row = valueEl.closest('.bar-row');
          if (!row) return;
          row.dataset.value = String(value);
          const fill = row.querySelector('.bar-fill');
          if (fill) {
            fill.dataset.value = String(value);
          }
        });

        updateBarChart();
      })
      .catch(() => {});
  };

  animateCounts();
  updateBarChart();
  updateTrendChart();
  refreshMetrics();
  setInterval(refreshMetrics, 10000);
});
