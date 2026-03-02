(() => {
  const body = document.body;
  const userType = body.dataset.userType;
  const userSingular = body.dataset.userSingular || (userType ? userType.slice(0, -1) : '');
  const hasKyc =
    body.dataset.hasKyc === 'true' || (body.dataset.hasKyc === undefined && userType !== 'candidates');
  const hasResume = body.dataset.hasResume === 'true';
  const profileName = (
    document.querySelector('.profile-meta strong')?.textContent ||
    document.querySelector('.company-user-meta strong')?.textContent ||
    ''
  )
    .trim()
    .toLowerCase();
  const isSubadmin = profileName === 'subadmin' || body.dataset.panelRole === 'subadmin';
  const canDelete = body.dataset.canDelete === 'true' || (body.dataset.canDelete !== 'false' && !isSubadmin);
  if (!userType) {
    return;
  }

  const hasSubscription = body.dataset.hasSubscription === 'true';
  const tableBody = document.getElementById('tableBody');
  const paginationEl = document.getElementById('pagination');
  const searchInput = document.getElementById('searchInput');
  const filterKyc = document.getElementById('filterKyc');
  const filterStatus = document.getElementById('filterStatus');
  const filterPlan = document.getElementById('filterPlan');
  const applyFilters = document.getElementById('applyFilters');
  const selectAll = document.getElementById('selectAll');
  const bulkDeleteBtn = document.getElementById('bulkDeleteBtn');
  const exportCsvBtn = document.getElementById('exportCsvBtn');
  const addNewBtn = document.getElementById('addNewBtn');
  const loadingOverlay = document.getElementById('loadingOverlay');
  const toastContainer = document.getElementById('toastContainer');
  const darkToggle = document.getElementById('darkModeToggle');
  const requestsBody = document.getElementById('requestsBody');

  const formModalEl = document.getElementById('userFormModal');
  const viewModalEl = document.getElementById('viewModal');
  const deleteModalEl = document.getElementById('deleteModal');

  const modalOptions = { backdrop: false, keyboard: true };
  const formModal = formModalEl ? new bootstrap.Modal(formModalEl, modalOptions) : null;
  const viewModal = viewModalEl ? new bootstrap.Modal(viewModalEl, modalOptions) : null;
  const deleteModal = deleteModalEl ? new bootstrap.Modal(deleteModalEl, modalOptions) : null;

  const userForm = document.getElementById('userForm');
  const formTitle = document.getElementById('formTitle');
  const userIdInput = document.getElementById('userId');
  const confirmDeleteBtn = document.getElementById('confirmDeleteBtn');
  const viewContent = document.getElementById('viewContent');

  let currentPage = 1;
  let totalPages = 1;
  let deleteIds = [];

  if (!canDelete) {
    if (bulkDeleteBtn) {
      bulkDeleteBtn.style.display = 'none';
      bulkDeleteBtn.disabled = true;
    }
    if (confirmDeleteBtn) {
      confirmDeleteBtn.style.display = 'none';
      confirmDeleteBtn.disabled = true;
    }
    if (selectAll) {
      selectAll.checked = false;
      selectAll.disabled = true;
    }
  }

  const statusClass = (value) => {
    if (!value) return 'neutral';
    const val = value.toLowerCase();
    if (val === 'active' || val === 'verified' || val === 'paid') return 'success';
    if (val === 'available') return 'success';
    if (val === 'suspended' || val === 'pending' || val === 'due') return 'warning';
    if (val === 'missing') return 'warning';
    if (val === 'blocked' || val === 'rejected' || val === 'failed') return 'danger';
    return 'neutral';
  };

  const showLoading = (show) => {
    if (!loadingOverlay) return;
    loadingOverlay.classList.toggle('active', show);
  };

  const showToast = (message, type = 'success') => {
    if (!toastContainer) return;
    const toast = document.createElement('div');
    toast.className = `toast-message ${type}`;
    toast.textContent = message;
    toastContainer.appendChild(toast);
    setTimeout(() => {
      toast.remove();
    }, 3000);
  };

  const getCookie = (name) => {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
    return '';
  };

  const fetchJson = async (url, options = {}) => {
    try {
      const response = await fetch(url, options);
      const text = await response.text();
      let data = {};
      try {
        data = text ? JSON.parse(text) : {};
      } catch (error) {
        data = { success: false, error: 'Server error. Please check server logs.' };
      }
      if (!response.ok && !data.error) {
        data.error = 'Server error. Please check server logs.';
      }
      return data;
    } catch (error) {
      return { success: false, error: 'Network error. Please check connection.' };
    }
  };

  const fetchList = async (page = 1) => {
    try {
      showLoading(true);
      const params = new URLSearchParams();
      params.set('page', String(page));
      params.set('page_size', '10');
      params.set('search', searchInput ? searchInput.value.trim() : '');
      params.set('kyc', filterKyc ? filterKyc.value : 'all');
      params.set('status', filterStatus ? filterStatus.value : 'all');
      if (hasSubscription && filterPlan) {
        params.set('plan', filterPlan.value);
      }

      const data = await fetchJson(`/api/user-management/${userType}/list/?${params.toString()}`);
      if (data.error) {
        showToast(data.error, 'danger');
      }
      currentPage = data.page || 1;
      totalPages = data.pages || 1;
      renderTable(data.results || []);
      renderPagination();
    } finally {
      showLoading(false);
    }
  };

  const renderTable = (rows) => {
    if (!tableBody) return;
    if (!rows.length) {
      tableBody.innerHTML = '<tr><td colspan="11" class="text-center">No records found</td></tr>';
      if (bulkDeleteBtn) bulkDeleteBtn.disabled = true;
      if (selectAll) selectAll.checked = false;
      return;
    }

    if (selectAll) selectAll.checked = false;
    tableBody.innerHTML = rows
      .map((row) => {
        const kycBadge = statusClass(row.kyc_status);
        const resumeLabel = row.resume_status || 'Missing';
        const resumeBadge = statusClass(resumeLabel);
        const accountBadge = statusClass(row.account_status);
        const plan = row.subscription_plan || 'N/A';
        const checked = row.account_status === 'Active' ? 'checked' : '';
        const disabled = row.account_status === 'Blocked' ? 'disabled' : '';
        const verificationCell = hasResume
          ? `<td><span class="badge ${resumeBadge}">${resumeLabel}</span></td>`
          : `<td><span class="badge ${kycBadge}">${row.kyc_status || 'Pending'}</span></td>`;
        const selectCell = canDelete
          ? `<td><input type="checkbox" class="row-check" data-id="${row.id}" /></td>`
          : '<td></td>';
        const deleteButton = canDelete
          ? `<button class="action-btn danger" data-action="delete" data-id="${row.id}"><i class="fa-solid fa-trash"></i> Delete</button>`
          : '';
        return `
<tr>
  ${selectCell}
  <td>#${row.id}</td>
  <td>${row.name || '-'}</td>
  <td>${row.email || '-'}</td>
  <td>${row.phone || '-'}</td>
  <td>${row.location || '-'}</td>
  ${verificationCell}
  <td>
    <div class="status-toggle">
      <span class="badge ${accountBadge}">${row.account_status || 'Active'}</span>
      <label class="switch">
        <input type="checkbox" class="status-switch" data-id="${row.id}" ${checked} ${disabled} />
        <span class="slider"></span>
      </label>
    </div>
  </td>
  <td>${plan}</td>
  <td>${row.registered_date || '-'}</td>
  <td>
    <div class="table-actions">
      <button class="action-btn" data-action="view" data-id="${row.id}"><i class="fa-solid fa-eye"></i> View</button>
      <button class="action-btn" data-action="edit" data-id="${row.id}"><i class="fa-solid fa-pen"></i> Edit</button>
      ${deleteButton}
    </div>
  </td>
</tr>`;
      })
      .join('');

    bindRowEvents();
  };

  const renderPagination = () => {
    if (!paginationEl) return;
    paginationEl.innerHTML = '';
    if (totalPages <= 1) return;

    const createButton = (label, page, disabled = false, active = false) => {
      const btn = document.createElement('button');
      btn.className = `page-btn${active ? ' active' : ''}`;
      btn.textContent = label;
      btn.disabled = disabled;
      btn.addEventListener('click', () => fetchList(page));
      paginationEl.appendChild(btn);
    };

    createButton('Prev', Math.max(1, currentPage - 1), currentPage === 1);
    for (let i = 1; i <= totalPages; i += 1) {
      createButton(String(i), i, false, i === currentPage);
    }
    createButton('Next', Math.min(totalPages, currentPage + 1), currentPage === totalPages);
  };

  const renderRequestsTable = (rows) => {
    if (!requestsBody) return;
    const isConsultancy = userType === 'consultancies';
    const emptyColspan = isConsultancy ? 9 : 8;
    if (!rows.length) {
      requestsBody.innerHTML = `<tr><td colspan="${emptyColspan}" class="text-center">No pending requests</td></tr>`;
      return;
    }
    requestsBody.innerHTML = rows
      .map((row) => {
        const kycBadge = statusClass(row.kyc_status);
        const docStatus = row.document_status || 'Missing';
        const docBadge = statusClass(docStatus === 'Uploaded' ? 'verified' : 'pending');
        const statusLabel = row.kyc_status === 'Verified' ? 'Approved' : (row.kyc_status || 'Pending');
        const detailsCols = isConsultancy
          ? `
  <td>${row.owner_name || '-'}</td>
  <td>${row.phone || '-'}</td>
  <td>${row.email || '-'}</td>
  <td><span class="badge ${docBadge}">${docStatus}</span></td>`
          : `
  <td>${row.email || '-'}</td>
  <td>${row.phone || '-'}</td>
  <td>${row.location || '-'}</td>`;
        const deleteButton = canDelete
          ? `<button class="action-btn danger" data-action="delete" data-id="${row.id}"><i class="fa-solid fa-trash"></i> Delete</button>`
          : '';
        return `
<tr>
  <td>#${row.id}</td>
  <td>${row.name || '-'}</td>
  ${detailsCols}
  <td>${row.registered_date || '-'}</td>
  <td><span class="badge ${kycBadge}">${statusLabel}</span></td>
  <td>
    <div class="table-actions">
      <button class="action-btn" data-action="view" data-id="${row.id}"><i class="fa-solid fa-eye"></i> Details</button>
      <button class="action-btn" data-action="edit" data-id="${row.id}"><i class="fa-solid fa-pen"></i> Edit</button>
      ${deleteButton}
      <button class="action-btn" data-action="accept" data-id="${row.id}"><i class="fa-solid fa-check"></i> Accept</button>
      <button class="action-btn danger" data-action="reject" data-id="${row.id}"><i class="fa-solid fa-xmark"></i> Reject</button>
    </div>
  </td>
</tr>`;
      })
      .join('');

    bindRowEvents();
  };

  const fetchRequests = async () => {
    if (!requestsBody || !hasKyc) return;
    const params = new URLSearchParams();
    params.set('page', '1');
    params.set('page_size', '50');
    params.set('kyc', 'Pending');
    const data = await fetchJson(`/api/user-management/${userType}/list/?${params.toString()}`);
    if (data.error) {
      showToast(data.error, 'danger');
      return;
    }
    renderRequestsTable(data.results || []);
  };

  const bindRowEvents = () => {
    const rowChecks = document.querySelectorAll('.row-check');
    rowChecks.forEach((check) => {
      if (check.dataset.bound) return;
      check.dataset.bound = 'true';
      check.addEventListener('change', () => {
        const anyChecked = Array.from(rowChecks).some((item) => item.checked);
        if (bulkDeleteBtn) bulkDeleteBtn.disabled = !anyChecked;
      });
    });

    const actionButtons = document.querySelectorAll('[data-action]');
    actionButtons.forEach((btn) => {
      if (btn.dataset.bound) return;
      btn.dataset.bound = 'true';
      btn.addEventListener('click', async () => {
        const action = btn.dataset.action;
        const id = btn.dataset.id;
        if (action === 'view') {
          await openViewModal(id);
        }
        if (action === 'edit') {
          await openEditModal(id);
        }
        if (action === 'delete') {
          if (!canDelete) {
            showToast('Delete action is disabled for subadmin.', 'warning');
            return;
          }
          deleteIds = [id];
          if (deleteModal) deleteModal.show();
        }
        if (action === 'accept' || action === 'reject') {
          const newStatus = action === 'accept' ? 'Verified' : 'Rejected';
          await updateKyc(id, newStatus);
        }
      });
    });

    const statusSwitches = document.querySelectorAll('.status-switch');
    statusSwitches.forEach((toggle) => {
      if (toggle.dataset.bound) return;
      toggle.dataset.bound = 'true';
      toggle.addEventListener('change', async () => {
        const id = toggle.dataset.id;
        const newStatus = toggle.checked ? 'Active' : 'Suspended';
        await updateStatus(id, newStatus);
      });
    });
  };

  const openEditModal = async (id) => {
    const data = await fetchDetail(id);
    if (!data || !userForm) return;
    userIdInput.value = data.id;
      formTitle.textContent = `Edit ${data.name || ''}`;
    fillForm(data);
    if (formModal) formModal.show();
  };

  const openViewModal = async (id) => {
    const data = await fetchDetail(id, true);
    if (!data || !viewContent) return;
    viewContent.innerHTML = buildViewHtml(data);
    if (viewModal) viewModal.show();
  };

  const fetchDetail = async (id, withExtras = false) => {
    showLoading(true);
    const data = await fetchJson(`/api/user-management/${userType}/${id}/detail/`);
    showLoading(false);
    return withExtras ? data : data.item;
  };

  const fillForm = (data) => {
    const fields = ['name', 'email', 'phone', 'password', 'location', 'address', 'account_type', 'profile_completion',
      'kyc_status', 'account_status', 'warning_count', 'suspension_reason', 'gst_number', 'cin_number', 'license_number',
      'date_of_birth', 'plan_name', 'plan_type', 'plan_start', 'plan_expiry', 'payment_status'];
    fields.forEach((field) => {
      const input = userForm.querySelector(`[name="${field}"]`);
      if (input && data[field] !== undefined && data[field] !== null) {
        input.value = data[field];
      }
    });

    const autoRenew = userForm.querySelector('[name="auto_renew"]');
    if (autoRenew) {
      autoRenew.checked = Boolean(data.auto_renew);
    }
  };

  const buildViewHtml = (data) => {
    const item = data.item || {};
    const documents = data.documents || [];
    const kycHistory = data.kyc_history || [];
    const statusHistory = data.status_history || [];
    const jobs = data.jobs || [];
    const selections = data.selections || [];
    const payments = data.payments || [];
    const complaints = data.complaints || [];
    const logins = data.logins || [];
    const resumeDoc = documents.find((doc) => (doc.label || '').toLowerCase() === 'resume');
    const resumeStatus = resumeDoc && resumeDoc.url ? 'Available' : item.resume_status || 'Missing';
    const escapeHtml = (value) => String(value)
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;')
      .replaceAll("'", '&#39;');
    const viewValue = (value, fallback = '-') => {
      if (value === undefined || value === null) return fallback;
      const text = String(value).trim();
      return text ? escapeHtml(text) : fallback;
    };

    const listRows = (rows, columns) => {
      return rows.map((row) => {
        return `<tr>${columns.map((col) => `<td>${viewValue(row[col])}</td>`).join('')}</tr>`;
      }).join('');
    };

    const listDocs = (rows) => {
      if (!rows.length) return '<div class="muted">No documents uploaded</div>';
      return rows.map((row) => {
        const label = viewValue(row.label, 'Document');
        const name = viewValue(row.value, 'Document');
        const link = row.url ? `<a href="${row.url}" target="_blank" rel="noopener">View</a>` : '';
        return `<div><span>${label}:</span> ${name} ${link}</div>`;
      }).join('');
    };

    const profileCompletion = Number(item.profile_completion || 0);
    const profileCard = `
  <div class="details-card">
    <h6>Profile</h6>
    <div class="details-list">
      <div><span>Name:</span> ${viewValue(item.name)}</div>
      <div><span>Email:</span> ${viewValue(item.email)}</div>
      <div><span>Phone:</span> ${viewValue(item.phone)}</div>
      <div><span>Location:</span> ${viewValue(item.location)}</div>
      <div><span>Account Type:</span> ${viewValue(item.account_type)}</div>
      <div><span>Registered:</span> ${viewValue(item.registered_date)}</div>
      <div><span>Profile Completion:</span> ${profileCompletion}%</div>
    </div>
  </div>`;

    const verificationCard = hasKyc
      ? `
  <div class="details-card">
    <h6>Verification</h6>
    <div class="details-list">
      <div><span>KYC Status:</span> ${viewValue(item.kyc_status, 'Pending')}</div>
      <div><span>Account Status:</span> ${viewValue(item.account_status, 'Active')}</div>
      <div><span>Warning Count:</span> ${viewValue(item.warning_count, '0')}</div>
      <div><span>Suspension Reason:</span> ${viewValue(item.suspension_reason, 'N/A')}</div>
    </div>
  </div>`
      : `
  <div class="details-card">
    <h6>Account Status</h6>
    <div class="details-list">
      <div><span>Status:</span> ${viewValue(item.account_status, 'Active')}</div>
      <div><span>Warning Count:</span> ${viewValue(item.warning_count, '0')}</div>
      <div><span>Suspension Reason:</span> ${viewValue(item.suspension_reason, 'N/A')}</div>
      ${hasResume ? `<div><span>Resume:</span> ${viewValue(resumeStatus)}</div>` : ''}
    </div>
  </div>`;

    const subscriptionCard = hasSubscription
      ? `
  <div class="details-card">
    <h6>Subscription</h6>
    <div class="details-list">
      <div><span>Plan:</span> ${viewValue(item.plan_name, 'N/A')}</div>
      <div><span>Plan Type:</span> ${viewValue(item.plan_type, 'N/A')}</div>
      <div><span>Payment:</span> ${viewValue(item.payment_status, 'N/A')}</div>
      <div><span>Start:</span> ${viewValue(item.plan_start, 'N/A')}</div>
      <div><span>Expiry:</span> ${viewValue(item.plan_expiry, 'N/A')}</div>
      <div><span>Auto Renew:</span> ${item.auto_renew ? 'Yes' : 'No'}</div>
    </div>
  </div>`
      : '';

    const typeSpecificCard = userType === 'companies'
      ? `
  <div class="details-card">
    <h6>Company Compliance</h6>
    <div class="details-list">
      <div><span>GST Number:</span> ${viewValue(item.gst_number, 'N/A')}</div>
      <div><span>CIN Number:</span> ${viewValue(item.cin_number, 'N/A')}</div>
      <div><span>Contact Position:</span> ${viewValue(item.contact_position, 'N/A')}</div>
    </div>
  </div>`
      : userType === 'consultancies'
        ? `
  <div class="details-card">
    <h6>Consultancy Profile</h6>
    <div class="details-list">
      <div><span>License Number:</span> ${viewValue(item.license_number, 'N/A')}</div>
      <div><span>Owner Name:</span> ${viewValue(item.owner_name, 'N/A')}</div>
      <div><span>Owner Phone:</span> ${viewValue(item.owner_phone, 'N/A')}</div>
      <div><span>Owner Email:</span> ${viewValue(item.owner_email, 'N/A')}</div>
      <div><span>Consultancy Type:</span> ${viewValue(item.consultancy_type, 'N/A')}</div>
      <div><span>Industries Served:</span> ${viewValue(item.industries_served, 'N/A')}</div>
    </div>
  </div>`
        : `
  <div class="details-card">
    <h6>Candidate Profile</h6>
    <div class="details-list">
      <div><span>Date of Birth:</span> ${viewValue(item.date_of_birth, 'N/A')}</div>
      <div><span>Resume Status:</span> ${viewValue(resumeStatus)}</div>
      <div><span>Address:</span> ${viewValue(item.address, 'N/A')}</div>
    </div>
  </div>`;

    const resumeActions = hasResume
      ? `
<h6>Resume</h6>
<div class="details-card" style="margin-bottom:16px;">
  <div class="view-actions">
    ${
      resumeDoc && resumeDoc.url
        ? `<a class="btn ghost" href="${resumeDoc.url}" target="_blank" rel="noopener">View Resume</a>
           <a class="btn primary" href="${resumeDoc.url}" download>Download Resume</a>`
        : '<span class="muted">No resume uploaded</span>'
    }
  </div>
</div>`
      : '';

    const kycSection = hasKyc
      ? `
<div class="details-grid">
  <div class="details-card">
    <h6>KYC History</h6>
    <div class="table-wrap">
      <table class="table">
        <thead><tr><th>Date</th><th>Status</th><th>Admin</th></tr></thead>
        <tbody>${listRows(kycHistory, ['date', 'status', 'admin']) || '<tr><td colspan="3">No data</td></tr>'}</tbody>
      </table>
    </div>
  </div>
  <div class="details-card">
    <h6>Account Status History</h6>
    <div class="table-wrap">
      <table class="table">
        <thead><tr><th>Date</th><th>Status</th><th>Note</th></tr></thead>
        <tbody>${listRows(statusHistory, ['date', 'status', 'note']) || '<tr><td colspan="3">No data</td></tr>'}</tbody>
      </table>
    </div>
  </div>
</div>`
      : `
<div class="details-card" style="margin-bottom:16px;">
  <h6>Account Status History</h6>
  <div class="table-wrap">
    <table class="table">
      <thead><tr><th>Date</th><th>Status</th><th>Note</th></tr></thead>
      <tbody>${listRows(statusHistory, ['date', 'status', 'note']) || '<tr><td colspan="3">No data</td></tr>'}</tbody>
    </table>
  </div>
</div>`;

    const selectionSection = userType === 'candidates'
      ? `
<h6>Selection Details</h6>
<div class="table-wrap" style="margin-bottom:16px;">
  <table class="table">
    <thead><tr><th>Selected By</th><th>Company</th><th>Position</th><th>Salary</th><th>Status</th><th>Date</th></tr></thead>
    <tbody>${listRows(selections, ['selected_by', 'company', 'position', 'salary', 'status', 'date']) || '<tr><td colspan="6">No selections yet.</td></tr>'}</tbody>
  </table>
</div>`
      : '';

    const jobsSection = userType !== 'candidates'
      ? `
<h6>Jobs Posted</h6>
<div class="table-wrap">
  <table class="table">
    <thead><tr><th>Job ID</th><th>Title</th><th>Status</th><th>Applications</th></tr></thead>
    <tbody>${listRows(jobs, ['id', 'title', 'status', 'applications']) || '<tr><td colspan="4">No data</td></tr>'}</tbody>
  </table>
</div>`
      : '';

    return `
<div class="details-grid">
  ${[profileCard, verificationCard, subscriptionCard, typeSpecificCard].filter(Boolean).join('')}
</div>

${resumeActions}

<h6>Uploaded Documents</h6>
<div class="details-card" style="margin-bottom:16px;">
  ${listDocs(documents)}
</div>

${kycSection}

${selectionSection}

${jobsSection}

<h6>Payment History</h6>
<div class="table-wrap">
  <table class="table">
    <thead><tr><th>Invoice</th><th>Date</th><th>Amount</th><th>Status</th></tr></thead>
    <tbody>${listRows(payments, ['invoice', 'date', 'amount', 'status']) || '<tr><td colspan="4">No data</td></tr>'}</tbody>
  </table>
</div>

<h6>Complaints</h6>
<div class="table-wrap">
  <table class="table">
    <thead><tr><th>ID</th><th>Type</th><th>Status</th><th>Date</th></tr></thead>
    <tbody>${listRows(complaints, ['id', 'type', 'status', 'date']) || '<tr><td colspan="4">No data</td></tr>'}</tbody>
  </table>
</div>

<h6>Login Activity</h6>
<div class="table-wrap">
  <table class="table">
    <thead><tr><th>IP</th><th>Device</th><th>Browser</th><th>Time</th></tr></thead>
    <tbody>${listRows(logins, ['ip', 'device', 'browser', 'time']) || '<tr><td colspan="4">No data</td></tr>'}</tbody>
  </table>
</div>
`;
  };

  const updateStatus = async (id, status) => {
    showLoading(true);
    const formData = new FormData();
    formData.append('account_status', status);
    const data = await fetchJson(`/api/user-management/${userType}/${id}/status/`, {
      method: 'POST',
      headers: { 'X-CSRFToken': getCookie('csrftoken') },
      body: formData,
    });
    showLoading(false);
    if (data.success) {
      showToast('Status updated', 'success');
      fetchList(currentPage);
    } else {
      showToast(data.error || 'Failed to update', 'danger');
    }
  };

  const updateKyc = async (id, status) => {
    if (!hasKyc) return;
    showLoading(true);
    const formData = new FormData();
    formData.append('kyc_status', status);
    const data = await fetchJson(`/api/user-management/${userType}/${id}/kyc/`, {
      method: 'POST',
      headers: { 'X-CSRFToken': getCookie('csrftoken') },
      body: formData,
    });
    showLoading(false);
    if (data.success) {
      showToast('KYC status updated', 'success');
      fetchList(currentPage);
      fetchRequests();
    } else {
      showToast(data.error || 'Failed to update', 'danger');
    }
  };

  const handleFormSubmit = async (event) => {
    event.preventDefault();
    const formData = new FormData(userForm);
    const id = formData.get('id');
    const url = id
      ? `/api/user-management/${userType}/${id}/update/`
      : `/api/user-management/${userType}/create/`;

    showLoading(true);
    const data = await fetchJson(url, {
      method: 'POST',
      headers: { 'X-CSRFToken': getCookie('csrftoken') },
      body: formData,
    });
    showLoading(false);

    if (data.success) {
      showToast(id ? 'Updated successfully' : 'Created successfully', 'success');
      userForm.reset();
      userIdInput.value = '';
      formTitle.textContent = `Add ${userSingular || ''}`;
      if (formModal) formModal.hide();
      fetchList(1);
      fetchRequests();
    } else {
      showToast(data.error || 'Something went wrong', 'danger');
    }
  };

  const confirmDelete = async () => {
    if (!canDelete) {
      showToast('Delete action is disabled for subadmin.', 'warning');
      return;
    }
    if (!deleteIds.length) return;
    showLoading(true);
    const data = await fetchJson(`/api/user-management/${userType}/bulk-delete/`, {
      method: 'POST',
      headers: {
        'X-CSRFToken': getCookie('csrftoken'),
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ ids: deleteIds }),
    });
    showLoading(false);
    if (data.success) {
      showToast('Deleted successfully', 'success');
      deleteIds = [];
      if (deleteModal) deleteModal.hide();
      fetchList(1);
      fetchRequests();
    } else {
      showToast(data.error || 'Delete failed', 'danger');
    }
  };

  const resolveThemeScope = () => {
    const scoped = (body.dataset.themeScope || '').trim().toLowerCase();
    if (scoped) return scoped;
    if (body.classList.contains('candidate-dashboard')) return 'candidate';
    if (body.classList.contains('company-dashboard')) return 'company';
    if (body.classList.contains('consultancy-dashboard')) return 'consultancy';
    return 'admin';
  };

  const initDarkMode = () => {
    if (window.__dashboardThemeManaged) {
      return;
    }
    const themeScope = resolveThemeScope();
    const darkStorageKey = `dark-mode-${themeScope}`;
    const updateDarkIcon = () => {
      if (!darkToggle) return;
      const icon = darkToggle.querySelector('i');
      const enabled = body.classList.contains('dark-mode');
      if (icon) {
        icon.classList.toggle('fa-moon', !enabled);
        icon.classList.toggle('fa-sun', enabled);
        return;
      }
      darkToggle.textContent = enabled ? 'Sun' : 'Moon';
    };
    const stored = localStorage.getItem(darkStorageKey);
    const legacy = localStorage.getItem('dark-mode');
    const enabled = stored === 'true' || (stored === null && themeScope === 'admin' && legacy === 'true');
    body.classList.toggle('dark-mode', enabled);
    updateDarkIcon();

    if (darkToggle && !darkToggle.dataset.darkBound) {
      darkToggle.addEventListener('click', () => {
        body.classList.toggle('dark-mode');
        localStorage.setItem(darkStorageKey, body.classList.contains('dark-mode'));
        updateDarkIcon();
      });
      darkToggle.dataset.darkBound = 'true';
    }
  };

  if (!hasSubscription && filterPlan) {
    filterPlan.style.display = 'none';
  }

  if (userForm) {
    userForm.addEventListener('submit', handleFormSubmit);
  }

  if (addNewBtn && userForm) {
    addNewBtn.addEventListener('click', (event) => {
      event.preventDefault();
      userForm.reset();
      if (userIdInput) userIdInput.value = '';
      if (formTitle) formTitle.textContent = `Add ${userSingular || ''}`;
      if (formModal) formModal.show();
    });
  }

  if (applyFilters) {
    applyFilters.addEventListener('click', () => fetchList(1));
  }

  if (searchInput) {
    let timer;
    searchInput.addEventListener('input', () => {
      clearTimeout(timer);
      timer = setTimeout(() => fetchList(1), 400);
    });
  }

  if (selectAll) {
    selectAll.addEventListener('change', () => {
      if (!canDelete) return;
      const checks = document.querySelectorAll('.row-check');
      checks.forEach((check) => {
        check.checked = selectAll.checked;
      });
      if (bulkDeleteBtn) {
        bulkDeleteBtn.disabled = !selectAll.checked;
      }
    });
  }

  if (bulkDeleteBtn) {
    bulkDeleteBtn.addEventListener('click', () => {
      if (!canDelete) {
        showToast('Delete action is disabled for subadmin.', 'warning');
        return;
      }
      const ids = Array.from(document.querySelectorAll('.row-check:checked')).map((el) => el.dataset.id);
      if (!ids.length) {
        showToast('Select at least one row', 'warning');
        return;
      }
      deleteIds = ids;
      if (deleteModal) deleteModal.show();
    });
  }

  if (exportCsvBtn) {
    exportCsvBtn.addEventListener('click', () => {
      const params = new URLSearchParams();
      params.set('search', searchInput ? searchInput.value.trim() : '');
      params.set('kyc', filterKyc ? filterKyc.value : 'all');
      params.set('status', filterStatus ? filterStatus.value : 'all');
      if (hasSubscription && filterPlan) {
        params.set('plan', filterPlan.value);
      }
      window.location.href = `/api/user-management/${userType}/export/?${params.toString()}`;
    });
  }

  if (confirmDeleteBtn) {
    confirmDeleteBtn.addEventListener('click', confirmDelete);
  }

  initDarkMode();
  fetchList(1);
  fetchRequests();
})();
