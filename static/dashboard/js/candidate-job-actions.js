document.addEventListener('DOMContentLoaded', () => {
  const saveButtons = Array.from(document.querySelectorAll('[data-save-job-btn]'));
  const similarToggleBtn = document.querySelector('[data-toggle-similar-jobs]');
  const similarPanel = document.querySelector('[data-similar-jobs-panel]');
  const savedJobsMeta = document.getElementById('savedJobsCountMeta');
  const savedMetric = document.getElementById('metricSavedJobs');
  const savedJobsBody = document.getElementById('savedJobsBody');
  const endpoint = '/candidate/api/saved-jobs/toggle/';

  const getCookie = (name) => {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
    return '';
  };

  const csrfToken =
    getCookie('csrftoken') ||
    document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') ||
    document.querySelector('input[name="csrfmiddlewaretoken"]')?.value ||
    '';

  const buttonsForJob = (jobId) =>
    saveButtons.filter((button) => String(button.dataset.jobId || '') === String(jobId || ''));

  const setButtonState = (button, saved) => {
    button.dataset.saved = saved ? '1' : '0';
    const isRemoveAction = button.dataset.removeRow === '1';
    if (isRemoveAction) {
      button.textContent = saved ? 'Remove' : 'Removed';
      button.disabled = !saved;
      return;
    }
    button.textContent = saved ? 'Saved' : 'Save Job';
  };

  const syncSavedCount = (count) => {
    if (savedJobsMeta) {
      savedJobsMeta.textContent = `Saved jobs: ${count}`;
    }
    if (savedMetric) {
      savedMetric.textContent = count;
    }
  };

  const removeSavedRowIfNeeded = (jobId, saved) => {
    if (saved || !savedJobsBody) return;
    const row = savedJobsBody.querySelector(`[data-saved-job-row][data-job-id="${jobId}"]`);
    if (row) {
      row.remove();
    }
    const dataRows = savedJobsBody.querySelectorAll('[data-saved-job-row]');
    if (!dataRows.length) {
      savedJobsBody.innerHTML = `
        <tr>
          <td colspan="5" class="muted" style="text-align:center; padding: 16px;">No saved jobs yet.</td>
        </tr>
      `;
    }
  };

  const toggleSavedJob = async (button) => {
    const jobId = button.dataset.jobId || '';
    if (!jobId) return;
    button.disabled = true;
    try {
      const formData = new URLSearchParams();
      formData.append('job_id', jobId);
      const response = await fetch(endpoint, {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
          'X-CSRFToken': csrfToken,
          'X-Requested-With': 'XMLHttpRequest',
        },
        body: formData.toString(),
      });
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      const payload = await response.json();
      if (!payload.success) {
        throw new Error(payload.error || 'Unable to update saved job.');
      }
      const saved = Boolean(payload.saved);
      buttonsForJob(jobId).forEach((item) => setButtonState(item, saved));
      syncSavedCount(Number(payload.saved_jobs_count || 0));
      removeSavedRowIfNeeded(jobId, saved);
    } catch (error) {
      // Keep silent to avoid blocking normal browsing flow.
    } finally {
      if (button.dataset.removeRow !== '1' || button.dataset.saved === '1') {
        button.disabled = false;
      }
    }
  };

  saveButtons.forEach((button) => {
    const initialSaved = button.dataset.saved === '1';
    setButtonState(button, initialSaved);
    button.addEventListener('click', (event) => {
      event.preventDefault();
      toggleSavedJob(button);
    });
  });

  if (similarToggleBtn && similarPanel) {
    similarToggleBtn.addEventListener('click', () => {
      const expanded = similarToggleBtn.getAttribute('aria-expanded') === 'true';
      const nextExpanded = !expanded;
      similarToggleBtn.setAttribute('aria-expanded', String(nextExpanded));
      similarPanel.hidden = !nextExpanded;
      if (nextExpanded) {
        similarPanel.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    });
  }
});
