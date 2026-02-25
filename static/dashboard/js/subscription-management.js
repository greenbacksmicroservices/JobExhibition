(() => {
  const exportBtn = document.getElementById('exportBtn');
  const planFilter = document.getElementById('planFilter');
  const expiryFilter = document.getElementById('expiryFilter');
  const subscriptionSearch = document.getElementById('subscriptionSearch');
  const freePaidTable = document.getElementById('freePaidTable');
  const expiryTable = document.getElementById('expiryTable');
  const revenueTable = document.getElementById('revenueTable');
  const revenueBars = document.getElementById('revenueBars');
  const subscriptionTableBody = document.getElementById('subscriptionTableBody');
  const paidRatio = document.getElementById('paidRatio');
  const assignAccount = document.getElementById('assignAccount');
  const assignPlan = document.getElementById('assignPlan');
  const assignStart = document.getElementById('assignStart');
  const assignExpiry = document.getElementById('assignExpiry');
  const assignPayment = document.getElementById('assignPayment');
  const assignAutoRenew = document.getElementById('assignAutoRenew');
  const manualPlanForm = document.getElementById('manualPlanForm');
  const assignmentLog = document.getElementById('assignmentLog');
  const loadingOverlay = document.getElementById('loadingOverlay');
  const toastContainer = document.getElementById('toastContainer');
  const addSubscriptionBtn = document.getElementById('addSubscriptionBtn');
  const subscriptionFormModalEl = document.getElementById('subscriptionFormModal');
  const subscriptionViewModalEl = document.getElementById('subscriptionViewModal');
  const subscriptionDeleteModalEl = document.getElementById('subscriptionDeleteModal');
  const subscriptionForm = document.getElementById('subscriptionForm');
  const subscriptionIdInput = document.getElementById('subscriptionId');
  const subscriptionFormTitle = document.getElementById('subscriptionFormTitle');
  const subscriptionViewContent = document.getElementById('subscriptionViewContent');
  const confirmSubscriptionDelete = document.getElementById('confirmSubscriptionDelete');
  const addonTable = document.getElementById('addonTable');
  const addonViewModalEl = document.getElementById('addonViewModal');
  const addonEditModalEl = document.getElementById('addonEditModal');
  const addonDeleteModalEl = document.getElementById('addonDeleteModal');
  const addonViewContent = document.getElementById('addonViewContent');
  const addonEditForm = document.getElementById('addonEditForm');
  const addonNameInput = document.getElementById('addonNameInput');
  const addonPriceInput = document.getElementById('addonPriceInput');
  const confirmAddonDelete = document.getElementById('confirmAddonDelete');

  const subscriptionFormModal = subscriptionFormModalEl ? new bootstrap.Modal(subscriptionFormModalEl) : null;
  const subscriptionViewModal = subscriptionViewModalEl ? new bootstrap.Modal(subscriptionViewModalEl) : null;
  const subscriptionDeleteModal = subscriptionDeleteModalEl ? new bootstrap.Modal(subscriptionDeleteModalEl) : null;
  const addonViewModal = addonViewModalEl ? new bootstrap.Modal(addonViewModalEl) : null;
  const addonEditModal = addonEditModalEl ? new bootstrap.Modal(addonEditModalEl) : null;
  const addonDeleteModal = addonDeleteModalEl ? new bootstrap.Modal(addonDeleteModalEl) : null;

  const totalAccountsEl = document.getElementById('totalAccounts');
  const paidAccountsEl = document.getElementById('paidAccounts');
  const freeAccountsEl = document.getElementById('freeAccounts');
  const expiringSoonEl = document.getElementById('expiringSoon');

  const pollInterval = 20000;

  let subscriptions = [];
  let logs = [];
  let plans = [];
  let deleteSubscriptionId = null;
  let activeAddonRow = null;

  const revenueSeries = [];

  const setLoading = (show) => {
    if (!loadingOverlay) return;
    loadingOverlay.classList.toggle('active', show);
  };

  const showToast = (message, type = 'success') => {
    if (!toastContainer) return;
    const toast = document.createElement('div');
    toast.className = `toast-message ${type}`;
    toast.textContent = message;
    toastContainer.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
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
        data = { error: 'Server error. Please check server logs.' };
      }
      if (!response.ok) {
        data.error = data.error || 'Server error. Please check server logs.';
      }
      return data;
    } catch (error) {
      return { error: 'Network error. Please check connection.' };
    }
  };

  const daysUntil = (dateStr) => {
    if (!dateStr) return 0;
    const today = new Date();
    const target = new Date(dateStr);
    const diff = target.getTime() - today.getTime();
    return Math.ceil(diff / (1000 * 60 * 60 * 24));
  };

  const statusBadge = (sub) => {
    const days = daysUntil(sub.expiry_date);
    if (days < 0) return 'danger';
    if (days <= 30) return 'warning';
    return 'success';
  };

  const formatNumber = (value) => {
    const number = Number(value || 0);
    return Number.isNaN(number) ? '0' : number.toLocaleString();
  };

  const computeLocalStats = () => {
    const total = subscriptions.length;
    const paid = subscriptions.filter((item) => item.plan !== 'Free').length;
    const free = subscriptions.filter((item) => item.plan === 'Free').length;
    const expiring = subscriptions.filter((item) => daysUntil(item.expiry_date) <= 30).length;
    return { total, paid, free, expiring };
  };

  const updateStats = (stats) => {
    const resolved = stats || computeLocalStats();
    if (totalAccountsEl) totalAccountsEl.textContent = formatNumber(resolved.total);
    if (paidAccountsEl) paidAccountsEl.textContent = formatNumber(resolved.paid);
    if (freeAccountsEl) freeAccountsEl.textContent = formatNumber(resolved.free);
    if (expiringSoonEl) expiringSoonEl.textContent = formatNumber(resolved.expiring);

    if (paidRatio) {
      const percent = resolved.total ? Math.round((resolved.paid / resolved.total) * 100) : 0;
      paidRatio.textContent = `${percent}%`;
    }
  };

  const getFilteredSubscriptions = () => {
    let filtered = [...subscriptions];
    if (planFilter && planFilter.value !== 'all') {
      filtered = filtered.filter((item) => item.plan === planFilter.value);
    }
    filtered.sort((a, b) => a.name.localeCompare(b.name));
    return filtered;
  };

  const getFilteredPlans = () => {
    let filtered = [...plans];
    const keyword = subscriptionSearch ? subscriptionSearch.value.trim().toLowerCase() : '';
    if (keyword) {
      filtered = filtered.filter(
        (item) =>
          (item.name || '').toLowerCase().includes(keyword) ||
          (item.plan_code || '').toLowerCase().includes(keyword),
      );
    }
    filtered.sort((a, b) => (a.name || '').localeCompare(b.name || ''));
    return filtered;
  };

  const renderFreePaidTable = () => {
    if (!freePaidTable) return;
    const rows = getFilteredSubscriptions();
    if (!rows.length) {
      freePaidTable.innerHTML = '<tr><td colspan="7" class="text-center text-muted py-4">No accounts found.</td></tr>';
      return;
    }
    freePaidTable.innerHTML = rows
      .map((sub) => {
        const badge = statusBadge(sub);
        return `
<tr>
  <td>${sub.name}</td>
  <td>${sub.account_type}</td>
  <td><span class="badge ${sub.plan === 'Free' ? 'neutral' : 'info'}">${sub.plan}</span></td>
  <td>${sub.payment_status}</td>
  <td>${sub.start_date}</td>
  <td>${sub.expiry_date}</td>
  <td><span class="badge ${badge}">${badge === 'danger' ? 'Expired' : badge === 'warning' ? 'Expiring' : 'Active'}</span></td>
</tr>`;
      })
      .join('');
  };

  const renderSubscriptionTable = () => {
    if (!subscriptionTableBody) return;
    const rows = getFilteredPlans();
    if (!rows.length) {
      subscriptionTableBody.innerHTML =
        '<tr><td colspan="20" class="text-center text-muted py-4">No plans found.</td></tr>';
      return;
    }
    subscriptionTableBody.innerHTML = rows
      .map((plan) => `
<tr>
  <td>${plan.name}</td>
  <td>${plan.plan_code}</td>
  <td>INR ${formatNumber(plan.price_monthly)}</td>
  <td>INR ${formatNumber(plan.price_quarterly)}</td>
  <td>${plan.job_posts || '-'}</td>
  <td>${plan.job_validity || '-'}</td>
  <td>${plan.resume_view || '-'}</td>
  <td>${plan.resume_download || '-'}</td>
  <td>${plan.candidate_chat || '-'}</td>
  <td>${plan.interview_scheduler || '-'}</td>
  <td>${plan.auto_match || '-'}</td>
  <td>${plan.shortlisting || '-'}</td>
  <td>${plan.candidate_ranking || '-'}</td>
  <td>${plan.candidate_pool_manager || '-'}</td>
  <td>${plan.featured_jobs || '-'}</td>
  <td>${plan.company_branding || '-'}</td>
  <td>${plan.analytics_dashboard || '-'}</td>
  <td>${plan.support || '-'}</td>
  <td>${plan.dedicated_account_manager || '-'}</td>
  <td>
    <div class="table-actions">
      <button class="action-btn" data-sub-action="view" data-id="${plan.id}"><i class="fa-solid fa-eye"></i> View</button>
      <button class="action-btn" data-sub-action="edit" data-id="${plan.id}"><i class="fa-solid fa-pen"></i> Edit</button>
      <button class="action-btn danger" data-sub-action="delete" data-id="${plan.id}"><i class="fa-solid fa-trash"></i> Delete</button>
    </div>
  </td>
</tr>`)
      .join('');
  };

  const bindSubscriptionTable = () => {
    if (!subscriptionTableBody || subscriptionTableBody.dataset.bound) return;
    subscriptionTableBody.dataset.bound = 'true';
    subscriptionTableBody.addEventListener('click', (event) => {
      const button = event.target.closest('[data-sub-action]');
      if (!button) return;
      const action = button.dataset.subAction;
      const id = button.dataset.id;
      if (action === 'view') {
        openSubscriptionView(id);
      }
      if (action === 'edit') {
        openSubscriptionForm(id);
      }
      if (action === 'delete') {
        deleteSubscriptionId = id;
        if (subscriptionDeleteModal) subscriptionDeleteModal.show();
      }
    });
  };

  const renderExpiryTable = () => {
    if (!expiryTable) return;
    const limit = expiryFilter ? Number(expiryFilter.value) : 30;
    const rows = subscriptions
      .map((sub) => ({ ...sub, daysLeft: daysUntil(sub.expiry_date) }))
      .filter((sub) => sub.daysLeft <= limit)
      .sort((a, b) => a.daysLeft - b.daysLeft);

    if (!rows.length) {
      expiryTable.innerHTML = '<tr><td colspan="6" class="text-center text-muted py-4">No expiry alerts.</td></tr>';
      return;
    }

    expiryTable.innerHTML = rows
      .map((sub) => `
<tr>
  <td>${sub.name}</td>
  <td>${sub.plan}</td>
  <td>${sub.expiry_date}</td>
  <td>${sub.daysLeft} days</td>
  <td>${sub.contact}</td>
  <td>
    <div class="table-actions">
      <button class="action-btn" data-action="notify" data-id="${sub.id}">Notify</button>
      <button class="action-btn" data-action="extend" data-id="${sub.id}">Extend</button>
    </div>
  </td>
</tr>`)
      .join('');
  };

  const renderRevenue = () => {
    if (revenueBars) {
      if (!revenueSeries.length) {
        revenueBars.innerHTML = '<p class="muted">No revenue data yet.</p>';
      } else {
        const maxValue = Math.max(...revenueSeries.map((row) => row.free + row.basic + row.standard + row.gold));
        revenueBars.innerHTML = revenueSeries
          .map((row) => {
            const total = row.free + row.basic + row.standard + row.gold;
            const width = maxValue ? Math.round((total / maxValue) * 100) : 0;
            return `
<div class="bar-row">
  <span>${row.month}</span>
  <div class="bar-track"><span style="width: ${width}%"></span></div>
  <strong>INR ${total}</strong>
</div>`;
          })
          .join('');
      }
    }

    if (revenueTable) {
      if (!revenueSeries.length) {
        revenueTable.innerHTML = '<tr><td colspan="6" class="text-center text-muted py-4">No revenue data yet.</td></tr>';
      } else {
        revenueTable.innerHTML = revenueSeries
          .map((row) => {
            const total = row.free + row.basic + row.standard + row.gold;
            return `
<tr>
  <td>${row.month} 2026</td>
  <td>INR ${row.free}</td>
  <td>INR ${row.basic}</td>
  <td>INR ${row.standard}</td>
  <td>INR ${row.gold}</td>
  <td><strong>INR ${total}</strong></td>
</tr>`;
          })
          .join('');
      }
    }
  };

  const renderLogs = () => {
    if (!assignmentLog) return;
    if (!logs.length) {
      assignmentLog.innerHTML = '<tr><td colspan="5" class="text-center text-muted py-4">No manual assignments yet.</td></tr>';
      return;
    }
    assignmentLog.innerHTML = logs
      .map((log) => `
<tr>
  <td>${log.account}</td>
  <td>${log.old_plan}</td>
  <td>${log.new_plan}</td>
  <td>${log.admin}</td>
  <td>${log.date}</td>
</tr>`)
      .join('');
  };

  const populateAssignSelect = () => {
    if (!assignAccount) return;
    assignAccount.innerHTML = subscriptions
      .slice()
      .sort((a, b) => a.name.localeCompare(b.name))
      .map((sub) => `<option value="${sub.id}">${sub.name} (${sub.account_type})</option>`)
      .join('');
  };

  const openSubscriptionForm = (id = null) => {
    if (!subscriptionForm) return;
    subscriptionForm.reset();
    if (subscriptionIdInput) subscriptionIdInput.value = '';
    if (subscriptionFormTitle) subscriptionFormTitle.textContent = 'Add Subscription Plan';

    if (id) {
      const plan = plans.find((item) => String(item.id) === String(id));
      if (!plan) return;
      if (subscriptionIdInput) subscriptionIdInput.value = plan.id;
      if (subscriptionFormTitle) subscriptionFormTitle.textContent = `Edit ${plan.name}`;
      const fields = [
        'name',
        'plan_code',
        'price_monthly',
        'price_quarterly',
        'job_posts',
        'job_validity',
        'resume_view',
        'resume_download',
        'candidate_chat',
        'interview_scheduler',
        'auto_match',
        'shortlisting',
        'candidate_ranking',
        'candidate_pool_manager',
        'featured_jobs',
        'company_branding',
        'analytics_dashboard',
        'support',
        'dedicated_account_manager',
      ];
      fields.forEach((field) => {
        const input = subscriptionForm.querySelector(`[name="${field}"]`);
        if (input) {
          input.value = plan[field] ?? '';
        }
      });
    }

    if (subscriptionFormModal) subscriptionFormModal.show();
  };

  const openSubscriptionView = (id) => {
    if (!subscriptionViewContent) return;
    const plan = plans.find((item) => String(item.id) === String(id));
    if (!plan) return;
    subscriptionViewContent.innerHTML = `
<div class="details-card">
  <h6>Subscription Plan</h6>
  <div class="details-list">
    <div><span>Plan:</span> ${plan.name}</div>
    <div><span>Code:</span> ${plan.plan_code}</div>
    <div><span>Monthly Price:</span> INR ${formatNumber(plan.price_monthly)}</div>
    <div><span>Quarterly Price:</span> INR ${formatNumber(plan.price_quarterly)}</div>
    <div><span>Job Posts:</span> ${plan.job_posts || '-'}</div>
    <div><span>Job Validity:</span> ${plan.job_validity || '-'}</div>
    <div><span>Resume View:</span> ${plan.resume_view || '-'}</div>
    <div><span>Resume Download:</span> ${plan.resume_download || '-'}</div>
    <div><span>Candidate Chat:</span> ${plan.candidate_chat || '-'}</div>
    <div><span>Interview Scheduler:</span> ${plan.interview_scheduler || '-'}</div>
    <div><span>Auto Match:</span> ${plan.auto_match || '-'}</div>
    <div><span>Shortlisting:</span> ${plan.shortlisting || '-'}</div>
    <div><span>Candidate Ranking:</span> ${plan.candidate_ranking || '-'}</div>
    <div><span>Candidate Pool Manager:</span> ${plan.candidate_pool_manager || '-'}</div>
    <div><span>Featured Jobs:</span> ${plan.featured_jobs || '-'}</div>
    <div><span>Company Branding:</span> ${plan.company_branding || '-'}</div>
    <div><span>Analytics Dashboard:</span> ${plan.analytics_dashboard || '-'}</div>
    <div><span>Support:</span> ${plan.support || '-'}</div>
    <div><span>Dedicated Account Manager:</span> ${plan.dedicated_account_manager || '-'}</div>
  </div>
</div>`;
    if (subscriptionViewModal) subscriptionViewModal.show();
  };

  const buildListParams = () => {
    const params = new URLSearchParams();
    if (planFilter && planFilter.value !== 'all') {
      params.set('plan', planFilter.value);
    }
    return params;
  };

  const toFormData = (payload) => {
    const formData = new FormData();
    Object.entries(payload).forEach(([key, value]) => {
      if (key === 'id') return;
      if (key === 'auto_renew') {
        if (value) formData.append('auto_renew', 'true');
        return;
      }
      formData.append(key, value ?? '');
    });
    return formData;
  };

  const updateSubscription = async (payload) => {
    const formData = toFormData(payload);
    const data = await fetchJson(`/api/subscriptions/${encodeURIComponent(payload.id)}/update/`, {
      method: 'POST',
      headers: { 'X-CSRFToken': getCookie('csrftoken') },
      body: formData,
    });
    if (data && data.success) {
      await refreshData(true);
      return true;
    }
    showToast(data.error || 'Failed to update subscription', 'danger');
    return false;
  };

  const extendSubscription = async (id, months = 3) => {
    const formData = new FormData();
    formData.append('months', String(months));
    const data = await fetchJson(`/api/subscriptions/${encodeURIComponent(id)}/extend/`, {
      method: 'POST',
      headers: { 'X-CSRFToken': getCookie('csrftoken') },
      body: formData,
    });
    if (data && data.success) {
      await refreshData(true);
      return true;
    }
    showToast(data.error || 'Failed to extend subscription', 'danger');
    return false;
  };

  const deleteSubscription = async (id) => {
    const data = await fetchJson(`/api/plans/${encodeURIComponent(id)}/delete/`, {
      method: 'POST',
      headers: { 'X-CSRFToken': getCookie('csrftoken') },
    });
    if (data && data.success) {
      showToast('Plan deleted', 'success');
      await refreshPlans();
      return true;
    }
    showToast(data.error || 'Failed to delete plan', 'danger');
    return false;
  };

  const handleSubscriptionSubmit = async (event) => {
    event.preventDefault();
    if (!subscriptionForm) return;
    const formData = new FormData(subscriptionForm);
    const id = subscriptionIdInput ? subscriptionIdInput.value : '';
    const url = id
      ? `/api/plans/${encodeURIComponent(id)}/update/`
      : '/api/plans/create/';
    setLoading(true);
    const data = await fetchJson(url, {
      method: 'POST',
      headers: { 'X-CSRFToken': getCookie('csrftoken') },
      body: formData,
    });
    setLoading(false);
    if (data && data.success) {
      showToast(id ? 'Plan updated' : 'Plan created', 'success');
      subscriptionForm.reset();
      if (subscriptionIdInput) subscriptionIdInput.value = '';
      if (subscriptionFormModal) subscriptionFormModal.hide();
      await refreshPlans();
    } else {
      showToast(data.error || 'Failed to save plan', 'danger');
    }
  };

  const handleExpiryActions = () => {
    if (!expiryTable) return;
    const buttons = expiryTable.querySelectorAll('[data-action]');
    buttons.forEach((btn) => {
      btn.addEventListener('click', async () => {
        const action = btn.dataset.action;
        const id = btn.dataset.id;
        const sub = subscriptions.find((item) => item.id === id);
        if (!sub) return;
        if (action === 'notify') {
          showToast(`Reminder sent to ${sub.name}`, 'success');
        }
        if (action === 'extend') {
          const success = await extendSubscription(id, 3);
          if (success) {
            renderExpiryTable();
            renderFreePaidTable();
            updateStats();
            showToast('Expiry extended by 3 months', 'success');
          }
        }
      });
    });
  };

  const refreshData = async (silent = false) => {
    if (!silent) setLoading(true);
    const params = buildListParams();
    const data = await fetchJson(`/api/subscriptions/list/?${params.toString()}`);
    if (data.error) {
      showToast(data.error, 'danger');
      subscriptions = [];
      logs = [];
      updateStats({ total: 0, paid: 0, free: 0, expiring: 0 });
      renderFreePaidTable();
      renderExpiryTable();
      renderLogs();
      populateAssignSelect();
      if (!silent) setLoading(false);
      return false;
    }
    subscriptions = Array.isArray(data.results) ? data.results : [];
    logs = Array.isArray(data.logs) ? data.logs : [];
    updateStats(data.stats);
    renderFreePaidTable();
    renderExpiryTable();
    renderLogs();
    populateAssignSelect();
    handleExpiryActions();
    if (!silent) setLoading(false);
    return true;
  };

  const refreshPlans = async () => {
    if (!subscriptionTableBody) return false;
    const data = await fetchJson('/api/plans/list/');
    if (data.error) {
      showToast(data.error, 'danger');
      plans = [];
      renderSubscriptionTable();
      return false;
    }
    plans = Array.isArray(data.results) ? data.results : [];
    renderSubscriptionTable();
    return true;
  };

  if (manualPlanForm) {
    manualPlanForm.addEventListener('submit', async (event) => {
      event.preventDefault();
      if (!assignAccount || !assignPlan || !assignStart || !assignExpiry) {
        return;
      }
      const selectedId = assignAccount.value;
      const sub = subscriptions.find((item) => item.id === selectedId);
      if (!sub) {
        showToast('Account not found', 'danger');
        return;
      }

      const payload = {
        ...sub,
        id: sub.id,
        plan: assignPlan.value,
        start_date: assignStart.value,
        expiry_date: assignExpiry.value,
        payment_status: assignPlan.value === 'Free' ? 'Free' : assignPayment ? assignPayment.value : sub.payment_status,
        auto_renew: Boolean(assignAutoRenew && assignAutoRenew.checked),
      };

      const saved = await updateSubscription(payload);
      if (saved) {
        renderFreePaidTable();
        renderExpiryTable();
        renderLogs();
        updateStats();
        showToast('Plan assigned successfully', 'success');
        manualPlanForm.reset();
        populateAssignSelect();
      }
    });
  }

  if (planFilter) {
    planFilter.addEventListener('change', () => {
      refreshData();
    });
  }

  if (expiryFilter) {
    expiryFilter.addEventListener('change', () => {
      renderExpiryTable();
      handleExpiryActions();
    });
  }

  if (subscriptionSearch) {
    let timer;
    subscriptionSearch.addEventListener('input', () => {
      clearTimeout(timer);
      timer = setTimeout(() => renderSubscriptionTable(), 300);
    });
  }

  if (exportBtn) {
    exportBtn.addEventListener('click', () => {
      const header = ['Account', 'Type', 'Plan', 'Payment Status', 'Start Date', 'Expiry Date'];
      const rows = getFilteredSubscriptions().map((sub) => [
        sub.name,
        sub.account_type,
        sub.plan,
        sub.payment_status,
        sub.start_date,
        sub.expiry_date,
      ]);
      const csv = [header.join(',')]
        .concat(rows.map((row) => row.map((val) => `"${String(val).replace(/"/g, '""')}"`).join(',')))
        .join('\n');
      const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = 'subscriptions.csv';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    });
  }

  if (subscriptionForm) {
    subscriptionForm.addEventListener('submit', handleSubscriptionSubmit);
  }

  if (addSubscriptionBtn) {
    addSubscriptionBtn.addEventListener('click', () => openSubscriptionForm());
  }

  if (confirmSubscriptionDelete) {
    confirmSubscriptionDelete.addEventListener('click', async () => {
      if (!deleteSubscriptionId) return;
      const success = await deleteSubscription(deleteSubscriptionId);
      if (success && subscriptionDeleteModal) subscriptionDeleteModal.hide();
      deleteSubscriptionId = null;
    });
  }

  const getAddonRowData = (row) => {
    if (!row) return { name: '', price: '' };
    const cells = row.querySelectorAll('td');
    return {
      name: cells[0] ? cells[0].textContent.trim() : '',
      price: cells[1] ? cells[1].textContent.trim() : '',
    };
  };

  if (addonTable) {
    addonTable.addEventListener('click', (event) => {
      const button = event.target.closest('[data-addon-action]');
      if (!button) return;
      const row = button.closest('tr');
      if (!row) return;
      activeAddonRow = row;
      const data = getAddonRowData(row);
      const action = button.dataset.addonAction;
      if (action === 'view' && addonViewContent) {
        addonViewContent.innerHTML = `
<div class="details-card">
  <h6>Add-on</h6>
  <div class="details-list">
    <div><span>Name:</span> ${data.name || '-'}</div>
    <div><span>Price:</span> ${data.price || '-'}</div>
  </div>
</div>`;
        if (addonViewModal) addonViewModal.show();
      }
      if (action === 'edit') {
        if (addonNameInput) addonNameInput.value = data.name || '';
        if (addonPriceInput) addonPriceInput.value = data.price || '';
        if (addonEditModal) addonEditModal.show();
      }
      if (action === 'delete') {
        if (addonDeleteModal) addonDeleteModal.show();
      }
    });
  }

  if (addonEditForm) {
    addonEditForm.addEventListener('submit', (event) => {
      event.preventDefault();
      if (!activeAddonRow) return;
      const name = addonNameInput ? addonNameInput.value.trim() : '';
      const price = addonPriceInput ? addonPriceInput.value.trim() : '';
      const cells = activeAddonRow.querySelectorAll('td');
      if (cells[0] && name) cells[0].textContent = name;
      if (cells[1] && price) cells[1].textContent = price;
      if (addonEditModal) addonEditModal.hide();
      showToast('Add-on updated', 'success');
    });
  }

  if (confirmAddonDelete) {
    confirmAddonDelete.addEventListener('click', () => {
      if (activeAddonRow) {
        activeAddonRow.remove();
        showToast('Add-on deleted', 'success');
      }
      activeAddonRow = null;
      if (addonDeleteModal) addonDeleteModal.hide();
    });
  }

  bindSubscriptionTable();

  renderRevenue();
  refreshPlans();
  refreshData();

  setInterval(() => {
    if (document.hidden) return;
    refreshData(true);
    refreshPlans();
  }, pollInterval);
})();
