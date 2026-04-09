(() => {
  const initThreadSearch = () => {
    const inputs = Array.from(document.querySelectorAll('[data-thread-search]'));
    if (!inputs.length) return;

    inputs.forEach((input) => {
      const panel = input.closest('.chat-thread-panel');
      if (!panel) return;
      const list = panel.querySelector('.chat-thread-list');
      if (!list) return;
      const rows = Array.from(list.querySelectorAll('.chat-thread'));
      if (!rows.length) return;
      const searchButton = panel.querySelector('[data-thread-search-btn]');

      let empty = list.querySelector('[data-thread-search-empty]');
      if (!empty) {
        empty = document.createElement('div');
        empty.className = 'analysis-card';
        empty.setAttribute('data-thread-search-empty', '');
        empty.innerHTML = '<strong>No matching conversation</strong><p class="muted">Try another name, job title, or application id.</p>';
        empty.hidden = true;
        list.appendChild(empty);
      }

      const applySearch = () => {
        const query = (input.value || '').trim().toLowerCase();
        let visibleCount = 0;
        rows.forEach((row) => {
          const haystack = (
            row.getAttribute('data-thread-search-text') ||
            row.innerText ||
            row.textContent ||
            ''
          ).toLowerCase();
          const shouldShow = !query || haystack.includes(query);
          row.classList.toggle('hidden-by-search', !shouldShow);
          if (shouldShow) visibleCount += 1;
        });
        empty.hidden = !(query && visibleCount === 0);
      };

      input.addEventListener('input', applySearch);
      if (searchButton) {
        searchButton.addEventListener('click', applySearch);
      }
      applySearch();
    });
  };

  initThreadSearch();

  const threadPanels = Array.from(document.querySelectorAll('[data-thread-live="1"]'));
  if (!threadPanels.length) return;

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

  const updateLiveBadge = (element, text, tone = 'info') => {
    if (!element) return;
    element.textContent = text;
    element.classList.remove('info', 'success', 'warning', 'danger');
    element.classList.add(tone);
  };

  const renderMessageItem = (message, viewerRole, mode) => {
    const isOwn = (message.sender_role || '') === viewerRole;
    const wrapperClass = mode === 'chat'
      ? `chat-message ${isOwn ? 'company' : 'support'}`
      : `message-row ${isOwn ? 'company' : 'support'}`;
    const bubbleClass = mode === 'chat' ? 'chat-bubble' : 'message-bubble';
    const attachment = message.attachment_url
      ? `<a class="action-link" href="${escapeHtml(message.attachment_url)}" target="_blank" rel="noopener">View attachment</a>`
      : '';
    const body = message.body ? `<p>${escapeHtml(message.body)}</p>` : '';
    const meta = mode === 'chat'
      ? `<div class="chat-meta"><strong>${escapeHtml(message.sender_name || 'User')}</strong><span class="muted">${escapeHtml(message.created_display || '--')}</span></div>`
      : `<strong>${escapeHtml(message.sender_name || 'User')}</strong><span class="muted">${escapeHtml(message.created_display || '--')}</span>`;
    return `
<div class="${wrapperClass}">
  <div class="${bubbleClass}">
    ${meta}
    ${body}
    ${attachment}
  </div>
</div>`;
  };

  const renderEmptyState = (messagesEl, mode) => {
    if (!messagesEl) return;
    if (mode === 'chat') {
      messagesEl.innerHTML = '<div class="analysis-card"><strong>No messages yet</strong><p class="muted">Start the conversation now.</p></div>';
      return;
    }
    messagesEl.innerHTML = `
      <div class="message-row support">
        <div class="message-bubble">
          <strong>Support Team</strong>
          <p>No conversation yet. Start with your first message.</p>
        </div>
      </div>`;
  };

  const initPanel = (panel) => {
    const messagesEndpoint = panel.dataset.messagesEndpoint || '';
    const sendEndpoint = panel.dataset.sendEndpoint || '';
    if (!messagesEndpoint) return;

    const mode = (panel.dataset.threadMode || 'support').trim().toLowerCase();
    const messagesEl = panel.querySelector('[data-thread-messages]');
    const statusEl = panel.querySelector('[data-thread-status]');
    const syncEl = panel.querySelector('[data-thread-sync]');
    const formEl = panel.querySelector('[data-thread-form]');
    const submitBtn = formEl ? formEl.querySelector('[data-thread-submit]') : null;
    const textInput = formEl ? formEl.querySelector('textarea[name="message_body"]') : null;
    const attachmentInput = formEl ? formEl.querySelector('input[name="attachment"]') : null;

    let isFetching = false;
    let viewerRole = '';

    const refreshMessages = async () => {
      if (isFetching) return;
      isFetching = true;
      try {
        const response = await fetch(`${messagesEndpoint}?mark_read=1`, { credentials: 'same-origin' });
        const payload = await response.json();
        if (!response.ok || !payload.success) {
          updateLiveBadge(statusEl, 'Retrying', 'warning');
          return;
        }

        viewerRole = payload.viewer_role || viewerRole;
        const messages = Array.isArray(payload.messages) ? payload.messages : [];
        if (!messages.length) {
          renderEmptyState(messagesEl, mode);
        } else if (messagesEl) {
          const nearBottom = messagesEl.scrollHeight - messagesEl.scrollTop - messagesEl.clientHeight < 120;
          messagesEl.innerHTML = messages
            .map((item) => renderMessageItem(item, viewerRole, mode))
            .join('');
          if (nearBottom) {
            messagesEl.scrollTop = messagesEl.scrollHeight;
          }
        }

        if (syncEl) {
          syncEl.textContent = `Last sync: ${payload.generated_at || '--'}`;
        }
        updateLiveBadge(statusEl, 'Live', 'success');
      } catch (error) {
        updateLiveBadge(statusEl, 'Retrying', 'warning');
      } finally {
        isFetching = false;
      }
    };

    if (formEl && sendEndpoint) {
      formEl.addEventListener('submit', async (event) => {
        event.preventDefault();
        const formData = new FormData(formEl);
        const messageText = (textInput?.value || '').trim();
        const hasAttachment = Boolean(attachmentInput && attachmentInput.files && attachmentInput.files.length);
        if (!messageText && !hasAttachment) {
          return;
        }

        if (submitBtn) submitBtn.disabled = true;
        updateLiveBadge(statusEl, 'Sending...', 'info');
        try {
          const response = await fetch(sendEndpoint, {
            method: 'POST',
            credentials: 'same-origin',
            headers: {
              'X-CSRFToken': getCookie('csrftoken'),
            },
            body: formData,
          });
          const payload = await response.json();
          if (!response.ok || !payload.success) {
            updateLiveBadge(statusEl, payload.error || 'Send failed', 'danger');
            return;
          }
          if (textInput) textInput.value = '';
          if (attachmentInput) attachmentInput.value = '';
          await refreshMessages();
        } catch (error) {
          updateLiveBadge(statusEl, 'Send failed', 'danger');
        } finally {
          if (submitBtn) submitBtn.disabled = false;
        }
      });
    }

    refreshMessages();
    setInterval(() => {
      if (document.hidden) return;
      refreshMessages();
    }, 6000);
  };

  threadPanels.forEach(initPanel);
})();
