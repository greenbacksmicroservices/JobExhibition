(() => {
  const SCHEDULED_STORAGE_KEY = 'je_comm_scheduled_items_v1';

  const nowStamp = () =>
    new Date().toLocaleString('en-IN', {
      year: 'numeric',
      month: 'short',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    });

  const ensureToastContainer = () => {
    let container = document.getElementById('toastContainer');
    if (container) return container;
    container = document.createElement('div');
    container.id = 'toastContainer';
    container.className = 'toast-container';
    document.body.appendChild(container);
    return container;
  };

  const showToast = (message, tone = 'info') => {
    const container = ensureToastContainer();
    const toast = document.createElement('div');
    toast.className = `alert alert-${tone}`;
    toast.style.marginBottom = '8px';
    toast.style.minWidth = '220px';
    toast.textContent = message;
    container.appendChild(toast);
    window.setTimeout(() => {
      toast.remove();
    }, 2800);
  };

  const parseStoredScheduled = () => {
    try {
      const raw = localStorage.getItem(SCHEDULED_STORAGE_KEY);
      const parsed = raw ? JSON.parse(raw) : [];
      return Array.isArray(parsed) ? parsed : [];
    } catch (error) {
      return [];
    }
  };

  const storeScheduledItems = (items) => {
    localStorage.setItem(SCHEDULED_STORAGE_KEY, JSON.stringify(items));
  };

  const renderScheduledCard = (grid, item) => {
    if (!grid || !item) return;
    const card = document.createElement('article');
    card.className = 'schedule-card';
    card.setAttribute('data-scheduled-id', item.id);
    card.innerHTML = `
      <div>
        <h4>${item.title}</h4>
        <p class="muted">${item.channel} - ${item.audience}</p>
      </div>
      <div class="schedule-meta">
        <span>Scheduled: ${item.scheduled_for}</span>
        <span class="badge warning">Scheduled</span>
      </div>
      <div class="schedule-actions">
        <button class="action-btn" type="button" data-cancel-scheduled="${item.id}">Cancel</button>
      </div>
    `;
    grid.prepend(card);
  };

  const wireScheduledCancelButtons = () => {
    const cancelButtons = document.querySelectorAll('[data-cancel-scheduled]');
    cancelButtons.forEach((button) => {
      if (button.dataset.bound === '1') return;
      button.dataset.bound = '1';
      button.addEventListener('click', () => {
        const itemId = button.getAttribute('data-cancel-scheduled');
        const all = parseStoredScheduled().filter((item) => String(item.id) !== String(itemId));
        storeScheduledItems(all);
        const card = button.closest('[data-scheduled-id]');
        if (card) {
          card.remove();
        }
        showToast('Scheduled message cancelled.', 'warning');
      });
    });
  };

  const hydrateScheduledGrid = () => {
    const scheduleGrid = document.querySelector('.schedule-grid');
    if (!scheduleGrid) return;
    const existingIds = new Set(
      Array.from(scheduleGrid.querySelectorAll('[data-scheduled-id]')).map((el) => el.getAttribute('data-scheduled-id')),
    );
    const stored = parseStoredScheduled();
    stored.forEach((item) => {
      if (!existingIds.has(String(item.id))) {
        renderScheduledCard(scheduleGrid, item);
      }
    });
    wireScheduledCancelButtons();
  };

  const appendSentHistoryRow = ({ channel, title, audience, status = 'Delivered' }) => {
    const tables = Array.from(document.querySelectorAll('table'));
    const sentTable = tables.find((table) => {
      const headText = (table.querySelector('thead')?.innerText || '').toLowerCase();
      return headText.includes('subject / template') && headText.includes('recipients');
    });
    if (!sentTable) return;
    const tbody = sentTable.querySelector('tbody');
    if (!tbody) return;
    const row = document.createElement('tr');
    row.innerHTML = `
      <td><span class="badge info">${channel}</span></td>
      <td>${title || 'Campaign Update'}</td>
      <td>${audience || 'Custom'}</td>
      <td>${nowStamp()}</td>
      <td>1</td>
      <td>1</td>
      <td>0</td>
      <td><span class="badge ${status === 'Scheduled' ? 'warning' : 'success'}">${status}</span></td>
      <td>${channel === 'Email' ? '35%' : '-'}</td>
    `;
    tbody.prepend(row);
  };

  const countCustomRecipients = (form) => {
    const checked = form.querySelectorAll('input[name="custom_candidate_ids"]:checked');
    return checked.length;
  };

  const inferAudience = (form) => {
    const checkedLabel = Array.from(form.querySelectorAll('.checkbox-grid input[type="checkbox"]:checked'))
      .map((input) => input.closest('label')?.innerText?.trim() || '')
      .find((value) => value && value !== 'Custom Selected');
    if (checkedLabel) return checkedLabel;
    if (countCustomRecipients(form) > 0) return 'Custom Selection';
    const select = form.querySelector('[data-custom-select]');
    if (select && (select.value || '').toLowerCase() === 'custom') return 'Custom Selection';
    return 'All Applicants';
  };

  const inferTitle = (form) => {
    const templateSelect = form.querySelector('select');
    const subject = form.querySelector('input[type="text"]');
    const editor = form.querySelector('.rich-editor');
    if (subject && subject.value.trim()) return subject.value.trim();
    if (templateSelect && templateSelect.options[templateSelect.selectedIndex]) {
      return templateSelect.options[templateSelect.selectedIndex].text.trim();
    }
    if (editor && editor.innerText.trim()) {
      return editor.innerText.trim().slice(0, 60);
    }
    return 'Communication Update';
  };

  const inferChannel = (form) => {
    const cardTitle = form.closest('.card')?.querySelector('h3')?.innerText?.trim() || '';
    if (cardTitle.toLowerCase().includes('sms')) return 'SMS';
    if (cardTitle.toLowerCase().includes('whatsapp')) return 'WhatsApp';
    if (cardTitle.toLowerCase().includes('notification')) return 'Notification';
    return 'Email';
  };

  const getScheduleValue = (form) => {
    const input = form.querySelector('input[type="datetime-local"]');
    return input ? input.value : '';
  };

  const scheduleMessage = (form) => {
    const scheduledFor = getScheduleValue(form);
    if (!scheduledFor) {
      showToast('Please choose schedule date and time first.', 'warning');
      return;
    }
    const item = {
      id: Date.now(),
      channel: inferChannel(form),
      title: inferTitle(form),
      audience: inferAudience(form),
      scheduled_for: scheduledFor.replace('T', ' '),
    };
    const stored = parseStoredScheduled();
    stored.unshift(item);
    storeScheduledItems(stored.slice(0, 80));
    const scheduleGrid = document.querySelector('.schedule-grid');
    if (scheduleGrid) {
      renderScheduledCard(scheduleGrid, item);
      wireScheduledCancelButtons();
    }
    appendSentHistoryRow({
      channel: item.channel,
      title: item.title,
      audience: item.audience,
      status: 'Scheduled',
    });
    showToast(`${item.channel} message scheduled successfully.`, 'success');
  };

  const sendMessageNow = (form) => {
    const channel = inferChannel(form);
    const title = inferTitle(form);
    const audience = inferAudience(form);
    const customCount = countCustomRecipients(form);
    if (audience === 'Custom Selection' && customCount === 0) {
      showToast('Please select at least one candidate in Custom Selection.', 'warning');
      return;
    }
    appendSentHistoryRow({
      channel,
      title,
      audience,
      status: 'Delivered',
    });
    showToast(`${channel} sent successfully to ${audience}.`, 'success');
  };

  const bindFormActions = () => {
    const forms = document.querySelectorAll('.comm-form');
    forms.forEach((form) => {
      const sendBtn = form.querySelector('.form-actions .btn.primary');
      const scheduleBtn = Array.from(form.querySelectorAll('.form-actions .btn.ghost')).find((btn) =>
        (btn.innerText || '').toLowerCase().includes('schedule'),
      );
      if (sendBtn && sendBtn.dataset.bound !== '1') {
        sendBtn.dataset.bound = '1';
        sendBtn.addEventListener('click', () => sendMessageNow(form));
      }
      if (scheduleBtn && scheduleBtn.dataset.bound !== '1') {
        scheduleBtn.dataset.bound = '1';
        scheduleBtn.addEventListener('click', () => scheduleMessage(form));
      }
    });
  };

  const bindTemplateUseButtons = () => {
    const buttons = document.querySelectorAll('.template-card .action-btn');
    buttons.forEach((button) => {
      if (button.dataset.bound === '1') return;
      button.dataset.bound = '1';
      button.addEventListener('click', () => {
        const card = button.closest('.template-card');
        if (!card) return;
        const title = card.querySelector('h4')?.innerText?.trim() || '';
        const body = card.querySelector('.template-body')?.innerText?.trim() || '';
        const subjectInput = document.querySelector('#bulkEmailSubject, input[name="subject"], .comm-form input[type="text"]');
        const editor = document.querySelector('#bulkEmailEditor');
        const textArea = document.querySelector('.comm-form textarea');
        if (subjectInput) subjectInput.value = title;
        if (editor) {
          editor.innerText = body;
        } else if (textArea) {
          textArea.value = body;
        }
        showToast(`Template loaded: ${title}`, 'info');
      });
    });
  };

  document.querySelectorAll('.sms-textarea').forEach((smsTextarea) => {
    const card = smsTextarea.closest('.form-group') || smsTextarea.parentElement;
    const charCount = card ? card.querySelector('.char-count') : null;
    if (!charCount) return;
    const updateCount = () => {
      const count = smsTextarea.value.length;
      charCount.textContent = `${count} / 160`;
    };
    smsTextarea.addEventListener('input', updateCount);
    updateCount();
  });

  const previewBtn = document.getElementById('emailPreviewBtn');
  const subjectInput = document.getElementById('bulkEmailSubject');
  const editor = document.getElementById('bulkEmailEditor');
  const previewSubject = document.getElementById('emailPreviewSubject');
  const previewBody = document.getElementById('emailPreviewBody');

  const updatePreview = () => {
    if (!previewSubject || !previewBody) return;
    const subject = subjectInput && subjectInput.value ? subjectInput.value : 'No subject';
    const bodyText = editor ? editor.innerText.trim() : '';
    previewSubject.textContent = subject;
    previewBody.textContent = bodyText || 'No content yet.';
  };

  if (previewBtn) {
    previewBtn.addEventListener('click', updatePreview);
  }

  const pickerGroups = document.querySelectorAll('[data-custom-recipient-group]');

  const updatePickerVisibility = (groupId) => {
    const group = document.querySelector(`[data-custom-recipient-group="${groupId}"]`);
    if (!group) return;

    const checkboxToggles = document.querySelectorAll(`[data-custom-toggle="${groupId}"]`);
    const selectToggles = document.querySelectorAll(`[data-custom-select="${groupId}"]`);

    const checkboxEnabled = Array.from(checkboxToggles).some((input) => input.checked);
    const selectEnabled = Array.from(selectToggles).some(
      (select) => (select.value || '').toLowerCase() === 'custom',
    );
    const shouldShow = checkboxEnabled || selectEnabled;
    group.hidden = !shouldShow;
    if (shouldShow) {
      const searchInput = group.querySelector('[data-custom-search]');
      if (searchInput && document.activeElement !== searchInput) {
        searchInput.focus();
      }
    }
  };

  pickerGroups.forEach((group) => {
    const groupId = group.getAttribute('data-custom-recipient-group');
    if (!groupId) return;

    const checkboxToggles = document.querySelectorAll(`[data-custom-toggle="${groupId}"]`);
    checkboxToggles.forEach((input) => {
      input.addEventListener('change', () => updatePickerVisibility(groupId));
    });

    const selectToggles = document.querySelectorAll(`[data-custom-select="${groupId}"]`);
    selectToggles.forEach((select) => {
      select.addEventListener('change', () => updatePickerVisibility(groupId));
    });

    const searchInput = group.querySelector('[data-custom-search]');
    const searchButton = group.querySelector('[data-custom-search-btn]');
    const countLabel = group.querySelector('[data-custom-count]');
    const options = Array.from(group.querySelectorAll('.custom-recipient-item'));
    const emptyState = group.querySelector('[data-custom-empty]');

    const runFilter = () => {
      if (!searchInput) return;
      const query = (searchInput.value || '').trim().toLowerCase();
      let visibleCount = 0;
      let selectedCount = 0;
      options.forEach((option) => {
        const haystack = (option.getAttribute('data-search-text') || '').toLowerCase();
        const isVisible = !query || haystack.includes(query);
        option.hidden = !isVisible;
        if (isVisible) visibleCount += 1;
        const checkbox = option.querySelector('input[type="checkbox"]');
        if (checkbox && checkbox.checked) selectedCount += 1;
      });
      if (emptyState) {
        emptyState.hidden = visibleCount > 0;
      }
      if (countLabel) {
        countLabel.textContent = `${visibleCount} visible candidate(s) | ${selectedCount} selected`;
      }
    };

    if (searchInput) {
      searchInput.addEventListener('input', runFilter);
      runFilter();
    }
    if (searchButton) {
      searchButton.addEventListener('click', runFilter);
    }
    options.forEach((option) => {
      const checkbox = option.querySelector('input[type="checkbox"]');
      if (!checkbox) return;
      checkbox.addEventListener('change', runFilter);
    });

    updatePickerVisibility(groupId);
  });

  bindFormActions();
  bindTemplateUseButtons();
  hydrateScheduledGrid();
  wireScheduledCancelButtons();
})();
