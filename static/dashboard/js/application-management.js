(() => {
  const body = document.body;
  const statusScope = body.dataset.appStatus || 'all';
  const profileName = (
    document.querySelector('.profile-meta strong')?.textContent ||
    document.querySelector('.company-user-meta strong')?.textContent ||
    ''
  )
    .trim()
    .toLowerCase();
  const isSubadmin = profileName === 'subadmin' || body.dataset.panelRole === 'subadmin';
  const canDelete = body.dataset.canDelete === 'true' || (body.dataset.canDelete !== 'false' && !isSubadmin);
  const tableBody = document.getElementById('tableBody');
  if (!tableBody) {
    return;
  }
  const tableHasCandidateResponseColumn = Array.from(
    document.querySelectorAll('#dataTable thead th')
  ).some((cell) => (cell.textContent || '').trim().toLowerCase() === 'candidate response');

  const searchInput = document.getElementById('searchInput');
  const filterStatus = document.getElementById('filterStatus');
  const paginationEl = document.getElementById('pagination');
  const addBtn = document.getElementById('addBtn');
  const exportBtn = document.getElementById('exportBtn');
  const toastContainer = document.getElementById('toastContainer');
  const loadingOverlay = document.getElementById('loadingOverlay');
  const pageSizeStorageKey = 'je_admin_page_size';
  const pageSizeOptions = [10, 25, 50, 100];

  const liveJobsCountEl = document.getElementById('liveJobsCount');
  const applicantCountEl = document.getElementById('applicantCount');
  const interviewCountEl = document.getElementById('interviewCount');
  const offerCountEl = document.getElementById('offerCount');

  const manualScheduleForm = document.getElementById('manualScheduleForm');
  const manualApplicationSelect = document.getElementById('manualApplicationSelect');
  const manualInterviewDate = document.getElementById('manualInterviewDate');
  const manualInterviewTime = document.getElementById('manualInterviewTime');
  const manualInterviewer = document.getElementById('manualInterviewer');

  const formModalEl = document.getElementById('applicationFormModal');
  const viewModalEl = document.getElementById('applicationViewModal');
  const deleteModalEl = document.getElementById('applicationDeleteModal');

  const modalOptions = { backdrop: false, keyboard: true };
  const formModal = formModalEl ? new bootstrap.Modal(formModalEl, modalOptions) : null;
  const viewModal = viewModalEl ? new bootstrap.Modal(viewModalEl, modalOptions) : null;
  const deleteModal = deleteModalEl ? new bootstrap.Modal(deleteModalEl, modalOptions) : null;

  const applicationForm = document.getElementById('applicationForm');
  const formTitle = document.getElementById('formTitle');
  const applicationIdInput = document.getElementById('applicationId');
  const viewContent = document.getElementById('applicationViewContent');
  const confirmDeleteBtn = document.getElementById('confirmDeleteBtn');

  const STORAGE_KEY = 'jobex_applications';
  const pollInterval = 15000;

  let currentPage = 1;
  let totalPages = 1;
  let totalCount = 0;
  let deleteTarget = null;
  let useApi = true;
  let apiWarned = false;
  let pageSize = 10;
  let tableInfoEl = null;
  let pageSizeSelect = null;
  let jobIdFilter = '';
  let jobTitleFilter = '';

  if (!canDelete) {
    if (confirmDeleteBtn) {
      confirmDeleteBtn.style.display = 'none';
      confirmDeleteBtn.disabled = true;
    }
  }

  const defaultApplications = [
    {
      id: 'APP-1201',
      candidate_name: 'Ritika Sharma',
      candidate_email: 'ritika.sharma@email.com',
      candidate_phone: '+91 98910 11223',
      candidate_location: 'Bangalore, IN',
      education: 'B.Tech (CSE)',
      experience: '3 years',
      job_title: 'Senior Backend Engineer',
      company: 'NimbusTech',
      status: 'Interview Scheduled',
      applied_date: '2026-02-10',
      interview_date: '2026-02-18',
      interview_time: '11:00',
      interviewer: 'Ankit Rao',
      offer_package: '',
      joining_date: '',
      notes: 'Strong system design skills.',
    },
    {
      id: 'APP-1202',
      candidate_name: 'Vikram Jain',
      candidate_email: 'vikram.jain@email.com',
      candidate_phone: '+91 98120 55678',
      candidate_location: 'Mumbai, IN',
      education: 'MBA',
      experience: '5 years',
      job_title: 'Business Development Manager',
      company: 'HirePulse',
      status: 'Selected',
      applied_date: '2026-02-06',
      interview_date: '2026-02-12',
      interview_time: '15:30',
      interviewer: 'Nisha Kapoor',
      offer_package: '',
      joining_date: '',
      notes: 'Great client-facing skills.',
    },
    {
      id: 'APP-1203',
      candidate_name: 'Meera Nair',
      candidate_email: 'meera.nair@email.com',
      candidate_phone: '+91 98220 99100',
      candidate_location: 'Chennai, IN',
      education: 'B.Des',
      experience: '2 years',
      job_title: 'Product Designer',
      company: 'BlueOrbit',
      status: 'Offer Issued',
      applied_date: '2026-02-02',
      interview_date: '2026-02-08',
      interview_time: '10:00',
      interviewer: 'Rohan Mehta',
      offer_package: '9 LPA',
      joining_date: '2026-03-05',
      notes: 'Offer accepted verbally.',
    },
    {
      id: 'APP-1204',
      candidate_name: 'Kunal Bansal',
      candidate_email: 'kunal.bansal@email.com',
      candidate_phone: '+91 90011 33445',
      candidate_location: 'Delhi, IN',
      education: 'B.Com',
      experience: '1 year',
      job_title: 'Finance Analyst',
      company: 'LedgerLine',
      status: 'Rejected',
      applied_date: '2026-02-01',
      interview_date: '',
      interview_time: '',
      interviewer: '',
      offer_package: '',
      joining_date: '',
      notes: 'Needs stronger analytical background.',
    },
    {
      id: 'APP-1205',
      candidate_name: 'Sana Ali',
      candidate_email: 'sana.ali@email.com',
      candidate_phone: '+91 98980 55677',
      candidate_location: 'Hyderabad, IN',
      education: 'B.Tech (IT)',
      experience: '4 years',
      job_title: 'Frontend Engineer',
      company: 'NovaWorks',
      status: 'Interview Scheduled',
      applied_date: '2026-02-11',
      interview_date: '2026-02-19',
      interview_time: '16:00',
      interviewer: 'Sara Iqbal',
      offer_package: '',
      joining_date: '',
      notes: 'Portfolio shared.',
    },
    {
      id: 'APP-1206',
      candidate_name: 'Rohit Kumar',
      candidate_email: 'rohit.kumar@email.com',
      candidate_phone: '+91 98188 11220',
      candidate_location: 'Pune, IN',
      education: 'MBA',
      experience: '6 years',
      job_title: 'Customer Success Manager',
      company: 'CloudSprint',
      status: 'Selected',
      applied_date: '2026-02-05',
      interview_date: '2026-02-13',
      interview_time: '12:30',
      interviewer: 'Manish Gupta',
      offer_package: '',
      joining_date: '',
      notes: 'Negotiating offer details.',
    },
    {
      id: 'APP-1207',
      candidate_name: 'Ananya Singh',
      candidate_email: 'ananya.singh@email.com',
      candidate_phone: '+91 99000 55661',
      candidate_location: 'Jaipur, IN',
      education: 'B.A.',
      experience: '2 years',
      job_title: 'Operations Coordinator',
      company: 'SwiftLogix',
      status: 'Rejected',
      applied_date: '2026-02-09',
      interview_date: '',
      interview_time: '',
      interviewer: '',
      offer_package: '',
      joining_date: '',
      notes: 'Not enough logistics exposure.',
    },
    {
      id: 'APP-1208',
      candidate_name: 'Sagar Gupta',
      candidate_email: 'sagar.gupta@email.com',
      candidate_phone: '+91 98765 11190',
      candidate_location: 'Ahmedabad, IN',
      education: 'B.Tech (ECE)',
      experience: '5 years',
      job_title: 'Data Analyst',
      company: 'InsightLoop',
      status: 'Offer Issued',
      applied_date: '2026-02-04',
      interview_date: '2026-02-10',
      interview_time: '14:00',
      interviewer: 'Priya Singh',
      offer_package: '10 LPA',
      joining_date: '2026-03-10',
      notes: 'Offer sent; awaiting response.',
    },
  ];

  const loadLocalApplications = () => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        return JSON.parse(raw);
      }
    } catch (error) {
      return [...defaultApplications];
    }
    return [...defaultApplications];
  };

  const saveLocalApplications = (items) => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
    } catch (error) {
      // ignore
    }
  };

  let localApplications = loadLocalApplications();
  let applications = [...localApplications];

  const formatNumber = (value) => {
    const number = Number(value || 0);
    return Number.isNaN(number) ? '0' : number.toLocaleString();
  };

  const setLoading = (show) => {
    if (!loadingOverlay) return;
    loadingOverlay.classList.toggle('active', show);
  };

  const statusClass = (status) => {
    switch ((status || '').toLowerCase()) {
      case 'selected':
        return 'success';
      case 'interview scheduled':
        return 'warning';
      case 'rejected':
        return 'danger';
      case 'offer issued':
        return 'info';
      default:
        return 'neutral';
    }
  };

  const showToast = (message, type = 'success') => {
    if (!toastContainer) return;
    const toast = document.createElement('div');
    toast.className = `toast-message ${type}`;
    toast.textContent = message;
    toastContainer.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
  };

  const getStoredPageSize = () => {
    try {
      const stored = Number(window.localStorage.getItem(pageSizeStorageKey));
      return Number.isFinite(stored) && stored > 0 ? stored : null;
    } catch {
      return null;
    }
  };

  const setStoredPageSize = (value) => {
    try {
      window.localStorage.setItem(pageSizeStorageKey, String(value));
    } catch {
      // Ignore storage errors.
    }
  };

  const initTableFooter = () => {
    if (!paginationEl) return;
    const parent = paginationEl.parentElement;
    if (!parent) return;
    let footer = parent.querySelector('[data-table-footer]');
    if (!footer) {
      footer = document.createElement('div');
      footer.className = 'table-footer';
      footer.dataset.tableFooter = 'true';
      footer.innerHTML = `
        <div class="table-footer-left">
          <label class="table-size-label">
            Show
            <select class="table-page-size"></select>
            Entries
          </label>
        </div>
        <div class="table-footer-right">
          <span class="table-info">Showing 0 to 0 of 0 Entries</span>
        </div>
      `;
      paginationEl.insertAdjacentElement('beforebegin', footer);
    }
    pageSizeSelect = footer.querySelector('.table-page-size');
    tableInfoEl = footer.querySelector('.table-info');
    if (pageSizeSelect && !pageSizeSelect.dataset.bound) {
      pageSizeSelect.innerHTML = pageSizeOptions
        .map((size) => `<option value="${size}">${size}</option>`)
        .join('');
      pageSizeSelect.value = String(pageSize);
      pageSizeSelect.addEventListener('change', () => {
        const nextSize = Number(pageSizeSelect.value) || 10;
        if (nextSize === pageSize) return;
        pageSize = nextSize;
        setStoredPageSize(pageSize);
        currentPage = 1;
        refreshData();
      });
      pageSizeSelect.dataset.bound = 'true';
    }
  };

  const updateTableInfo = () => {
    if (!tableInfoEl) return;
    const total = Number(totalCount) || 0;
    const start = total === 0 ? 0 : (currentPage - 1) * pageSize + 1;
    const end = total === 0 ? 0 : Math.min(currentPage * pageSize, total);
    tableInfoEl.textContent = `Showing ${start} to ${end} of ${total} Entries`;
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

  const mergeLocalApplications = (items) => {
    if (!Array.isArray(items) || !items.length) return;
    const map = new Map(localApplications.map((item) => [item.id, item]));
    items.forEach((item) => {
      map.set(item.id, { ...map.get(item.id), ...item });
    });
    localApplications = Array.from(map.values());
    saveLocalApplications(localApplications);
  };

  const updateLocalApplication = (item) => {
    if (!item || !item.id) return;
    const index = localApplications.findIndex((row) => row.id === item.id);
    if (index >= 0) {
      localApplications[index] = { ...localApplications[index], ...item };
    } else {
      localApplications.unshift(item);
    }
    saveLocalApplications(localApplications);
  };

  const removeLocalApplication = (id) => {
    localApplications = localApplications.filter((row) => row.id !== id);
    saveLocalApplications(localApplications);
  };

  const updateStats = (stats) => {
    const total = stats && stats.total !== undefined ? stats.total : applications.length;
    const uniqueJobs = stats && stats.unique_jobs !== undefined
      ? stats.unique_jobs
      : new Set(applications.map((app) => app.job_title)).size;
    const interview = stats && stats.interview !== undefined
      ? stats.interview
      : applications.filter((app) => app.status === 'Interview Scheduled').length;
    const offer = stats && stats.offer !== undefined
      ? stats.offer
      : applications.filter((app) => app.status === 'Offer Issued').length;

    if (liveJobsCountEl) liveJobsCountEl.textContent = formatNumber(uniqueJobs);
    if (applicantCountEl) applicantCountEl.textContent = formatNumber(total);
    if (interviewCountEl) interviewCountEl.textContent = formatNumber(interview);
    if (offerCountEl) offerCountEl.textContent = formatNumber(offer);
  };

  const getFilteredApplications = () => {
    let filtered = [...localApplications];
    if (statusScope && statusScope !== 'all') {
      filtered = filtered.filter((app) => app.status === statusScope);
    }
    if (filterStatus && statusScope === 'all' && filterStatus.value !== 'all') {
      filtered = filtered.filter((app) => app.status === filterStatus.value);
    }
    if (jobTitleFilter) {
      const titleNeedle = jobTitleFilter.toLowerCase();
      filtered = filtered.filter((app) => (app.job_title || '').toLowerCase() === titleNeedle);
    }
    const keyword = searchInput ? searchInput.value.trim().toLowerCase() : '';
    if (keyword) {
      filtered = filtered.filter((app) => {
        return (
          app.candidate_name.toLowerCase().includes(keyword) ||
          app.candidate_email.toLowerCase().includes(keyword) ||
          app.job_title.toLowerCase().includes(keyword) ||
          app.company.toLowerCase().includes(keyword)
        );
      });
    }
    filtered.sort((a, b) => a.company.localeCompare(b.company));
    return filtered;
  };

  const populateManualSelect = () => {
    if (!manualApplicationSelect) return;
    const sorted = [...applications].sort((a, b) => a.company.localeCompare(b.company));
    manualApplicationSelect.innerHTML = sorted
      .map((app) => `<option value="${app.id}">${app.company} - ${app.candidate_name} (${app.job_title})</option>`)
      .join('');
  };

  const renderPagination = (pages, onPageChange) => {
    if (!paginationEl) return;
    paginationEl.innerHTML = '';
    if (pages <= 1) return;

    const addButton = (label, page, disabled = false, active = false) => {
      const button = document.createElement('button');
      button.className = `page-btn${active ? ' active' : ''}`;
      button.textContent = label;
      button.disabled = disabled;
      button.addEventListener('click', () => {
        onPageChange(page);
      });
      paginationEl.appendChild(button);
    };

    addButton('Prev', Math.max(1, currentPage - 1), currentPage === 1);
    addButton('Next', Math.min(pages, currentPage + 1), currentPage === pages);
    updateTableInfo();
  };

  const formatSchedule = (app) => {
    if (!app.interview_date && !app.interview_time) return '-';
    if (app.interview_date && app.interview_time) return `${app.interview_date} - ${app.interview_time}`;
    return app.interview_date || app.interview_time;
  };

  const formatCandidateResponse = (app) => {
    const responseKey = String(app.candidate_confirmation_key || '').toLowerCase();
    const responseLabel = String(app.candidate_confirmation || 'Pending');
    let badgeClass = 'neutral';
    if (responseKey === 'accepted') {
      badgeClass = 'success';
    } else if (responseKey === 'declined') {
      badgeClass = 'danger';
    }
    const noteHtml = app.candidate_confirmation_note
      ? `<div class="muted">${app.candidate_confirmation_note}</div>`
      : '';
    const timeHtml = app.candidate_confirmed_at
      ? `<div class="muted">${app.candidate_confirmed_at}</div>`
      : '';
    return `<span class="badge ${badgeClass}">${responseLabel}</span>${noteHtml}${timeHtml}`;
  };

  const renderTableRows = (rows) => {
    const emptyColspan = tableHasCandidateResponseColumn ? 9 : 8;
    if (!rows.length) {
      tableBody.innerHTML = `<tr><td colspan="${emptyColspan}" class="text-center text-muted py-4">No applications found.</td></tr>`;
      return;
    }

    tableBody.innerHTML = rows
      .map((app) => {
        const badgeClass = statusClass(app.status);
        const deleteButton = canDelete
          ? `<button class="action-btn danger" data-action="delete" data-id="${app.id}"><i class="fa-solid fa-trash"></i> Delete</button>`
          : '';
        return `
<tr>
  <td>${app.id}</td>
  <td>
    <strong>${app.candidate_name}</strong>
    <div class="muted">${app.candidate_email}</div>
  </td>
  <td>${app.job_title}</td>
  <td>${app.company}</td>
  <td><span class="badge ${badgeClass}">${app.status}</span></td>
  <td>${app.applied_date || '-'}</td>
  <td>${formatSchedule(app)}</td>
  ${tableHasCandidateResponseColumn ? `<td>${formatCandidateResponse(app)}</td>` : ''}
  <td>
    <div class="table-actions">
      <button class="action-btn" data-action="view" data-id="${app.id}"><i class="fa-solid fa-eye"></i> View</button>
      <button class="action-btn" data-action="edit" data-id="${app.id}"><i class="fa-solid fa-pen"></i> Edit</button>
      ${deleteButton}
    </div>
  </td>
</tr>`;
      })
      .join('');

    bindRowEvents();
  };

  const renderLocalTable = () => {
    const filtered = getFilteredApplications();
    totalCount = filtered.length;
    totalPages = Math.max(1, Math.ceil(filtered.length / pageSize));
    currentPage = Math.min(currentPage, totalPages);
    const start = (currentPage - 1) * pageSize;
    const pageItems = filtered.slice(start, start + pageSize);

    renderTableRows(pageItems);
    renderPagination(totalPages, (page) => {
      currentPage = page;
      renderLocalTable();
    });
    updateTableInfo();
    applications = [...localApplications];
    updateStats();
    populateManualSelect();
  };

  const buildListParams = (page) => {
    const params = new URLSearchParams();
    params.set('page', String(page));
    params.set('page_size', String(pageSize));
    if (jobIdFilter) params.set('job_id', jobIdFilter);
    if (jobTitleFilter) params.set('job_title', jobTitleFilter);
    const keyword = searchInput ? searchInput.value.trim() : '';
    if (keyword) params.set('search', keyword);
    const status = statusScope !== 'all' ? statusScope : filterStatus ? filterStatus.value : 'all';
    if (status) params.set('status', status);
    return params;
  };

  const fetchApplicationsFromApi = async (page = 1, silent = false) => {
    if (!silent) setLoading(true);
    const params = buildListParams(page);
    const data = await fetchJson(`/api/applications/list/?${params.toString()}`);
    if (data.error) {
      if (!apiWarned) {
        showToast(data.error, 'danger');
        apiWarned = true;
      }
      if (!silent) setLoading(false);
      useApi = false;
      return false;
    }
    useApi = true;
    apiWarned = false;
    currentPage = data.page || 1;
    totalPages = data.pages || 1;
    totalCount = data.count || 0;
    applications = Array.isArray(data.results) ? data.results : [];
    renderTableRows(applications);
    renderPagination(totalPages, (nextPage) => {
      currentPage = nextPage;
      fetchApplicationsFromApi(nextPage);
    });
    updateTableInfo();
    updateStats(data.stats);
    populateManualSelect();
    mergeLocalApplications(applications);
    if (!silent) setLoading(false);
    return true;
  };

  const refreshData = async (silent = false) => {
    const ok = await fetchApplicationsFromApi(currentPage, silent);
    if (!ok) {
      localApplications = loadLocalApplications();
      renderLocalTable();
    }
  };

  const fillForm = (app) => {
    if (!applicationForm) return;
    const fields = [
      'candidate_name',
      'candidate_email',
      'candidate_phone',
      'candidate_location',
      'education',
      'experience',
      'job_title',
      'company',
      'status',
      'applied_date',
      'interview_date',
      'interview_time',
      'interviewer',
      'offer_package',
      'joining_date',
      'notes',
    ];
    fields.forEach((field) => {
      const input = applicationForm.querySelector(`[name="${field}"]`);
      if (input && app[field] !== undefined) {
        input.value = app[field] || '';
      }
    });
  };

  const buildViewHtml = (app) => {
    return `
<div class="details-grid">
  <div class="details-card">
    <h6>Candidate Details</h6>
    <div class="details-list">
      <div><span>Name</span> <strong>${app.candidate_name}</strong></div>
      <div><span>Email</span> <strong>${app.candidate_email}</strong></div>
      <div><span>Phone</span> <strong>${app.candidate_phone || '-'}</strong></div>
      <div><span>Location</span> <strong>${app.candidate_location || '-'}</strong></div>
      <div><span>Education</span> <strong>${app.education || '-'}</strong></div>
      <div><span>Experience</span> <strong>${app.experience || '-'}</strong></div>
    </div>
  </div>
  <div class="details-card">
    <h6>Job Details</h6>
    <div class="details-list">
      <div><span>Application ID</span> <strong>${app.id}</strong></div>
      <div><span>Job Title</span> <strong>${app.job_title}</strong></div>
      <div><span>Company</span> <strong>${app.company}</strong></div>
      <div><span>Status</span> <strong>${app.status}</strong></div>
      <div><span>Applied Date</span> <strong>${app.applied_date || '-'}</strong></div>
    </div>
  </div>
  <div class="details-card">
    <h6>Interview Schedule</h6>
    <div class="details-list">
      <div><span>Date</span> <strong>${app.interview_date || '-'}</strong></div>
      <div><span>Time</span> <strong>${app.interview_time || '-'}</strong></div>
      <div><span>Interviewer</span> <strong>${app.interviewer || '-'}</strong></div>
      <div><span>Candidate Response</span> <strong>${app.candidate_confirmation || 'Pending'}</strong></div>
      <div><span>Response Note</span> <strong>${app.candidate_confirmation_note || '-'}</strong></div>
      <div><span>Response Time</span> <strong>${app.candidate_confirmed_at || '-'}</strong></div>
    </div>
  </div>
  <div class="details-card">
    <h6>Offer Details</h6>
    <div class="details-list">
      <div><span>Offer Package</span> <strong>${app.offer_package || '-'}</strong></div>
      <div><span>Joining Date</span> <strong>${app.joining_date || '-'}</strong></div>
      <div><span>Notes</span> <strong>${app.notes || '-'}</strong></div>
    </div>
  </div>
</div>
<div class="view-actions">
  <button class="btn ghost" data-view-action="schedule">Schedule Interview</button>
  <button class="btn ghost" data-view-action="select">Mark Selected</button>
  <button class="btn ghost" data-view-action="reject">Reject</button>
  <button class="btn primary" data-view-action="offer">Issue Offer</button>
</div>
`;
  };

  const toFormData = (payload) => {
    const formData = new FormData();
    Object.entries(payload).forEach(([key, value]) => {
      if (key === 'id') return;
      formData.append(key, value ?? '');
    });
    return formData;
  };

  const updateApplication = async (app) => {
    if (useApi) {
      const formData = toFormData(app);
      const data = await fetchJson(`/api/applications/${encodeURIComponent(app.id)}/update/`, {
        method: 'POST',
        headers: { 'X-CSRFToken': getCookie('csrftoken') },
        body: formData,
      });
      if (data && data.success) {
        updateLocalApplication(data.item);
        await refreshData(true);
        return true;
      }
      useApi = false;
      showToast(data.error || 'Server error. Switching to local data.', 'danger');
    }

    const index = localApplications.findIndex((item) => item.id === app.id);
    if (index >= 0) {
      localApplications[index] = { ...localApplications[index], ...app };
      saveLocalApplications(localApplications);
      renderLocalTable();
      return true;
    }
    return false;
  };

  const deleteApplication = async (id) => {
    if (useApi) {
      const data = await fetchJson(`/api/applications/${encodeURIComponent(id)}/delete/`, {
        method: 'POST',
        headers: { 'X-CSRFToken': getCookie('csrftoken') },
      });
      if (data && data.success) {
        removeLocalApplication(id);
        await refreshData(true);
        return true;
      }
      useApi = false;
      showToast(data.error || 'Server error. Switching to local data.', 'danger');
    }

    localApplications = localApplications.filter((item) => item.id !== id);
    saveLocalApplications(localApplications);
    renderLocalTable();
    return true;
  };

  const createApplication = async (payload) => {
    if (useApi) {
      const formData = toFormData(payload);
      const data = await fetchJson('/api/applications/create/', {
        method: 'POST',
        headers: { 'X-CSRFToken': getCookie('csrftoken') },
        body: formData,
      });
      if (data && data.success) {
        updateLocalApplication(data.item);
        await refreshData(true);
        return true;
      }
      useApi = false;
      showToast(data.error || 'Server error. Switching to local data.', 'danger');
    }

    const nextId = `APP-${Math.max(1200, localApplications.length + 1200 + Math.floor(Math.random() * 50))}`;
    payload.id = nextId;
    localApplications.unshift(payload);
    saveLocalApplications(localApplications);
    renderLocalTable();
    return true;
  };

  const openViewModal = (id) => {
    const app = applications.find((item) => item.id === id) || localApplications.find((item) => item.id === id);
    if (!app || !viewContent) return;
    viewContent.innerHTML = buildViewHtml(app);
    const actionButtons = viewContent.querySelectorAll('[data-view-action]');
    actionButtons.forEach((btn) => {
      btn.addEventListener('click', async () => {
        const action = btn.dataset.viewAction;
        if (action === 'schedule') {
          app.status = 'Interview Scheduled';
          if (!app.interview_date) {
            app.interview_date = new Date(Date.now() + 3 * 86400000).toISOString().slice(0, 10);
          }
          if (!app.interview_time) {
            app.interview_time = '11:00';
          }
        }
        if (action === 'select') app.status = 'Selected';
        if (action === 'reject') app.status = 'Rejected';
        if (action === 'offer') {
          app.status = 'Offer Issued';
          if (!app.offer_package) app.offer_package = '6 LPA';
          if (!app.joining_date) {
            app.joining_date = new Date(Date.now() + 14 * 86400000).toISOString().slice(0, 10);
          }
        }
        const saved = await updateApplication(app);
        if (saved) {
          showToast('Application updated', 'success');
          if (viewModal) viewModal.hide();
        }
      });
    });
    if (viewModal) viewModal.show();
  };

  const openEditModal = (id) => {
    const app = applications.find((item) => item.id === id) || localApplications.find((item) => item.id === id);
    if (!app) return;
    if (applicationIdInput) applicationIdInput.value = app.id;
    if (formTitle) formTitle.textContent = `Edit ${app.candidate_name}`;
    fillForm(app);
    if (formModal) formModal.show();
  };

  const bindRowEvents = () => {
    const actionButtons = document.querySelectorAll('[data-action]');
    actionButtons.forEach((btn) => {
      btn.addEventListener('click', () => {
        const action = btn.dataset.action;
        const id = btn.dataset.id;
        if (action === 'view') openViewModal(id);
        if (action === 'edit') openEditModal(id);
        if (action === 'delete') {
          if (!canDelete) {
            showToast('Delete action is disabled for subadmin.', 'warning');
            return;
          }
          deleteTarget = id;
          if (deleteModal) deleteModal.show();
        }
      });
    });
  };

  const handleFormSubmit = async (event) => {
    event.preventDefault();
    if (!applicationForm) return;
    const formData = new FormData(applicationForm);
    const payload = {
      id: formData.get('application_id') || '',
      candidate_name: formData.get('candidate_name') || '',
      candidate_email: formData.get('candidate_email') || '',
      candidate_phone: formData.get('candidate_phone') || '',
      candidate_location: formData.get('candidate_location') || '',
      education: formData.get('education') || '',
      experience: formData.get('experience') || '',
      job_title: formData.get('job_title') || '',
      company: formData.get('company') || '',
      status: formData.get('status') || 'Interview Scheduled',
      applied_date: formData.get('applied_date') || new Date().toISOString().slice(0, 10),
      interview_date: formData.get('interview_date') || '',
      interview_time: formData.get('interview_time') || '',
      interviewer: formData.get('interviewer') || '',
      offer_package: formData.get('offer_package') || '',
      joining_date: formData.get('joining_date') || '',
      notes: formData.get('notes') || '',
    };

    if (payload.id) {
      const saved = await updateApplication(payload);
      if (saved) showToast('Application updated', 'success');
    } else {
      const saved = await createApplication(payload);
      if (saved) showToast('Application created', 'success');
    }

    applicationForm.reset();
    if (applicationIdInput) applicationIdInput.value = '';
    if (formModal) formModal.hide();
  };

  const handleDelete = async () => {
    if (!canDelete) {
      showToast('Delete action is disabled for subadmin.', 'warning');
      return;
    }
    if (!deleteTarget) return;
    await deleteApplication(deleteTarget);
    deleteTarget = null;
    showToast('Application deleted', 'warning');
    if (deleteModal) deleteModal.hide();
  };

  const exportCsv = () => {
    if (useApi) {
      const params = buildListParams(1);
      window.location.href = `/api/applications/export/?${params.toString()}`;
      return;
    }

    const rows = getFilteredApplications();
    if (!rows.length) {
      showToast('No data to export', 'warning');
      return;
    }
    const header = ['Application ID', 'Candidate', 'Email', 'Job Title', 'Company', 'Status', 'Applied Date'];
    const csv = [header.join(',')]
      .concat(
        rows.map((app) =>
          [app.id, app.candidate_name, app.candidate_email, app.job_title, app.company, app.status, app.applied_date]
            .map((value) => `"${String(value).replace(/"/g, '""')}"`)
            .join(',')
        )
      )
      .join('\n');

    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'applications.csv';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const initStatusFilter = () => {
    if (!filterStatus) return;
    if (statusScope !== 'all') {
      filterStatus.value = statusScope;
      filterStatus.disabled = true;
    }
  };

  const applyInitialQueryFilters = () => {
    const params = new URLSearchParams(window.location.search || '');
    const jobIdValue = (params.get('job_id') || '').trim();
    const jobTitleValue = (params.get('job_title') || '').trim();
    if (jobIdValue) {
      jobIdFilter = jobIdValue;
    }
    if (jobTitleValue) {
      jobTitleFilter = jobTitleValue;
    }
    if (jobIdFilter) {
      const subtitle = document.querySelector('.page-hero .muted');
      if (subtitle) {
        const titleText = jobTitleFilter ? `${jobIdFilter} - ${jobTitleFilter}` : jobIdFilter;
        subtitle.textContent = `Showing applicants for ${titleText}.`;
      }
    }
    const searchValue = (params.get('search') || params.get('job') || jobTitleValue || '').trim();
    if (searchInput && searchValue) {
      searchInput.value = searchValue;
    }
    const statusValue = (params.get('status') || '').trim();
    if (filterStatus && statusScope === 'all' && statusValue) {
      const optionExists = Array.from(filterStatus.options).some((option) => option.value === statusValue);
      if (optionExists) {
        filterStatus.value = statusValue;
      }
    }
  };

  if (applicationForm) {
    applicationForm.addEventListener('submit', handleFormSubmit);
  }

  if (addBtn && applicationForm) {
    addBtn.addEventListener('click', () => {
      applicationForm.reset();
      if (applicationIdInput) applicationIdInput.value = '';
      if (formTitle) formTitle.textContent = 'Add Application';
      if (formModal) formModal.show();
    });
  }

  if (confirmDeleteBtn) {
    confirmDeleteBtn.addEventListener('click', handleDelete);
  }

  if (searchInput) {
    let timer;
    searchInput.addEventListener('input', () => {
      clearTimeout(timer);
      timer = setTimeout(() => {
        currentPage = 1;
        refreshData();
      }, 300);
    });
  }

  if (filterStatus) {
    filterStatus.addEventListener('change', () => {
      currentPage = 1;
      refreshData();
    });
  }

  if (exportBtn) {
    exportBtn.addEventListener('click', exportCsv);
  }

  if (manualScheduleForm) {
    manualScheduleForm.addEventListener('submit', async (event) => {
      event.preventDefault();
      if (!manualApplicationSelect || !manualInterviewDate || !manualInterviewTime) {
        return;
      }
      const id = manualApplicationSelect.value;
      const app = applications.find((item) => item.id === id) || localApplications.find((item) => item.id === id);
      if (!app) {
        showToast('Application not found', 'danger');
        return;
      }
      app.interview_date = manualInterviewDate.value;
      app.interview_time = manualInterviewTime.value;
      app.interviewer = manualInterviewer ? manualInterviewer.value : app.interviewer;
      app.status = 'Interview Scheduled';
      const saved = await updateApplication(app);
      if (saved) {
        showToast('Interview schedule saved', 'success');
        manualScheduleForm.reset();
      }
    });
  }

  window.addEventListener('storage', (event) => {
    if (event.key === STORAGE_KEY && !useApi) {
      localApplications = loadLocalApplications();
      renderLocalTable();
    }
  });

  const storedSize = getStoredPageSize();
  if (storedSize) {
    pageSize = storedSize;
  }
  initTableFooter();
  initStatusFilter();
  applyInitialQueryFilters();
  refreshData();

  setInterval(() => {
    if (document.hidden) return;
    if (document.querySelector('.modal.show')) return;
    refreshData(true);
  }, pollInterval);
})();
