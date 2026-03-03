(() => {
  const select = document.getElementById('shortlistedSelect');
  const nameInput = document.getElementById('candidateName');
  const emailInput = document.getElementById('candidateEmail');
  const jobInput = document.getElementById('jobTitle');
  const modeSelect = document.getElementById('interviewModeSelect');
  const linkGroup = document.getElementById('interviewMeetingLinkGroup');
  const locationGroup = document.getElementById('interviewLocationGroup');
  const meetingLinkInput = linkGroup ? linkGroup.querySelector('input[name="meeting_link"]') : null;
  const locationInput = locationGroup ? locationGroup.querySelector('input[name="location"]') : null;

  const syncCandidateFields = (option) => {
    if (!option) return;
    const name = option.getAttribute('data-name') || '';
    const email = option.getAttribute('data-email') || '';
    const job = option.getAttribute('data-job') || '';
    if (nameInput) nameInput.value = name;
    if (emailInput) emailInput.value = email;
    if (jobInput) jobInput.value = job;
  };

  if (select) {
    select.addEventListener('change', () => {
      const option = select.options[select.selectedIndex];
      syncCandidateFields(option);
    });

    const hasPrefilled = Boolean((nameInput && nameInput.value.trim()) || (emailInput && emailInput.value.trim()) || (jobInput && jobInput.value.trim()));
    if (!hasPrefilled && select.options.length > 1) {
      select.selectedIndex = 1;
      syncCandidateFields(select.options[1]);
    }
  }

  const syncModeFields = () => {
    if (!modeSelect || !linkGroup || !locationGroup || !meetingLinkInput || !locationInput) return;
    const isOffline = (modeSelect.value || '').trim().toLowerCase() === 'offline';
    locationGroup.style.display = isOffline ? 'block' : 'none';
    locationInput.required = isOffline;
    meetingLinkInput.required = !isOffline;
  };

  if (modeSelect) {
    modeSelect.addEventListener('change', syncModeFields);
    syncModeFields();
  }

  const modal = document.getElementById('rescheduleModal');
  if (modal) {
    modal.addEventListener('show.bs.modal', (event) => {
      const button = event.relatedTarget;
      if (!button) return;
      const interviewId = button.getAttribute('data-interview-id') || '';
      const interviewDate = button.getAttribute('data-interview-date') || '';
      const interviewTime = button.getAttribute('data-interview-time') || '';
      const idInput = document.getElementById('rescheduleInterviewId');
      const dateInput = document.getElementById('rescheduleDate');
      const timeInput = document.getElementById('rescheduleTime');
      if (idInput) idInput.value = interviewId;
      if (dateInput) dateInput.value = interviewDate;
      if (timeInput) timeInput.value = interviewTime;
    });
  }

  if (document.querySelector('.interview-summary')) {
    window.setInterval(() => {
      if (document.hidden) return;
      if (modal && modal.classList.contains('show')) return;
      const path = window.location.pathname || '';
      if (!path.includes('/company/interviews/')) return;
      window.location.reload();
    }, 60000);
  }
})();
