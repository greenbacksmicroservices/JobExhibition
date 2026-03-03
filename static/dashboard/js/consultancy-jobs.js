document.addEventListener('DOMContentLoaded', () => {
  const statusSelect = document.getElementById('jobStatusSelect');
  const statusValue = document.getElementById('jobStatusValue');
  const statusButtons = document.querySelectorAll('[data-job-status]');

  if (!statusSelect || !statusValue) return;

  const statusMap = {
    Draft: 'Pending',
    Active: 'Approved',
    Paused: 'Pending',
    Closed: 'Approved',
    Expired: 'Approved',
    Archived: 'Reported',
  };

  const syncStatus = () => {
    const lifecycle = statusSelect.value;
    statusValue.value = statusMap[lifecycle] || 'Pending';
    statusButtons.forEach((button) => {
      button.classList.toggle('active', button.dataset.jobStatus === lifecycle);
    });
  };

  statusButtons.forEach((button) => {
    button.addEventListener('click', () => {
      statusSelect.value = button.dataset.jobStatus || statusSelect.value;
      syncStatus();
    });
  });

  statusSelect.addEventListener('change', syncStatus);
  syncStatus();
});
