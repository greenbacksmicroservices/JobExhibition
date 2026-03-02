(() => {
  const shell = document.querySelector('.subadmin-management-shell');
  if (!shell) {
    return;
  }

  const canManage = shell.dataset.canManage === 'true';
  const tableBody = document.getElementById('subadminTableBody');
  const paginationEl = document.getElementById('subadminPagination');
  const searchInput = document.getElementById('subadminSearch');
  const roleFilter = document.getElementById('subadminRoleFilter');
  const statusFilter = document.getElementById('subadminStatusFilter');
  const applyFiltersBtn = document.getElementById('subadminApplyFilters');

  const form = document.getElementById('subadminForm');
  const idInput = document.getElementById('subadminId');
  const nameInput = document.getElementById('subadminName');
  const usernameInput = document.getElementById('subadminUsername');
  const emailInput = document.getElementById('subadminEmail');
  const phoneInput = document.getElementById('subadminPhone');
  const roleInput = document.getElementById('subadminRole');
  const statusInput = document.getElementById('subadminStatus');
  const passwordInput = document.getElementById('subadminPassword');
  const saveBtn = document.getElementById('subadminSaveBtn');
  const resetBtn = document.getElementById('subadminResetBtn');
  const addBtn = document.getElementById('subadminAddBtn');

  const loadingOverlay = document.getElementById('loadingOverlay');
  const toastContainer = document.getElementById('toastContainer');

  const viewModalEl = document.getElementById('subadminViewModal');
  const deleteModalEl = document.getElementById('subadminDeleteModal');
  const viewContent = document.getElementById('subadminViewContent');
  const deleteConfirmBtn = document.getElementById('subadminDeleteConfirmBtn');

  const viewModal = viewModalEl ? new bootstrap.Modal(viewModalEl, { backdrop: false, keyboard: true }) : null;
  const deleteModal = deleteModalEl ? new bootstrap.Modal(deleteModalEl, { backdrop: false, keyboard: true }) : null;

  let currentPage = 1;
  let totalPages = 1;
  let pendingDeleteId = null;

  const setLoading = (isVisible) => {
    if (!loadingOverlay) {
      return;
    }
    loadingOverlay.classList.toggle('active', !!isVisible);
  };

  const showToast = (message, type = 'success') => {
    if (!toastContainer) {
      return;
    }
    const toast = document.createElement('div');
    toast.className = `toast-message ${type}`;
    toast.textContent = message;
    toastContainer.appendChild(toast);
    setTimeout(() => {
      toast.remove();
    }, 3200);
  };

  const getCookie = (name) => {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) {
      return parts.pop().split(';').shift();
    }
    return '';
  };

  const csrfToken = () => {
    return (
      document.querySelector('#subadminForm input[name="csrfmiddlewaretoken"]')?.value ||
      getCookie('csrftoken')
    );
  };

  const fetchJson = async (url, options = {}) => {
    try {
      const response = await fetch(url, options);
      const text = await response.text();
      let payload = {};
      try {
        payload = text ? JSON.parse(text) : {};
      } catch (error) {
        payload = { success: false, error: 'Invalid server response.' };
      }
      if (!response.ok && !payload.error) {
        payload.error = 'Request failed.';
      }
      return payload;
    } catch (error) {
      return { success: false, error: 'Network error. Please retry.' };
    }
  };

  const escapeHtml = (value) => {
    return String(value ?? '')
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;')
      .replaceAll("'", '&#39;');
  };

  const statusBadgeClass = (status) => {
    if ((status || '').toLowerCase() === 'active') {
      return 'success';
    }
    return 'warning';
  };

  const resetForm = () => {
    if (!form) {
      return;
    }
    form.reset();
    if (idInput) {
      idInput.value = '';
    }
    if (statusInput) {
      statusInput.value = 'Active';
    }
    if (roleInput) {
      roleInput.value = roleInput.querySelector('option')?.value || 'Sub Admin';
    }
    if (saveBtn) {
      saveBtn.textContent = 'Save Sub-Admin';
    }
  };

  const fillForm = (item) => {
    if (!item) {
      return;
    }
    if (idInput) idInput.value = item.id || '';
    if (nameInput) nameInput.value = item.name || '';
    if (usernameInput) usernameInput.value = item.username || '';
    if (emailInput) emailInput.value = item.email || '';
    if (phoneInput) phoneInput.value = item.phone || '';
    if (roleInput) roleInput.value = item.role || 'Sub Admin';
    if (statusInput) statusInput.value = item.account_status || 'Active';
    if (passwordInput) passwordInput.value = '';
    if (saveBtn) saveBtn.textContent = 'Update Sub-Admin';
    shell.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  const renderPagination = () => {
    if (!paginationEl) {
      return;
    }
    paginationEl.innerHTML = '';
    if (totalPages <= 1) {
      return;
    }

    const addPageBtn = (label, page, disabled = false, isActive = false) => {
      const btn = document.createElement('button');
      btn.className = `page-btn${isActive ? ' active' : ''}`;
      btn.textContent = label;
      btn.disabled = disabled;
      btn.addEventListener('click', () => fetchList(page));
      paginationEl.appendChild(btn);
    };

    addPageBtn('Prev', Math.max(currentPage - 1, 1), currentPage === 1);
    for (let i = 1; i <= totalPages; i += 1) {
      addPageBtn(String(i), i, false, i === currentPage);
    }
    addPageBtn('Next', Math.min(currentPage + 1, totalPages), currentPage === totalPages);
  };

  const renderRows = (rows) => {
    if (!tableBody) {
      return;
    }

    if (!rows.length) {
      tableBody.innerHTML = '<tr><td colspan="9" class="text-center">No sub-admin records found.</td></tr>';
      return;
    }

    tableBody.innerHTML = rows
      .map((row) => {
        const statusClass = statusBadgeClass(row.account_status);
        const disabledAttr = canManage ? '' : 'disabled';
        return `
<tr>
  <td>#${escapeHtml(row.id)}</td>
  <td>${escapeHtml(row.username || '-')}</td>
  <td>${escapeHtml(row.name || '-')}</td>
  <td>${escapeHtml(row.email || '-')}</td>
  <td>${escapeHtml(row.phone || '-')}</td>
  <td>${escapeHtml(row.role || 'Sub Admin')}</td>
  <td>${escapeHtml(row.last_login || '-')}</td>
  <td><span class="badge ${statusClass}">${escapeHtml(row.account_status || 'Active')}</span></td>
  <td>
    <div class="table-actions">
      <button class="action-btn" data-action="view" data-id="${row.id}"><i class="fa-solid fa-eye"></i> View</button>
      <button class="action-btn" data-action="edit" data-id="${row.id}" ${disabledAttr}><i class="fa-solid fa-pen"></i> Edit</button>
      <button class="action-btn danger" data-action="delete" data-id="${row.id}" ${disabledAttr}><i class="fa-solid fa-trash"></i> Delete</button>
    </div>
  </td>
</tr>`;
      })
      .join('');

    bindActionEvents();
  };

  const fetchList = async (page = 1) => {
    const params = new URLSearchParams();
    params.set('page', String(page));
    params.set('page_size', '10');
    params.set('search', searchInput ? searchInput.value.trim() : '');
    params.set('role', roleFilter ? roleFilter.value : 'all');
    params.set('status', statusFilter ? statusFilter.value : 'all');

    setLoading(true);
    const payload = await fetchJson(`/api/subadmins/list/?${params.toString()}`);
    setLoading(false);

    if (!payload.success) {
      showToast(payload.error || 'Unable to load sub-admin records.', 'danger');
      return;
    }

    currentPage = payload.page || 1;
    totalPages = payload.pages || 1;
    renderRows(payload.results || []);
    renderPagination();
  };

  const fetchDetail = async (id) => {
    setLoading(true);
    const payload = await fetchJson(`/api/subadmins/${id}/detail/`);
    setLoading(false);
    if (!payload.success) {
      showToast(payload.error || 'Unable to fetch details.', 'danger');
      return null;
    }
    return payload.item || null;
  };

  const renderView = (item) => {
    if (!viewContent || !item) {
      return;
    }

    viewContent.innerHTML = `
<div class="details-grid">
  <div class="details-card">
    <h6>Identity</h6>
    <div class="details-list">
      <div><span>ID:</span> #${escapeHtml(item.id)}</div>
      <div><span>Name:</span> ${escapeHtml(item.name || '-')}</div>
      <div><span>Username:</span> ${escapeHtml(item.username || '-')}</div>
      <div><span>Email:</span> ${escapeHtml(item.email || '-')}</div>
      <div><span>Phone:</span> ${escapeHtml(item.phone || '-')}</div>
    </div>
  </div>
  <div class="details-card">
    <h6>Access</h6>
    <div class="details-list">
      <div><span>Role:</span> ${escapeHtml(item.role || 'Sub Admin')}</div>
      <div><span>Status:</span> ${escapeHtml(item.account_status || 'Active')}</div>
      <div><span>Last Active:</span> ${escapeHtml(item.last_login || '-')}</div>
      <div><span>Created:</span> ${escapeHtml(item.created_at || '-')}</div>
    </div>
  </div>
</div>`;
  };

  const openView = async (id) => {
    const item = await fetchDetail(id);
    if (!item) {
      return;
    }
    renderView(item);
    if (viewModal) {
      viewModal.show();
    }
  };

  const openEdit = async (id) => {
    if (!canManage) {
      showToast('Edit action is disabled for this account.', 'warning');
      return;
    }
    const item = await fetchDetail(id);
    if (!item) {
      return;
    }
    fillForm(item);
  };

  const openDelete = (id) => {
    if (!canManage) {
      showToast('Delete action is disabled for this account.', 'warning');
      return;
    }
    pendingDeleteId = id;
    if (deleteModal) {
      deleteModal.show();
    }
  };

  const bindActionEvents = () => {
    const buttons = document.querySelectorAll('#subadminTableBody [data-action]');
    buttons.forEach((button) => {
      if (button.dataset.bound) {
        return;
      }
      button.dataset.bound = 'true';
      button.addEventListener('click', () => {
        const action = button.dataset.action;
        const id = button.dataset.id;
        if (!id) {
          return;
        }
        if (action === 'view') {
          openView(id);
          return;
        }
        if (action === 'edit') {
          openEdit(id);
          return;
        }
        if (action === 'delete') {
          openDelete(id);
        }
      });
    });
  };

  const submitForm = async (event) => {
    event.preventDefault();

    if (!nameInput?.value.trim() || !usernameInput?.value.trim()) {
      showToast('Name and username are required.', 'warning');
      return;
    }

    const isUpdate = Boolean(idInput?.value);
    if (!isUpdate && !(passwordInput?.value || '').trim()) {
      showToast('Password is required for new sub-admin.', 'warning');
      return;
    }

    if (!canManage) {
      showToast('This account has read-only access.', 'warning');
      return;
    }

    const formData = new FormData();
    formData.append('name', nameInput.value.trim());
    formData.append('username', usernameInput.value.trim());
    formData.append('email', emailInput?.value.trim() || '');
    formData.append('phone', phoneInput?.value.trim() || '');
    formData.append('role', roleInput?.value || 'Sub Admin');
    formData.append('account_status', statusInput?.value || 'Active');
    formData.append('password', passwordInput?.value || '');

    const endpoint = isUpdate
      ? `/api/subadmins/${idInput.value}/update/`
      : '/api/subadmins/create/';

    setLoading(true);
    const payload = await fetchJson(endpoint, {
      method: 'POST',
      headers: {
        'X-CSRFToken': csrfToken(),
      },
      body: formData,
    });
    setLoading(false);

    if (!payload.success) {
      showToast(payload.error || 'Unable to save sub-admin.', 'danger');
      return;
    }

    showToast(isUpdate ? 'Sub-admin updated successfully.' : 'Sub-admin created successfully.', 'success');
    resetForm();
    fetchList(isUpdate ? currentPage : 1);
  };

  const confirmDelete = async () => {
    if (!pendingDeleteId) {
      return;
    }
    if (!canManage) {
      showToast('This account cannot delete records.', 'warning');
      return;
    }

    setLoading(true);
    const payload = await fetchJson(`/api/subadmins/${pendingDeleteId}/delete/`, {
      method: 'POST',
      headers: {
        'X-CSRFToken': csrfToken(),
      },
    });
    setLoading(false);

    if (!payload.success) {
      showToast(payload.error || 'Delete failed.', 'danger');
      return;
    }

    showToast('Sub-admin deleted successfully.', 'success');
    pendingDeleteId = null;
    if (deleteModal) {
      deleteModal.hide();
    }
    fetchList(1);
    resetForm();
  };

  if (form) {
    form.addEventListener('submit', submitForm);
  }

  if (resetBtn) {
    resetBtn.addEventListener('click', () => {
      resetForm();
    });
  }

  if (addBtn) {
    addBtn.addEventListener('click', () => {
      resetForm();
      nameInput?.focus();
    });
  }

  if (applyFiltersBtn) {
    applyFiltersBtn.addEventListener('click', () => fetchList(1));
  }

  if (searchInput) {
    let searchTimer;
    searchInput.addEventListener('input', () => {
      clearTimeout(searchTimer);
      searchTimer = setTimeout(() => fetchList(1), 300);
    });
  }

  if (deleteConfirmBtn) {
    deleteConfirmBtn.addEventListener('click', confirmDelete);
  }

  if (!canManage) {
    if (saveBtn) saveBtn.disabled = true;
    if (addBtn) addBtn.disabled = true;
  }

  resetForm();
  fetchList(1);
})();
