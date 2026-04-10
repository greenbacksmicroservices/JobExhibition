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
  const scheduleForm = document.querySelector('form.interview-form input[name="action"][value="schedule"]')?.closest('form') || null;
  const scheduleDateInput = scheduleForm ? scheduleForm.querySelector('input[name="interview_date"]') : null;
  const rescheduleForm = document.querySelector('#rescheduleModal form');
  const rescheduleDateInput = document.getElementById('rescheduleDate');

  const todayIsoDate = () => {
    const now = new Date();
    const local = new Date(now.getTime() - now.getTimezoneOffset() * 60000);
    return local.toISOString().slice(0, 10);
  };

  const applyDateBoundary = (input) => {
    if (!input) return '';
    const minDate = todayIsoDate();
    input.min = minDate;
    return minDate;
  };

  const clearDateError = (input) => {
    if (!input) return;
    input.classList.remove('field-error');
    input.setCustomValidity('');
  };

  const validateDateInput = (input) => {
    if (!input) return true;
    const minDate = applyDateBoundary(input);
    const selectedDate = (input.value || '').trim();
    if (!selectedDate) {
      clearDateError(input);
      return true;
    }
    if (selectedDate < minDate) {
      input.classList.add('field-error');
      input.setCustomValidity('Past interview date is not allowed. Please choose today or a future date.');
      return false;
    }
    clearDateError(input);
    return true;
  };

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

  if (scheduleDateInput) {
    applyDateBoundary(scheduleDateInput);
    scheduleDateInput.addEventListener('input', () => validateDateInput(scheduleDateInput));
    scheduleDateInput.addEventListener('change', () => validateDateInput(scheduleDateInput));
  }

  if (scheduleForm && scheduleDateInput) {
    scheduleForm.addEventListener('submit', (event) => {
      if (validateDateInput(scheduleDateInput)) return;
      event.preventDefault();
      scheduleDateInput.reportValidity();
    });
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
      validateDateInput(dateInput);
    });
  }

  if (rescheduleDateInput) {
    applyDateBoundary(rescheduleDateInput);
    rescheduleDateInput.addEventListener('input', () => validateDateInput(rescheduleDateInput));
    rescheduleDateInput.addEventListener('change', () => validateDateInput(rescheduleDateInput));
  }

  if (rescheduleForm && rescheduleDateInput) {
    rescheduleForm.addEventListener('submit', (event) => {
      if (validateDateInput(rescheduleDateInput)) return;
      event.preventDefault();
      rescheduleDateInput.reportValidity();
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
