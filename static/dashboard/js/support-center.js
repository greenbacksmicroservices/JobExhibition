(() => {
  if (!document.body.classList.contains('support-center')) {
    return;
  }

  const toastContainer = document.getElementById('toastContainer');
  const liveStatusEl = document.getElementById('supportLiveStatus');
  const lastSyncEl = document.getElementById('supportLastSync');

  const showToast = (message, type = 'success') => {
    if (!toastContainer) return;
    const toast = document.createElement('div');
    toast.className = `toast-message ${type}`;
    toast.textContent = message;
    toastContainer.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
  };

  const normalizeAction = (text) => (text || '').trim().toLowerCase();
  const nowLabel = () =>
    new Date().toLocaleString('en-IN', {
      year: 'numeric',
      month: 'short',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
    });

  const refreshLiveStamp = () => {
    if (liveStatusEl) {
      liveStatusEl.textContent = 'Realtime Active';
      liveStatusEl.classList.remove('warning', 'danger');
      liveStatusEl.classList.add('success');
    }
    if (lastSyncEl) {
      lastSyncEl.textContent = `Last Sync: ${nowLabel()}`;
    }
  };

  refreshLiveStamp();
  setInterval(() => {
    if (document.hidden) return;
    refreshLiveStamp();
  }, 7000);

  const findCellByHeader = (row, label) => {
    if (!row) return null;
    const table = row.closest('table');
    if (!table) return null;
    const headers = Array.from(table.querySelectorAll('thead th'));
    const targetIndex = headers.findIndex((th) => normalizeAction(th.textContent) === normalizeAction(label));
    if (targetIndex < 0) return null;
    const cells = row.querySelectorAll('td');
    return cells[targetIndex] || null;
  };

  const getTicketLabel = (row) => {
    const firstCell = row ? row.querySelector('td') : null;
    return firstCell ? firstCell.textContent.trim() : 'Ticket';
  };

  const addInternalNote = (row) => {
    const statusCell = findCellByHeader(row, 'Status');
    if (!statusCell) return;
    if (statusCell.dataset.noted === 'true') {
      showToast('Internal note already added.', 'warning');
      return;
    }
    statusCell.dataset.noted = 'true';
    statusCell.insertAdjacentHTML('beforeend', ' <span class="badge neutral">Noted</span>');
    showToast(`${getTicketLabel(row)} noted successfully.`, 'success');
  };

  const handleAssign = (row) => {
    const assignCell = findCellByHeader(row, 'Assigned') || findCellByHeader(row, 'Assign');
    if (!assignCell) {
      showToast('Assignment column not found for this row.', 'warning');
      return;
    }
    const select = assignCell.querySelector('select');
    if (select) {
      const nextAgent = Array.from(select.options).find((option) => option.value && !/assign/i.test(option.value));
      if (!nextAgent) {
        showToast('No agents available to assign.', 'warning');
        return;
      }
      select.value = nextAgent.value;
      assignCell.dataset.assigned = 'true';
      showToast(`${getTicketLabel(row)} assigned to ${nextAgent.value}.`, 'success');
      return;
    }
    assignCell.textContent = 'Priya';
    showToast(`${getTicketLabel(row)} assigned to Priya.`, 'success');
  };

  const handleView = (row) => {
    const ticket = getTicketLabel(row);
    const companyCell = findCellByHeader(row, 'Company');
    const statusCell = findCellByHeader(row, 'Status');
    const company = companyCell ? companyCell.textContent.trim() : 'Unknown Company';
    const status = statusCell ? statusCell.textContent.trim() : 'Unknown Status';
    showToast(`${ticket} | ${company} | ${status}`, 'info');
  };

  const handleMerge = (row) => {
    const tbody = row ? row.closest('tbody') : null;
    if (!tbody || tbody.querySelectorAll('tr').length <= 1) {
      showToast('No duplicate ticket available to merge.', 'warning');
      return;
    }
    row.remove();
    showToast('Duplicate ticket merged.', 'success');
  };

  document.querySelectorAll('.table-actions .action-btn').forEach((button) => {
    button.addEventListener('click', (event) => {
      event.preventDefault();
      const row = button.closest('tr');
      const action = normalizeAction(button.textContent);
      if (!row) return;
      if (action.includes('assign')) {
        handleAssign(row);
        return;
      }
      if (action.includes('view')) {
        handleView(row);
        return;
      }
      if (action.includes('merge')) {
        handleMerge(row);
        return;
      }
      if (action.includes('note')) {
        addInternalNote(row);
        return;
      }
      showToast('Action completed.', 'success');
    });
  });

  document.querySelectorAll('.support-center table select').forEach((select) => {
    select.addEventListener('change', () => {
      if (!select.value || /assign/i.test(select.value)) return;
      const row = select.closest('tr');
      showToast(`${getTicketLabel(row)} assigned to ${select.value}.`, 'success');
    });
  });

  document.querySelectorAll('.support-center a[href="#"]').forEach((link) => {
    link.addEventListener('click', (event) => {
      event.preventDefault();
      showToast('This module will be enabled in next update.', 'info');
    });
  });

  const searchInput = document.querySelector('[data-support-search]');
  if (searchInput) {
    const ticketRows = Array.from(document.querySelectorAll('.support-table tbody tr'));
    searchInput.addEventListener('input', () => {
      const query = (searchInput.value || '').trim().toLowerCase();
      ticketRows.forEach((row) => {
        const text = (row.innerText || row.textContent || '').toLowerCase();
        const visible = !query || text.includes(query);
        row.style.display = visible ? '' : 'none';
      });
    });
  }
})();
