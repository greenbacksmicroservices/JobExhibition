(() => {
  const body = document.body;
  const profileName = (
    document.querySelector('.profile-meta strong')?.textContent ||
    document.querySelector('.company-user-meta strong')?.textContent ||
    ''
  )
    .trim()
    .toLowerCase();
  const isSubadmin = profileName === 'subadmin' || body.dataset.panelRole === 'subadmin';
  const canDelete = body.dataset.canDelete === 'true' || (body.dataset.canDelete !== 'false' && !isSubadmin);
  const exportBtn = document.getElementById('exportBtn');
  const planFilter = document.getElementById('planFilter');
  const expiryFilter = document.getElementById('expiryFilter');
  const subscriptionSearch = document.getElementById('subscriptionSearch');
  const freePaidTable = document.getElementById('freePaidTable');
  const freePaidEntriesSelect = document.getElementById('freePaidEntriesSelect');
  const freePaidEntriesInfo = document.getElementById('freePaidEntriesInfo');
  const freePaidPrevBtn = document.getElementById('freePaidPrevBtn');
  const freePaidNextBtn = document.getElementById('freePaidNextBtn');
  const expiryTable = document.getElementById('expiryTable');
  const revenueTable = document.getElementById('revenueTable');
  const revenueBars = document.getElementById('revenueBars');
  const downloadReportBtn = document.getElementById('downloadReportBtn');
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
  const billingDetailsModalEl = document.getElementById('billingDetailsModal');
  const subscriptionForm = document.getElementById('subscriptionForm');
  const subscriptionIdInput = document.getElementById('subscriptionId');
  const subscriptionFormTitle = document.getElementById('subscriptionFormTitle');
  const subscriptionViewContent = document.getElementById('subscriptionViewContent');
  const confirmSubscriptionDelete = document.getElementById('confirmSubscriptionDelete');
  const billingSummaryGrid = document.getElementById('billingSummaryGrid');
  const billingHistoryModalBody = document.getElementById('billingHistoryModalBody');
  const addonTable = document.getElementById('addonTable');
  const addonViewModalEl = document.getElementById('addonViewModal');
  const addonEditModalEl = document.getElementById('addonEditModal');
  const addonDeleteModalEl = document.getElementById('addonDeleteModal');
  const addonViewContent = document.getElementById('addonViewContent');
  const addonEditForm = document.getElementById('addonEditForm');
  const addonNameInput = document.getElementById('addonNameInput');
  const addonPriceInput = document.getElementById('addonPriceInput');
  const confirmAddonDelete = document.getElementById('confirmAddonDelete');

  const BootstrapModal = window.bootstrap && window.bootstrap.Modal ? window.bootstrap.Modal : null;
  const modalOptions = { backdrop: false, keyboard: true };
  const subscriptionFormModal = BootstrapModal && subscriptionFormModalEl ? new BootstrapModal(subscriptionFormModalEl, modalOptions) : null;
  const subscriptionViewModal = BootstrapModal && subscriptionViewModalEl ? new BootstrapModal(subscriptionViewModalEl, modalOptions) : null;
  const subscriptionDeleteModal = BootstrapModal && subscriptionDeleteModalEl ? new BootstrapModal(subscriptionDeleteModalEl, modalOptions) : null;
  const billingDetailsModal = BootstrapModal && billingDetailsModalEl ? new BootstrapModal(billingDetailsModalEl, modalOptions) : null;
  const addonViewModal = BootstrapModal && addonViewModalEl ? new BootstrapModal(addonViewModalEl, modalOptions) : null;
  const addonEditModal = BootstrapModal && addonEditModalEl ? new BootstrapModal(addonEditModalEl, modalOptions) : null;
  const addonDeleteModal = BootstrapModal && addonDeleteModalEl ? new BootstrapModal(addonDeleteModalEl, modalOptions) : null;

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
  let freePaidPage = 1;
  let freePaidPageSize = Number(freePaidEntriesSelect ? freePaidEntriesSelect.value : 10) || 10;

  const revenueSeries = [];

  if (!canDelete) {
    if (confirmSubscriptionDelete) {
      confirmSubscriptionDelete.style.display = 'none';
      confirmSubscriptionDelete.disabled = true;
    }
    if (confirmAddonDelete) {
      confirmAddonDelete.style.display = 'none';
      confirmAddonDelete.disabled = true;
    }
    document.querySelectorAll('[data-addon-action="delete"]').forEach((button) => {
      button.style.display = 'none';
      button.disabled = true;
    });
  }

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

  const escapeHtml = (value) =>
    String(value ?? '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');

  const safeText = (value, fallback = '-') => {
    const normalized = String(value ?? '').trim();
    return normalized ? escapeHtml(normalized) : fallback;
  };

  const toSortText = (value) => String(value ?? '').toLowerCase();

  const daysUntil = (dateStr) => {
    if (!dateStr) return null;
    const today = new Date();
    const target = new Date(dateStr);
    if (Number.isNaN(target.getTime())) return null;
    const diff = target.getTime() - today.getTime();
    return Math.ceil(diff / (1000 * 60 * 60 * 24));
  };

  const statusBadge = (sub) => {
    const days = daysUntil(sub.expiry_date);
    if (days === null) return 'neutral';
    if (days < 0) return 'danger';
    if (days <= 30) return 'warning';
    return 'success';
  };

  const formatNumber = (value) => {
    const number = Number(value || 0);
    return Number.isNaN(number) ? '0' : number.toLocaleString();
  };

  const formatCurrency = (amount, currency = 'INR') => {
    const value = Number(amount || 0);
    const printable = Number.isNaN(value) ? '0' : value.toLocaleString();
    return `${safeText(currency)} ${printable}`;
  };

  const normalizeLabel = (value) => {
    const normalized = String(value || '').trim();
    if (!normalized) return '-';
    return normalized.charAt(0).toUpperCase() + normalized.slice(1);
  };

  const extractDateParts = (rawValue) => {
    if (!rawValue) {
      return {
        full: '-',
        date: '-',
        time: '-',
        month: '-',
        year: '-',
      };
    }
    const parsed = new Date(rawValue);
    if (Number.isNaN(parsed.getTime())) {
      const safe = safeText(rawValue);
      return {
        full: safe,
        date: safe,
        time: '-',
        month: '-',
        year: '-',
      };
    }
    return {
      full: parsed.toLocaleString(),
      date: parsed.toLocaleDateString(),
      time: parsed.toLocaleTimeString(),
      month: parsed.toLocaleString(undefined, { month: 'long' }),
      year: String(parsed.getFullYear()),
    };
  };

  const computeLocalStats = () => {
    const total = subscriptions.length;
    const paid = subscriptions.filter((item) => item.plan !== 'Free').length;
    const free = subscriptions.filter((item) => item.plan === 'Free').length;
    const expiring = subscriptions.filter((item) => {
      const days = daysUntil(item.expiry_date);
      return days !== null && days >= 0 && days <= 30;
    }).length;
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
    filtered.sort((a, b) => toSortText(a.name).localeCompare(toSortText(b.name)));
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
    filtered.sort((a, b) => toSortText(a.name).localeCompare(toSortText(b.name)));
    return filtered;
  };

  const renderFreePaidTable = () => {
    if (!freePaidTable) return;
    const rows = getFilteredSubscriptions();
    const total = rows.length;
    const totalPages = Math.max(Math.ceil(total / freePaidPageSize), 1);
    if (freePaidPage > totalPages) freePaidPage = totalPages;
    const startIndex = total ? (freePaidPage - 1) * freePaidPageSize : 0;
    const endIndex = total ? Math.min(startIndex + freePaidPageSize, total) : 0;

    if (!total) {
      freePaidTable.innerHTML = '<tr><td colspan="8" class="text-center text-muted py-4">No accounts found.</td></tr>';
      if (freePaidEntriesInfo) freePaidEntriesInfo.textContent = 'Showing 0 to 0 of 0 Entries';
      if (freePaidPrevBtn) freePaidPrevBtn.disabled = true;
      if (freePaidNextBtn) freePaidNextBtn.disabled = true;
      return;
    }

    const pagedRows = rows.slice(startIndex, endIndex);
    freePaidTable.innerHTML = pagedRows
      .map((sub) => {
        const badge = statusBadge(sub);
        const expiryText = safeText(sub.expiry_date);
        const badgeLabel = badge === 'danger' ? 'Expired' : badge === 'warning' ? 'Expiring' : badge === 'neutral' ? 'No Expiry' : 'Active';
        const id = escapeHtml(String(sub.id || ''));
        return `
<tr>
  <td>${safeText(sub.name)}</td>
  <td>${safeText(sub.account_type)}</td>
  <td><span class="badge ${sub.plan === 'Free' ? 'neutral' : 'info'}">${safeText(sub.plan)}</span></td>
  <td>${safeText(sub.payment_status)}</td>
  <td>${safeText(sub.start_date)}</td>
  <td>${expiryText}</td>
  <td><span class="badge ${badge}">${badgeLabel}</span></td>
  <td>
    <button class="action-btn" type="button" data-free-paid-action="view" data-subscription-id="${id}">
      <i class="fa-solid fa-eye"></i> View
    </button>
  </td>
</tr>`;
      })
      .join('');

    if (freePaidEntriesInfo) {
      freePaidEntriesInfo.textContent = `Showing ${startIndex + 1} to ${endIndex} of ${total} Entries`;
    }
    if (freePaidPrevBtn) freePaidPrevBtn.disabled = freePaidPage <= 1;
    if (freePaidNextBtn) freePaidNextBtn.disabled = freePaidPage >= totalPages;
  };

  const renderSubscriptionTable = () => {
    if (!subscriptionTableBody) return;
    const rows = getFilteredPlans();
    if (!rows.length) {
      subscriptionTableBody.innerHTML =
        '<tr><td colspan="20" class="text-center text-muted py-4">No plans found.</td></tr>';
      return;
    }
    const deleteButton = (planId) =>
      canDelete
        ? `<button class="action-btn danger" data-sub-action="delete" data-id="${safeText(planId, '')}"><i class="fa-solid fa-trash"></i> Delete</button>`
        : '';
    subscriptionTableBody.innerHTML = rows
      .map((plan) => `
<tr>
  <td>${safeText(plan.name)}</td>
  <td>${safeText(plan.plan_code)}</td>
  <td>INR ${formatNumber(plan.price_monthly)}</td>
  <td>INR ${formatNumber(plan.price_quarterly)}</td>
  <td>${safeText(plan.job_posts)}</td>
  <td>${safeText(plan.job_validity)}</td>
  <td>${safeText(plan.resume_view)}</td>
  <td>${safeText(plan.resume_download)}</td>
  <td>${safeText(plan.candidate_chat)}</td>
  <td>${safeText(plan.interview_scheduler)}</td>
  <td>${safeText(plan.auto_match)}</td>
  <td>${safeText(plan.shortlisting)}</td>
  <td>${safeText(plan.candidate_ranking)}</td>
  <td>${safeText(plan.candidate_pool_manager)}</td>
  <td>${safeText(plan.featured_jobs)}</td>
  <td>${safeText(plan.company_branding)}</td>
  <td>${safeText(plan.analytics_dashboard)}</td>
  <td>${safeText(plan.support)}</td>
  <td>${safeText(plan.dedicated_account_manager)}</td>
  <td>
    <div class="table-actions">
      <button class="action-btn" data-sub-action="view" data-id="${safeText(plan.id, '')}"><i class="fa-solid fa-eye"></i> View</button>
      <button class="action-btn" data-sub-action="edit" data-id="${safeText(plan.id, '')}"><i class="fa-solid fa-pen"></i> Edit</button>
      ${deleteButton(plan.id)}
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
        if (!canDelete) {
          showToast('Delete action is disabled for subadmin.', 'warning');
          return;
        }
        deleteSubscriptionId = id;
        if (subscriptionDeleteModal) {
          subscriptionDeleteModal.show();
        } else {
          showToast('Delete modal unavailable. Refresh page and try again.', 'danger');
        }
      }
    });
  };

  const renderBillingSummary = (subscription) => {
    if (!billingSummaryGrid) return;
    const items = [
      ['Account', subscription.name],
      ['Account Type', subscription.account_type],
      ['Plan', subscription.plan],
      ['Payment Status', subscription.payment_status],
      ['Start Date', subscription.start_date],
      ['End Date', subscription.expiry_date],
      ['Auto Renew', subscription.auto_renew ? 'Enabled' : 'Disabled'],
      ['Estimated Monthly Billing', formatCurrency(subscription.monthly_revenue, 'INR')],
      ['Contact', subscription.contact],
    ];
    billingSummaryGrid.innerHTML = items
      .map(
        ([label, value]) => `
<div class="payment-summary-item">
  <span>${label}</span>
  <strong>${safeText(value || '-')}</strong>
</div>`,
      )
      .join('');
  };

  const renderBillingHistoryRows = (payments) => {
    if (!billingHistoryModalBody) return;
    if (!payments.length) {
      billingHistoryModalBody.innerHTML =
        '<tr><td colspan="11" class="text-center text-muted py-4">No payment history found for this subscription.</td></tr>';
      return;
    }
    billingHistoryModalBody.innerHTML = payments
      .map((payment) => {
        const dateParts = extractDateParts(payment.created_at);
        const statusValue = String(payment.status || '').toLowerCase();
        const statusClass = statusValue === 'success' ? 'success' : statusValue === 'failed' ? 'danger' : 'warning';
        const gatewayRef = payment.gateway_reference || payment.gateway_order_id || '-';
        return `
<tr>
  <td>${safeText(payment.payment_id)}</td>
  <td>${safeText(payment.plan_code)}</td>
  <td>${safeText(normalizeLabel(payment.billing_cycle))}</td>
  <td>${formatCurrency(payment.amount, payment.currency || 'INR')}</td>
  <td><span class="badge ${statusClass}">${safeText(normalizeLabel(payment.status))}</span></td>
  <td>${safeText(payment.provider || '-')}</td>
  <td>${safeText(dateParts.date)}</td>
  <td>${safeText(dateParts.time)}</td>
  <td>${safeText(dateParts.month)}</td>
  <td>${safeText(dateParts.year)}</td>
  <td>${safeText(gatewayRef)}</td>
</tr>`;
      })
      .join('');
  };

  const openBillingDetails = async (subscriptionId) => {
    if (!subscriptionId) return;
    setLoading(true);
    const data = await fetchJson(`/api/subscriptions/${encodeURIComponent(subscriptionId)}/payments/`);
    setLoading(false);
    if (!data || !data.success) {
      showToast(data.error || 'Unable to load payment details.', 'danger');
      return;
    }

    renderBillingSummary(data.subscription || {});
    renderBillingHistoryRows(Array.isArray(data.payments) ? data.payments : []);

    if (billingDetailsModal) {
      billingDetailsModal.show();
      return;
    }
    showToast('Billing details modal unavailable. Refresh page and try again.', 'danger');
  };

  const bindFreePaidTable = () => {
    if (!freePaidTable || freePaidTable.dataset.bound) return;
    freePaidTable.dataset.bound = 'true';
    freePaidTable.addEventListener('click', (event) => {
      const button = event.target.closest('[data-free-paid-action="view"]');
      if (!button) return;
      openBillingDetails(button.dataset.subscriptionId);
    });
  };

  const renderExpiryTable = () => {
    if (!expiryTable) return;
    const limit = expiryFilter ? Number(expiryFilter.value) : 30;
    const rows = subscriptions
      .map((sub) => ({ ...sub, daysLeft: daysUntil(sub.expiry_date) }))
      .filter((sub) => sub.daysLeft !== null && sub.daysLeft <= limit)
      .sort((a, b) => a.daysLeft - b.daysLeft);

    if (!rows.length) {
      expiryTable.innerHTML = '<tr><td colspan="6" class="text-center text-muted py-4">No expiry alerts.</td></tr>';
      return;
    }

    expiryTable.innerHTML = rows
      .map((sub) => `
<tr>
  <td>${safeText(sub.name)}</td>
  <td>${safeText(sub.plan)}</td>
  <td>${safeText(sub.expiry_date)}</td>
  <td>${sub.daysLeft} days</td>
  <td>${safeText(sub.contact)}</td>
  <td>
    <div class="table-actions">
      <button class="action-btn" data-action="notify" data-id="${safeText(sub.id, '')}">Notify</button>
      <button class="action-btn" data-action="extend" data-id="${safeText(sub.id, '')}">Extend</button>
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
  <span>${safeText(row.month)}</span>
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
  <td>${safeText(row.month)} 2026</td>
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
  <td>${safeText(log.account)}</td>
  <td>${safeText(log.old_plan)}</td>
  <td>${safeText(log.new_plan)}</td>
  <td>${safeText(log.admin)}</td>
  <td>${safeText(log.date)}</td>
</tr>`)
      .join('');
  };

  const populateAssignSelect = () => {
    if (!assignAccount) return;
    assignAccount.innerHTML = subscriptions
      .slice()
      .sort((a, b) => toSortText(a.name).localeCompare(toSortText(b.name)))
      .map((sub) => `<option value="${safeText(sub.id, '')}">${safeText(sub.name)} (${safeText(sub.account_type)})</option>`)
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

    if (subscriptionFormModal) {
      subscriptionFormModal.show();
      return;
    }
    showToast('Form modal unavailable. Refresh page and try again.', 'danger');
  };

  const openSubscriptionView = (id) => {
    if (!subscriptionViewContent) return;
    const plan = plans.find((item) => String(item.id) === String(id));
    if (!plan) return;
    subscriptionViewContent.innerHTML = `
<div class="details-card">
  <h6>Subscription Plan</h6>
  <div class="details-list">
    <div><span>Plan:</span> ${safeText(plan.name)}</div>
    <div><span>Code:</span> ${safeText(plan.plan_code)}</div>
    <div><span>Monthly Price:</span> INR ${formatNumber(plan.price_monthly)}</div>
    <div><span>Quarterly Price:</span> INR ${formatNumber(plan.price_quarterly)}</div>
    <div><span>Job Posts:</span> ${safeText(plan.job_posts)}</div>
    <div><span>Job Validity:</span> ${safeText(plan.job_validity)}</div>
    <div><span>Resume View:</span> ${safeText(plan.resume_view)}</div>
    <div><span>Resume Download:</span> ${safeText(plan.resume_download)}</div>
    <div><span>Candidate Chat:</span> ${safeText(plan.candidate_chat)}</div>
    <div><span>Interview Scheduler:</span> ${safeText(plan.interview_scheduler)}</div>
    <div><span>Auto Match:</span> ${safeText(plan.auto_match)}</div>
    <div><span>Shortlisting:</span> ${safeText(plan.shortlisting)}</div>
    <div><span>Candidate Ranking:</span> ${safeText(plan.candidate_ranking)}</div>
    <div><span>Candidate Pool Manager:</span> ${safeText(plan.candidate_pool_manager)}</div>
    <div><span>Featured Jobs:</span> ${safeText(plan.featured_jobs)}</div>
    <div><span>Company Branding:</span> ${safeText(plan.company_branding)}</div>
    <div><span>Analytics Dashboard:</span> ${safeText(plan.analytics_dashboard)}</div>
    <div><span>Support:</span> ${safeText(plan.support)}</div>
    <div><span>Dedicated Account Manager:</span> ${safeText(plan.dedicated_account_manager)}</div>
  </div>
</div>`;
    if (subscriptionViewModal) {
      subscriptionViewModal.show();
      return;
    }
    showToast('View modal unavailable. Refresh page and try again.', 'danger');
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
        const sub = subscriptions.find((item) => String(item.id) === String(id));
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
    try {
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
      return true;
    } finally {
      if (!silent) setLoading(false);
    }
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
      const sub = subscriptions.find((item) => String(item.id) === String(selectedId));
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
      freePaidPage = 1;
      refreshData();
    });
  }

  if (freePaidEntriesSelect) {
    freePaidEntriesSelect.addEventListener('change', () => {
      freePaidPageSize = Number(freePaidEntriesSelect.value || 10) || 10;
      freePaidPage = 1;
      renderFreePaidTable();
    });
  }

  if (freePaidPrevBtn) {
    freePaidPrevBtn.addEventListener('click', () => {
      if (freePaidPage <= 1) return;
      freePaidPage -= 1;
      renderFreePaidTable();
    });
  }

  if (freePaidNextBtn) {
    freePaidNextBtn.addEventListener('click', () => {
      const totalRows = getFilteredSubscriptions().length;
      const totalPages = Math.max(Math.ceil(totalRows / freePaidPageSize), 1);
      if (freePaidPage >= totalPages) return;
      freePaidPage += 1;
      renderFreePaidTable();
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

  if (downloadReportBtn) {
    downloadReportBtn.addEventListener('click', () => {
      if (!revenueSeries.length) {
        showToast('No revenue data available to download.', 'warning');
        return;
      }
      const header = ['Month', 'Free', 'Basic', 'Standard', 'Gold', 'Total'];
      const rows = revenueSeries.map((row) => {
        const total = row.free + row.basic + row.standard + row.gold;
        return [row.month, row.free, row.basic, row.standard, row.gold, total];
      });
      const csv = [header.join(',')]
        .concat(rows.map((row) => row.map((val) => `"${String(val).replace(/"/g, '""')}"`).join(',')))
        .join('\n');
      const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = 'subscription-revenue-report.csv';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
      showToast('Revenue report downloaded', 'success');
    });
  }

  if (subscriptionForm) {
    subscriptionForm.addEventListener('submit', handleSubscriptionSubmit);
  }

  if (addSubscriptionBtn) {
    addSubscriptionBtn.addEventListener('click', (event) => {
      event.preventDefault();
      openSubscriptionForm();
    });
  }

  if (confirmSubscriptionDelete) {
    confirmSubscriptionDelete.addEventListener('click', async () => {
      if (!canDelete) {
        showToast('Delete action is disabled for subadmin.', 'warning');
        return;
      }
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
    <div><span>Name:</span> ${safeText(data.name)}</div>
    <div><span>Price:</span> ${safeText(data.price)}</div>
  </div>
</div>`;
        if (addonViewModal) {
          addonViewModal.show();
          return;
        }
        showToast('Add-on view modal unavailable. Refresh page and try again.', 'danger');
      }
      if (action === 'edit') {
        if (addonNameInput) addonNameInput.value = data.name || '';
        if (addonPriceInput) addonPriceInput.value = data.price || '';
        if (addonEditModal) {
          addonEditModal.show();
          return;
        }
        showToast('Add-on edit modal unavailable. Refresh page and try again.', 'danger');
      }
      if (action === 'delete') {
        if (!canDelete) {
          showToast('Delete action is disabled for subadmin.', 'warning');
          return;
        }
        if (addonDeleteModal) {
          addonDeleteModal.show();
          return;
        }
        showToast('Add-on delete modal unavailable. Refresh page and try again.', 'danger');
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
      if (!canDelete) {
        showToast('Delete action is disabled for subadmin.', 'warning');
        return;
      }
      if (activeAddonRow) {
        activeAddonRow.remove();
        showToast('Add-on deleted', 'success');
      }
      activeAddonRow = null;
      if (addonDeleteModal) addonDeleteModal.hide();
    });
  }

  bindSubscriptionTable();
  bindFreePaidTable();

  renderRevenue();
  refreshPlans();
  refreshData();

  setInterval(() => {
    if (document.hidden) return;
    if (document.querySelector('.modal.show')) return;
    refreshData(true);
    refreshPlans();
  }, pollInterval);
})();
