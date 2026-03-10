document.addEventListener('DOMContentLoaded', () => {
  const statusSelect = document.getElementById('jobStatusSelect');
  const statusValue = document.getElementById('jobStatusValue');
  const statusButtons = document.querySelectorAll('[data-job-status]');

  if (!statusSelect || !statusButtons.length || !statusValue) return;

  const statusMap = {
    Draft: 'Pending',
    Active: 'Approved',
    Paused: 'Pending',
    Closed: 'Approved',
    Expired: 'Approved',
    Archived: 'Reported',
    Rejected: 'Rejected',
  };

  const syncStatusButtons = () => {
    const value = statusSelect.value;
    statusValue.value = statusMap[value] || statusValue.value || 'Pending';
    statusButtons.forEach((button) => {
      button.classList.toggle('active', button.dataset.jobStatus === value);
    });
  };

  statusButtons.forEach((button) => {
    button.addEventListener('click', () => {
      statusSelect.value = button.dataset.jobStatus || statusSelect.value;
      syncStatusButtons();
    });
  });

  statusSelect.addEventListener('change', syncStatusButtons);
  syncStatusButtons();
});
