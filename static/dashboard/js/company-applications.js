(() => {
  const detailModalEl = document.getElementById('candidateDetailModal');
  const scheduleModalEl = document.getElementById('scheduleInterviewModal');
  const detailModal = detailModalEl ? new bootstrap.Modal(detailModalEl) : null;
  const scheduleModal = scheduleModalEl ? new bootstrap.Modal(scheduleModalEl) : null;

  const selectAll = document.getElementById('selectAllApplications');
  const rowCheckboxes = () => Array.from(document.querySelectorAll('.row-select'));

  if (selectAll) {
    selectAll.addEventListener('change', () => {
      rowCheckboxes().forEach((box) => {
        box.checked = selectAll.checked;
      });
    });
  }

  const updateSelectAllState = () => {
    if (!selectAll) return;
    const boxes = rowCheckboxes();
    if (!boxes.length) return;
    const checked = boxes.filter((box) => box.checked).length;
    selectAll.indeterminate = checked > 0 && checked < boxes.length;
    selectAll.checked = checked === boxes.length;
  };

  rowCheckboxes().forEach((box) => {
    box.addEventListener('change', updateSelectAllState);
  });

  const toggleRowRejectionRemark = (form) => {
    if (!form) return;
    const statusSelect = form.querySelector('select[name="status"]');
    const remarkInput = form.querySelector('.rejection-remark-input');
    if (!statusSelect || !remarkInput) return;
    const isRejected = (statusSelect.value || '').toLowerCase() === 'rejected';
    remarkInput.style.display = isRejected ? 'block' : 'none';
    remarkInput.required = isRejected;
  };

  document.querySelectorAll('form.inline-form').forEach((form) => {
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

  const bulkForm = document.getElementById('bulkForm');
  const bulkActionSelect = bulkForm ? bulkForm.querySelector('select[name="bulk_action"]') : null;
  const bulkRejectRemark = document.getElementById('bulkRejectRemark');

  const toggleBulkRemarkField = () => {
    if (!bulkActionSelect || !bulkRejectRemark) return;
    const isReject = (bulkActionSelect.value || '').toLowerCase() === 'reject';
    bulkRejectRemark.style.display = isReject ? 'inline-flex' : 'none';
    bulkRejectRemark.required = isReject;
  };

  if (bulkActionSelect) {
    bulkActionSelect.addEventListener('change', toggleBulkRemarkField);
    toggleBulkRemarkField();
  }

  if (bulkForm) {
    bulkForm.addEventListener('submit', (event) => {
      if (!bulkActionSelect || !bulkRejectRemark) return;
      const isReject = (bulkActionSelect.value || '').toLowerCase() === 'reject';
      if (isReject && !bulkRejectRemark.value.trim()) {
        event.preventDefault();
        alert('Please add rejection remark for bulk reject action.');
      }
    });
  }

  const text = (value, fallback = '--') => {
    return value && String(value).trim() ? value : fallback;
  };

  const normalizeText = (value) => {
    if (!value) return value;
    return String(value).replace(/\\n/g, '\n');
  };

  const setText = (id, value, fallback) => {
    const el = document.getElementById(id);
    if (el) {
      el.textContent = text(value, fallback);
    }
  };

  const setValue = (id, value) => {
    const el = document.getElementById(id);
    if (el) {
      el.value = value || '';
    }
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

  const updateSkillMatch = (matchValue) => {
    const meter = document.getElementById('detailSkillMatch');
    const label = document.getElementById('detailSkillMatchLabel');
    if (!meter || !label) return;

    if (matchValue === '' || matchValue === undefined || matchValue === null) {
      meter.style.display = 'none';
      label.textContent = 'Skill match: --';
      return;
    }
    const percent = Number(matchValue);
    if (!Number.isFinite(percent)) {
      meter.style.display = 'none';
      label.textContent = 'Skill match: --';
      return;
    }

    meter.style.display = 'block';
    const bar = meter.querySelector('span');
    if (bar) {
      bar.style.width = `${Math.max(0, Math.min(100, percent))}%`;
    }
    label.textContent = `Skill match: ${percent}%`;
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
      previewBtn.style.display = 'inline-flex';
      downloadBtn.style.display = 'inline-flex';
      previewBtn.href = previewUrl;
      downloadBtn.href = downloadUrl || previewUrl;
      resumeName.textContent = name || 'Resume';
      resumeMeta.textContent = 'Preview available';
    } else {
      previewBtn.style.display = 'none';
      downloadBtn.style.display = 'none';
      resumeName.textContent = 'Resume';
      resumeMeta.textContent = '';
      resumeEmpty.style.display = 'block';
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
    setText('detailExpectedSalary', data.expectedSalary);
    setText('detailStatus', data.status);
    setText('detailCoverLetter', normalizeText(data.coverLetter) || '--', '--');

    updateSkills('detailSkills', data.skills);
    updateSkillMatch(data.skillMatch);
    updateResumeSection(data.resumePreviewUrl, data.resumeDownloadUrl, data.resumeName);

    setValue('notesApplicationId', data.appId);
    setValue('detailInternalNotes', normalizeText(data.internalNotes) || '');
    setValue('detailInterviewRemarks', normalizeText(data.interviewFeedback) || '');

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
    setValue('scheduleInterviewer', data.interviewer);
    setValue('scheduleFeedback', normalizeText(data.interviewFeedback) || '');
    scheduleModal.show();
  };

  document.querySelectorAll('[data-action="view-application"]').forEach((button) => {
    button.addEventListener('click', () => {
      const row = button.closest('tr');
      openDetailModal(row);
    });
  });

  document.querySelectorAll('[data-action="schedule-interview"]').forEach((button) => {
    button.addEventListener('click', () => {
      const row = button.closest('tr');
      openScheduleModal(row);
    });
  });
})();
