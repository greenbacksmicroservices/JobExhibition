(() => {
  const detailModalEl = document.getElementById('candidateDetailModal');
  const scheduleModalEl = document.getElementById('scheduleInterviewModal');
  const chatModalEl = document.getElementById('candidateChatModal');
  const modalOptions = { backdrop: true, keyboard: true, focus: true };
  const detailModal = detailModalEl ? new bootstrap.Modal(detailModalEl, modalOptions) : null;
  const scheduleModal = scheduleModalEl ? new bootstrap.Modal(scheduleModalEl, modalOptions) : null;
  const chatModal = chatModalEl ? new bootstrap.Modal(chatModalEl, modalOptions) : null;

  const cleanupModalArtifacts = () => {
    const visibleModal = document.querySelector('.modal.show');
    const backdrops = Array.from(document.querySelectorAll('.modal-backdrop'));
    if (visibleModal) {
      if (backdrops.length > 1) {
        backdrops.slice(0, -1).forEach((node) => node.remove());
      }
      return;
    }
    backdrops.forEach((node) => node.remove());
    document.body.classList.remove('modal-open');
    document.body.style.removeProperty('padding-right');
  };

  [detailModalEl, scheduleModalEl, chatModalEl].forEach((modalEl) => {
    if (!modalEl) return;
    modalEl.addEventListener('hidden.bs.modal', cleanupModalArtifacts);
  });

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
    if (!value) return '';
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
    updateSkillMatch(data.skillMatch);
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

  const getCookie = (name) => {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
    return '';
  };

  const escapeHtml = (value) =>
    String(value ?? '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');

  const chatModalTitle = document.getElementById('candidateChatModalTitle');
  const chatLiveBadge = document.getElementById('candidateChatLiveBadge');
  const chatThreadMeta = document.getElementById('candidateChatThreadMeta');
  const chatMessages = document.getElementById('candidateChatMessages');
  const chatSyncInfo = document.getElementById('candidateChatSyncInfo');
  const chatForm = document.getElementById('candidateChatForm');
  const chatInput = document.getElementById('candidateChatInput');
  const chatAttachment = document.getElementById('candidateChatAttachment');
  const chatSendBtn = document.getElementById('candidateChatSendBtn');
  const chatFullPageLink = document.getElementById('candidateChatFullPageLink');

  const chatState = {
    pollHandle: null,
    messagesEndpoint: '',
    sendEndpoint: '',
    activeThreadId: '',
    viewerRole: 'company',
    activeBootstrapUrl: '',
    activeMessagePageUrl: '',
  };

  const updateChatBadge = (textValue, tone = 'info') => {
    if (!chatLiveBadge) return;
    chatLiveBadge.textContent = textValue;
    chatLiveBadge.classList.remove('info', 'success', 'warning', 'danger');
    chatLiveBadge.classList.add(tone);
  };

  const renderChatMessages = (messages) => {
    if (!chatMessages) return;
    if (!messages.length) {
      chatMessages.innerHTML = '<div class="analysis-card"><strong>No messages yet</strong><p class="muted">Start the conversation now.</p></div>';
      return;
    }

    const nearBottom = chatMessages.scrollHeight - chatMessages.scrollTop - chatMessages.clientHeight < 120;
    chatMessages.innerHTML = messages
      .map((msg) => {
        const own = (msg.sender_role || '') === chatState.viewerRole;
        const sideClass = own ? 'company' : 'support';
        const attachment = msg.attachment_url
          ? `<a class="attachment-link" href="${escapeHtml(msg.attachment_url)}" target="_blank" rel="noopener">View attachment</a>`
          : '';
        const body = msg.body ? `<p>${escapeHtml(msg.body)}</p>` : '';
        return `
          <div class="chat-message ${sideClass}">
            <div class="chat-bubble">
              <div class="chat-meta">
                <strong>${escapeHtml(msg.sender_name || 'User')}</strong>
                <span class="muted">${escapeHtml(msg.created_display || '--')}</span>
              </div>
              ${body}
              ${attachment}
            </div>
          </div>`;
      })
      .join('');

    if (nearBottom) {
      chatMessages.scrollTop = chatMessages.scrollHeight;
    }
  };

  const refreshChatMessages = async () => {
    if (!chatState.messagesEndpoint) return;
    try {
      const response = await fetch(`${chatState.messagesEndpoint}?mark_read=1`, {
        credentials: 'same-origin',
      });
      const payload = await response.json();
      if (!response.ok || !payload.success) {
        updateChatBadge('Retrying...', 'warning');
        return;
      }
      chatState.viewerRole = payload.viewer_role || chatState.viewerRole;
      renderChatMessages(Array.isArray(payload.messages) ? payload.messages : []);
      if (chatSyncInfo) {
        chatSyncInfo.textContent = `Last sync: ${payload.generated_at || '--'}`;
      }
      updateChatBadge('Live', 'success');
    } catch (error) {
      updateChatBadge('Retrying...', 'warning');
    }
  };

  const stopChatPolling = () => {
    if (!chatState.pollHandle) return;
    clearInterval(chatState.pollHandle);
    chatState.pollHandle = null;
  };

  const startChatPolling = () => {
    stopChatPolling();
    chatState.pollHandle = setInterval(() => {
      if (document.hidden) return;
      refreshChatMessages();
    }, 5000);
  };

  const openChatModal = async (row) => {
    if (!chatModal || !row) return;

    const bootstrapUrl = (row.dataset.threadBootstrapUrl || '').trim();
    const messagePageUrl = (row.dataset.messagePageUrl || '').trim();
    if (!bootstrapUrl) {
      alert('Unable to open chat for this candidate.');
      return;
    }

    chatState.activeBootstrapUrl = bootstrapUrl;
    chatState.activeMessagePageUrl = messagePageUrl;
    chatState.messagesEndpoint = '';
    chatState.sendEndpoint = '';
    chatState.activeThreadId = '';
    chatState.viewerRole = 'company';
    stopChatPolling();

    if (chatModalTitle) {
      chatModalTitle.textContent = `Chat - ${text(row.dataset.name, 'Candidate')}`;
    }
    if (chatThreadMeta) {
      chatThreadMeta.textContent = 'Connecting to conversation...';
    }
    if (chatMessages) {
      chatMessages.innerHTML = '<div class="analysis-card"><strong>Loading...</strong><p class="muted">Please wait while we open candidate thread.</p></div>';
    }
    if (chatFullPageLink) {
      chatFullPageLink.href = messagePageUrl || '/company/messages/';
    }
    updateChatBadge('Connecting...', 'info');
    chatModal.show();

    try {
      const response = await fetch(bootstrapUrl, { credentials: 'same-origin' });
      const payload = await response.json();
      if (!response.ok || !payload.success) {
        throw new Error(payload.error || 'Unable to open chat thread');
      }
      const thread = payload.thread || {};
      chatState.activeThreadId = thread.id || '';
      chatState.messagesEndpoint = thread.messages_endpoint || '';
      chatState.sendEndpoint = thread.send_endpoint || '';
      if (chatThreadMeta) {
        chatThreadMeta.textContent = `${text(thread.partner_name, 'Candidate')} - ${text(thread.job_title, 'Job')} (Application ${text(thread.application_id, '--')})`;
      }
      if (chatFullPageLink && messagePageUrl) {
        chatFullPageLink.href = messagePageUrl;
      }

      await refreshChatMessages();
      startChatPolling();
    } catch (error) {
      if (chatMessages) {
        chatMessages.innerHTML = `<div class="analysis-card"><strong>Unable to load chat</strong><p class="muted">${escapeHtml(error.message || 'Please try again.')}</p></div>`;
      }
      updateChatBadge('Disconnected', 'danger');
    }
  };

  if (chatModalEl) {
    chatModalEl.addEventListener('hidden.bs.modal', () => {
      stopChatPolling();
      cleanupModalArtifacts();
    });
  }

  if (chatForm) {
    chatForm.addEventListener('submit', async (event) => {
      event.preventDefault();
      if (!chatState.sendEndpoint) return;

      const messageBody = (chatInput ? chatInput.value : '').trim();
      const hasAttachment = Boolean(chatAttachment && chatAttachment.files && chatAttachment.files.length);
      if (!messageBody && !hasAttachment) return;

      const formData = new FormData(chatForm);
      if (chatSendBtn) chatSendBtn.disabled = true;
      updateChatBadge('Sending...', 'info');
      try {
        const response = await fetch(chatState.sendEndpoint, {
          method: 'POST',
          credentials: 'same-origin',
          headers: {
            'X-CSRFToken': getCookie('csrftoken'),
          },
          body: formData,
        });
        const payload = await response.json();
        if (!response.ok || !payload.success) {
          throw new Error(payload.error || 'Unable to send message.');
        }
        if (chatInput) chatInput.value = '';
        if (chatAttachment) chatAttachment.value = '';
        await refreshChatMessages();
      } catch (error) {
        updateChatBadge('Send failed', 'danger');
      } finally {
        if (chatSendBtn) chatSendBtn.disabled = false;
      }
    });
  }

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
      return;
    }
    if (action === 'chat-candidate') {
      openChatModal(row);
    }
  });
})();
