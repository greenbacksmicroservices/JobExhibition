document.addEventListener('DOMContentLoaded', () => {
  const endpoint = '/company/api/metrics/';
  const updateText = (id, value) => {
    const el = document.getElementById(id);
    if (el) {
      el.textContent = value;
    }
  };

  const toNumber = (value) => {
    const parsed = parseInt(String(value || '').replace(/[^0-9]/g, ''), 10);
    return Number.isNaN(parsed) ? 0 : parsed;
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
      const minPercent = value > 0 ? 8 : 0;
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

  const updateInterviewCalendar = () => {
    const calendar = document.getElementById('interviewCalendar');
    if (!calendar) return;

    const days = Array.from(calendar.querySelectorAll('.calendar-day'));
    if (!days.length) return;

    const today = new Date();
    const dayIndex = (today.getDay() + 6) % 7;
    const monday = new Date(today);
    monday.setDate(today.getDate() - dayIndex);

    let maxCount = 0;
    days.forEach((day) => {
      const count = toNumber(day.dataset.count);
      if (count > maxCount) maxCount = count;
    });

    days.forEach((day, index) => {
      const date = new Date(monday);
      date.setDate(monday.getDate() + index);
      const dateCell = day.querySelector('[data-date]');
      const metaCell = day.querySelector('[data-meta]');
      const count = toNumber(day.dataset.count);

      if (dateCell) {
        dateCell.textContent = date.getDate();
      }
      if (metaCell) {
        metaCell.textContent = `${count} ${count === 1 ? 'Interview' : 'Interviews'}`;
      }

      day.classList.toggle('today', date.toDateString() === today.toDateString());
      day.classList.toggle('has-interviews', count > 0);
    });

    days.forEach((day) => day.classList.remove('active'));
    const topDay = days.find((day) => toNumber(day.dataset.count) === maxCount && maxCount > 0);
    if (topDay) {
      topDay.classList.add('active');
    } else {
      const todayCard = days.find((day) => day.classList.contains('today'));
      if (todayCard) {
        todayCard.classList.add('active');
      }
    }
  };

  const refreshMetrics = () => {
    fetch(endpoint, { credentials: 'same-origin' })
      .then((res) => res.ok ? res.json() : null)
      .then((data) => {
        if (!data) return;
        updateText('metricActiveJobs', data.active_jobs ?? 0);
        updateText('metricTotalApplications', data.total_applications ?? 0);
        updateText('metricShortlisted', data.shortlisted ?? 0);
        updateText('metricInterviews', data.interviews ?? 0);
        updateText('metricTotalApplicationsBar', data.total_applications ?? 0);
        updateText('metricShortlistedBar', data.shortlisted ?? 0);
        updateText('metricOnHoldBar', data.on_hold ?? 0);
        updateText('metricRejectedBar', data.rejected ?? 0);
        updateBarChart();
      })
      .catch(() => {});
  };

  updateBarChart();
  updateTrendChart();
  updateInterviewCalendar();
  refreshMetrics();
  setInterval(refreshMetrics, 30000);
});
