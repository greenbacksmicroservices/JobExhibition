(() => {
  const select = document.getElementById('shortlistedSelect');
  const nameInput = document.getElementById('candidateName');
  const emailInput = document.getElementById('candidateEmail');
  const jobInput = document.getElementById('jobTitle');

  if (select) {
    select.addEventListener('change', () => {
      const option = select.options[select.selectedIndex];
      if (!option) return;
      const name = option.getAttribute('data-name') || '';
      const email = option.getAttribute('data-email') || '';
      const job = option.getAttribute('data-job') || '';
      if (nameInput) nameInput.value = name;
      if (emailInput) emailInput.value = email;
      if (jobInput) jobInput.value = job;
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
    });
  }
})();
