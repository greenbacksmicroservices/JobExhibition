(() => {
  const detailModalEl = document.getElementById('candidateDetailModal');
  const scheduleModalEl = document.getElementById('scheduleInterviewModal');
  const modalOptions = { backdrop: true, keyboard: true, focus: true };
  const detailModal = detailModalEl ? new bootstrap.Modal(detailModalEl, modalOptions) : null;
  const scheduleModal = scheduleModalEl ? new bootstrap.Modal(scheduleModalEl, modalOptions) : null;

  const text = (value, fallback = '--') => {
    return value && String(value).trim() ? value : fallback;
  };

  const normalizeText = (value) => {
    if (!value) return '';
    return String(value).replace(/\\n/g, '\n');
  };

  const setText = (id, value, fallback) => {
    const el = document.getElementById(id);
    if (el) el.textContent = text(value, fallback);
  };

  const setValue = (id, value) => {
    const el = document.getElementById(id);
    if (el) el.value = value || '';
  };

  const setLinkState = (link, url, enabled) => {
    if (!link) return;
    if (enabled) {
      link.href = url;
      link.classList.remove('disabled');
      link.removeAttribute('aria-disabled');
      return;
    }
    link.removeAttribute('href');
    link.classList.add('disabled');
    link.setAttribute('aria-disabled', 'true');
  };

  const updateResumeSection = (previewUrl, downloadUrl, name) => {
    const previewBtn = document.getElementById('detailResumePreview');
    const downloadBtn = document.getElementById('detailResumeDownload');
    const resumeName = document.getElementById('detailResumeName');
    const resumeMeta = document.getElementById('detailResumeMeta');
    const resumeEmpty = document.getElementById('detailResumeEmpty');
    if (!previewBtn || !downloadBtn || !resumeName || !resumeMeta || !resumeEmpty) return;

    if (previewUrl) {
      resumeEmpty.style.display = 'none';
      setLinkState(previewBtn, previewUrl, true);
      setLinkState(downloadBtn, downloadUrl || previewUrl, true);
      resumeName.textContent = name || 'Candidate Resume';
      resumeMeta.textContent = 'View and download resume';
      return;
    }

    setLinkState(previewBtn, '', false);
    setLinkState(downloadBtn, '', false);
    resumeName.textContent = 'Resume not available';
    resumeMeta.textContent = 'Candidate has not uploaded resume';
    resumeEmpty.style.display = 'block';
  };

  const updateSkills = (containerId, skillsRaw) => {
    const container = document.getElementById(containerId);
    if (!container) return;
    container.innerHTML = '';
    const skills = (skillsRaw || '')
      .split(',')
      .map((item) => item.trim())
      .filter(Boolean);

    if (!skills.length) {
      container.textContent = '--';
      return;
    }

    skills.forEach((skill) => {
      const tag = document.createElement('span');
      tag.className = 'skill-tag';
      tag.textContent = skill;
      container.appendChild(tag);
    });
  };

  const syncScheduleModeUI = () => {
    const modeSelect = document.getElementById('scheduleMode');
    const linkInput = document.getElementById('scheduleLink');
    const addressGroup = document.getElementById('scheduleAddressGroup');
    const addressInput = document.getElementById('scheduleAddress');
    if (!modeSelect || !linkInput || !addressGroup || !addressInput) return;

    const isOffline = (modeSelect.value || '').trim().toLowerCase() === 'offline';
    addressGroup.style.display = isOffline ? 'block' : 'none';
    addressInput.required = isOffline;
    linkInput.required = !isOffline;

    if (isOffline && !addressInput.value.trim() && linkInput.value.trim()) {
      addressInput.value = linkInput.value.trim();
    }
  };

  const openDetailModal = (row) => {
    if (!row || !detailModal) return;
    const data = row.dataset;

    setText('detailName', data.name);
    setText('detailEmail', data.email);
    setText('detailPhone', data.phone);
    setText('detailLocation', data.location);
    setText('detailExperience', data.experience);
    setText('detailCompany', data.currentCompany);
    setText('detailNotice', data.noticePeriod);
    setText('detailAppliedDate', data.appliedDate);
    setText('detailAppliedTime', data.appliedTime);
    setText('detailAppliedJob', data.jobTitle);
    setText('detailExpectedSalary', data.expectedSalary);
    setText('detailStatus', data.status);
    setText('detailRejectionRemark', normalizeText(data.rejectionRemark) || '--', '--');
    setText('detailCoverLetter', normalizeText(data.coverLetter) || '--', '--');

    const rejectionRow = document.getElementById('detailRejectionRow');
    if (rejectionRow) {
      const isRejected = (data.status || '').trim().toLowerCase() === 'rejected';
      const hasRemark = Boolean((data.rejectionRemark || '').trim());
      rejectionRow.style.display = isRejected || hasRemark ? 'flex' : 'none';
    }

    updateSkills('detailSkills', data.skills);
    updateResumeSection(data.resumePreviewUrl, data.resumeDownloadUrl, data.resumeName);

    setValue('notesApplicationId', data.appId);
    setValue('detailInternalNotes', normalizeText(data.internalNotes));
    setValue('detailInterviewRemarks', normalizeText(data.interviewFeedback));
    setValue('detailSummaryNotes', normalizeText(data.summary) || normalizeText(data.rejectionRemark));

    const modalTitle = document.getElementById('detailModalTitle');
    if (modalTitle) {
      modalTitle.textContent = `Candidate Details - ${text(data.name, 'Candidate')}`;
    }

    detailModal.show();
  };

  const openScheduleModal = (row) => {
    if (!row || !scheduleModal) return;
    const data = row.dataset;

    const scheduleTitle = document.getElementById('scheduleModalTitle');
    if (scheduleTitle) {
      scheduleTitle.textContent = `Schedule Interview - ${text(data.name, 'Candidate')}`;
    }
    setValue('scheduleApplicationId', data.appId);
    setValue('scheduleDate', data.interviewDate);
    setValue('scheduleTime', data.interviewTime);
    setValue('scheduleMode', data.interviewMode || 'Online');
    setValue('scheduleLink', data.meetingLink);
    setValue('scheduleAddress', data.meetingAddress || '');
    setValue('scheduleInterviewer', data.interviewer);
    setValue('scheduleFeedback', normalizeText(data.interviewFeedback));
    syncScheduleModeUI();

    scheduleModal.show();
  };

  const toggleRowRejectionRemark = (form) => {
    if (!form) return;
    const statusSelect = form.querySelector('select[name="status"]');
    const remarkInput = form.querySelector('.rejection-remark-input');
    if (!statusSelect || !remarkInput) return;
    const isRejected = (statusSelect.value || '').toLowerCase() === 'rejected';
    remarkInput.style.display = isRejected ? 'block' : 'none';
    remarkInput.required = isRejected;
  };

  document.querySelectorAll('form.consultancy-change-form').forEach((form) => {
    const statusSelect = form.querySelector('select[name="status"]');
    if (statusSelect) {
      statusSelect.addEventListener('change', () => toggleRowRejectionRemark(form));
      toggleRowRejectionRemark(form);
    }
    form.addEventListener('submit', (event) => {
      const currentStatus = (statusSelect && statusSelect.value ? statusSelect.value : '').toLowerCase();
      const remarkInput = form.querySelector('.rejection-remark-input');
      if (currentStatus === 'rejected' && remarkInput && !remarkInput.value.trim()) {
        event.preventDefault();
        alert('Please add rejection remark before rejecting this candidate.');
      }
    });
  });

  const scheduleModeSelect = document.getElementById('scheduleMode');
  if (scheduleModeSelect) {
    scheduleModeSelect.addEventListener('change', syncScheduleModeUI);
    syncScheduleModeUI();
  }

  document.addEventListener('click', (event) => {
    const actionBtn = event.target.closest('[data-action]');
    if (!actionBtn) return;
    const action = (actionBtn.dataset.action || '').trim();
    const row = actionBtn.closest('tr');
    if (!row) return;

    if (action === 'view-application') {
      openDetailModal(row);
      return;
    }
    if (action === 'schedule-interview') {
      openScheduleModal(row);
    }
  });
})();
