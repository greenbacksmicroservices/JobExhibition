(() => {
  const body = document.body;
  const statusScope = body.dataset.jobStatus || 'all';
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

  const searchInput = document.getElementById('searchInput');
  const filterStatus = document.getElementById('filterStatus');
  const paginationEl = document.getElementById('pagination');
  const addBtn = document.getElementById('addBtn');
  const exportBtn = document.getElementById('exportBtn');
  const toastContainer = document.getElementById('toastContainer');
  const loadingOverlay = document.getElementById('loadingOverlay');

  const formModalEl = document.getElementById('jobFormModal');
  const viewModalEl = document.getElementById('jobViewModal');
  const deleteModalEl = document.getElementById('jobDeleteModal');

  const BootstrapModal = window.bootstrap && window.bootstrap.Modal ? window.bootstrap.Modal : null;
  const modalOptions = { backdrop: false, keyboard: true };
  const formModal = BootstrapModal && formModalEl ? new BootstrapModal(formModalEl, modalOptions) : null;
  const viewModal = BootstrapModal && viewModalEl ? new BootstrapModal(viewModalEl, modalOptions) : null;
  const deleteModal = BootstrapModal && deleteModalEl ? new BootstrapModal(deleteModalEl, modalOptions) : null;

  const jobForm = document.getElementById('jobForm');
  const formTitle = document.getElementById('formTitle');
  const jobIdInput = document.getElementById('jobId');
  const viewContent = document.getElementById('jobViewContent');
  const confirmDeleteBtn = document.getElementById('confirmDeleteBtn');

  const totalCountEl = document.getElementById('jobsTotalCount');
  const approvedCountEl = document.getElementById('jobsApprovedCount');
  const pendingCountEl = document.getElementById('jobsPendingCount');
  const reportedCountEl = document.getElementById('jobsReportedCount');

  const STORAGE_KEY = 'jobex_jobs';
  const pageSize = 8;
  const pollInterval = 15000;

  let currentPage = 1;
  let totalPages = 1;
  let deleteTarget = null;
  let useApi = true;
  let apiWarned = false;

  if (!canDelete) {
    if (confirmDeleteBtn) {
      confirmDeleteBtn.style.display = 'none';
      confirmDeleteBtn.disabled = true;
    }
  }

  const defaultJobs = [
    {
      id: 'JOB-1001',
      title: 'Senior Backend Engineer',
      company: 'NimbusTech',
      category: 'IT & Software',
      location: 'Bangalore, IN',
      job_type: 'Full-time',
      salary: '$3,500 - $4,500',
      experience: '4-6 years',
      skills: 'Python, Django, PostgreSQL',
      posted_date: '2026-02-05',
      status: 'Pending',
      applicants: 42,
      verification: 'Pending',
      featured: false,
      recruiter_name: 'Aditi Sharma',
      recruiter_email: 'aditi@nimbustech.com',
      recruiter_phone: '+91 98765 43210',
      description: 'Lead backend services and improve system performance.',
      requirements: 'Strong API design, Docker, and cloud deployment experience.',
    },
    {
      id: 'JOB-1002',
      title: 'Product Designer',
      company: 'BlueOrbit',
      category: 'Design & Media',
      location: 'Remote',
      job_type: 'Full-time',
      salary: '$2,800 - $3,600',
      experience: '3-5 years',
      skills: 'Figma, Design Systems, UX Research',
      posted_date: '2026-02-08',
      status: 'Approved',
      applicants: 66,
      verification: 'Verified',
      featured: true,
      recruiter_name: 'Rohan Mehta',
      recruiter_email: 'rohan@blueorbit.io',
      recruiter_phone: '+91 99887 66554',
      description: 'Design intuitive product workflows and UI systems.',
      requirements: 'Portfolio with SaaS design projects and collaboration experience.',
    },
    {
      id: 'JOB-1003',
      title: 'Business Development Manager',
      company: 'HirePulse',
      category: 'Sales & Marketing',
      location: 'Delhi, IN',
      job_type: 'Full-time',
      salary: '$2,200 - $3,000',
      experience: '2-4 years',
      skills: 'Lead Generation, CRM, Negotiation',
      posted_date: '2026-02-03',
      status: 'Approved',
      applicants: 29,
      verification: 'Verified',
      featured: false,
      recruiter_name: 'Nisha Kapoor',
      recruiter_email: 'nisha@hirepulse.in',
      recruiter_phone: '+91 98110 22110',
      description: 'Drive partnerships and build enterprise sales pipeline.',
      requirements: 'Strong communication, B2B sales background.',
    },
    {
      id: 'JOB-1004',
      title: 'Digital Marketing Specialist',
      company: 'BrightLeaf',
      category: 'Marketing',
      location: 'Mumbai, IN',
      job_type: 'Full-time',
      salary: '$1,800 - $2,400',
      experience: '1-3 years',
      skills: 'SEO, Paid Ads, Analytics',
      posted_date: '2026-01-30',
      status: 'Rejected',
      applicants: 18,
      verification: 'Flagged',
      featured: false,
      recruiter_name: 'Kunal Desai',
      recruiter_email: 'kunal@brightleaf.in',
      recruiter_phone: '+91 99001 12345',
      description: 'Execute paid campaigns and improve organic acquisition.',
      requirements: 'Google Ads certification preferred.',
    },
    {
      id: 'JOB-1005',
      title: 'Operations Coordinator',
      company: 'SwiftLogix',
      category: 'Operations',
      location: 'Hyderabad, IN',
      job_type: 'Full-time',
      salary: '$1,400 - $1,900',
      experience: '1-2 years',
      skills: 'Process Optimization, Vendor Mgmt',
      posted_date: '2026-02-10',
      status: 'Reported',
      applicants: 12,
      verification: 'Pending',
      featured: false,
      recruiter_name: 'Ankit Rao',
      recruiter_email: 'ankit@swiftlogix.com',
      recruiter_phone: '+91 97777 88888',
      description: 'Coordinate daily operations and vendor schedules.',
      requirements: 'Strong Excel and reporting skills.',
    },
    {
      id: 'JOB-1006',
      title: 'Frontend Engineer',
      company: 'NovaWorks',
      category: 'IT & Software',
      location: 'Remote',
      job_type: 'Contract',
      salary: '$3,000 - $3,800',
      experience: '3-5 years',
      skills: 'React, TypeScript, CSS',
      posted_date: '2026-02-11',
      status: 'Pending',
      applicants: 35,
      verification: 'Pending',
      featured: false,
      recruiter_name: 'Sara Iqbal',
      recruiter_email: 'sara@novaworks.dev',
      recruiter_phone: '+91 90909 12000',
      description: 'Build high performance UI for product modules.',
      requirements: 'Experience with modern frontend tooling.',
    },
    {
      id: 'JOB-1007',
      title: 'Finance Analyst',
      company: 'LedgerLine',
      category: 'Finance',
      location: 'Chennai, IN',
      job_type: 'Full-time',
      salary: '$2,600 - $3,200',
      experience: '2-4 years',
      skills: 'Forecasting, Reporting, Excel',
      posted_date: '2026-02-01',
      status: 'Approved',
      applicants: 24,
      verification: 'Verified',
      featured: false,
      recruiter_name: 'Divya Menon',
      recruiter_email: 'divya@ledgerline.io',
      recruiter_phone: '+91 98888 77661',
      description: 'Support finance planning and monthly reporting.',
      requirements: 'CA/CPA candidates preferred.',
    },
    {
      id: 'JOB-1008',
      title: 'Customer Success Manager',
      company: 'CloudSprint',
      category: 'Support',
      location: 'Remote',
      job_type: 'Full-time',
      salary: '$2,300 - $3,100',
      experience: '3-5 years',
      skills: 'Account Management, SaaS, Retention',
      posted_date: '2026-02-09',
      status: 'Reported',
      applicants: 14,
      verification: 'Flagged',
      featured: false,
      recruiter_name: 'Manish Gupta',
      recruiter_email: 'manish@cloudsprint.com',
      recruiter_phone: '+91 99111 00990',
      description: 'Drive renewals and onboarding for enterprise clients.',
      requirements: 'Experience handling enterprise customers.',
    },
    {
      id: 'JOB-1009',
      title: 'HR Manager',
      company: 'TalentForge',
      category: 'Human Resources',
      location: 'Pune, IN',
      job_type: 'Full-time',
      salary: '$2,000 - $2,800',
      experience: '4-6 years',
      skills: 'Hiring, Policy, L&D',
      posted_date: '2026-01-28',
      status: 'Rejected',
      applicants: 10,
      verification: 'Flagged',
      featured: false,
      recruiter_name: 'Sneha Kulkarni',
      recruiter_email: 'sneha@talentforge.in',
      recruiter_phone: '+91 90909 99887',
      description: 'Lead HR operations and strategic hiring programs.',
      requirements: 'Strong compliance and policy management.',
    },
    {
      id: 'JOB-1010',
      title: 'Data Analyst',
      company: 'InsightLoop',
      category: 'Analytics',
      location: 'Remote',
      job_type: 'Full-time',
      salary: '$2,700 - $3,400',
      experience: '2-4 years',
      skills: 'SQL, PowerBI, Python',
      posted_date: '2026-02-07',
      status: 'Approved',
      applicants: 51,
      verification: 'Verified',
      featured: true,
      recruiter_name: 'Priya Singh',
      recruiter_email: 'priya@insightloop.ai',
      recruiter_phone: '+91 92345 67890',
      description: 'Analyze product metrics and build dashboards.',
      requirements: 'Experience with BI tools and data modeling.',
    },
  ];

  const loadLocalJobs = () => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        return JSON.parse(raw);
      }
    } catch (error) {
      return [...defaultJobs];
    }
    return [...defaultJobs];
  };

  const saveLocalJobs = (items) => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
    } catch (error) {
      // ignore storage errors
    }
  };

  let localJobs = loadLocalJobs();
  let jobs = [...localJobs];

  const formatNumber = (value) => {
    const number = Number(value || 0);
    return Number.isNaN(number) ? '0' : number.toLocaleString();
  };

  const escapeHtml = (value) =>
    String(value ?? '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');

  const toSearchText = (value) => String(value ?? '').toLowerCase();

  const safeText = (value, fallback = '-') => {
    const normalized = String(value ?? '').trim();
    return normalized ? escapeHtml(normalized) : fallback;
  };

  const safeMultilineText = (value, fallback = '-') => {
    const normalized = String(value ?? '').trim();
    if (!normalized) return fallback;
    return escapeHtml(normalized).replace(/\n/g, '<br>');
  };

  const setLoading = (show) => {
    if (!loadingOverlay) return;
    loadingOverlay.classList.toggle('active', show);
  };

  const statusClass = (status) => {
    switch ((status || '').toLowerCase()) {
      case 'approved':
        return 'success';
      case 'pending':
        return 'warning';
      case 'rejected':
        return 'danger';
      case 'reported':
        return 'info';
      default:
        return 'neutral';
    }
  };

  const showToast = (message, type = 'success') => {
    if (!toastContainer) {
      return;
    }
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

  const mergeLocalJobs = (items) => {
    if (!Array.isArray(items) || !items.length) return;
    const map = new Map(localJobs.map((item) => [item.id, item]));
    items.forEach((item) => {
      map.set(item.id, { ...map.get(item.id), ...item });
    });
    localJobs = Array.from(map.values());
    saveLocalJobs(localJobs);
  };

  const updateLocalJob = (item) => {
    if (!item || !item.id) return;
    const index = localJobs.findIndex((row) => row.id === item.id);
    if (index >= 0) {
      localJobs[index] = { ...localJobs[index], ...item };
    } else {
      localJobs.unshift(item);
    }
    saveLocalJobs(localJobs);
  };

  const removeLocalJob = (id) => {
    localJobs = localJobs.filter((row) => row.id !== id);
    saveLocalJobs(localJobs);
  };

  const updateStats = (stats) => {
    if (!stats) return;
    if (totalCountEl) totalCountEl.textContent = formatNumber(stats.total);
    if (approvedCountEl) approvedCountEl.textContent = formatNumber(stats.approved);
    if (pendingCountEl) pendingCountEl.textContent = formatNumber(stats.pending);
    if (reportedCountEl) reportedCountEl.textContent = formatNumber(stats.reported);
  };

  const computeLocalStats = () => {
    const total = localJobs.length;
    const approved = localJobs.filter((job) => job.status === 'Approved').length;
    const pending = localJobs.filter((job) => job.status === 'Pending').length;
    const reported = localJobs.filter((job) => job.status === 'Reported').length;
    return {
      total,
      approved,
      pending,
      reported,
    };
  };

  const getFilteredJobs = () => {
    let filtered = [...localJobs];
    if (statusScope && statusScope !== 'all') {
      filtered = filtered.filter((job) => job.status === statusScope);
    }
    if (filterStatus && statusScope === 'all' && filterStatus.value !== 'all') {
      filtered = filtered.filter((job) => job.status === filterStatus.value);
    }
    const keyword = searchInput ? searchInput.value.trim().toLowerCase() : '';
    if (keyword) {
      filtered = filtered.filter((job) => {
        return (
          toSearchText(job.title).includes(keyword) ||
          toSearchText(job.company).includes(keyword) ||
          toSearchText(job.category).includes(keyword) ||
          toSearchText(job.location).includes(keyword)
        );
      });
    }
    return filtered;
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
    for (let i = 1; i <= pages; i += 1) {
      addButton(String(i), i, false, i === currentPage);
    }
    addButton('Next', Math.min(pages, currentPage + 1), currentPage === pages);
  };

  const renderTableRows = (rows) => {
    if (!rows.length) {
      tableBody.innerHTML = '<tr><td colspan="7" class="text-center text-muted py-4">No jobs found.</td></tr>';
      return;
    }

    tableBody.innerHTML = rows
      .map((job) => {
        const badgeClass = statusClass(job.status);
        const jobId = safeText(job.id);
        const title = safeText(job.title);
        const category = safeText(job.category);
        const location = safeText(job.location);
        const company = safeText(job.company);
        const status = safeText(job.status);
        const postedDate = safeText(job.posted_date);
        const applicants = safeText(job.applicants ?? 0, '0');
        const featured = job.featured ? '<span class="badge info" style="margin-left:6px;">Featured</span>' : '';
        const deleteButton = canDelete
          ? `<button class="action-btn danger" data-action="delete" data-id="${jobId}"><i class="fa-solid fa-trash"></i> Delete</button>`
          : '';
        return `
<tr>
  <td>${jobId}</td>
  <td>
    <strong>${title}</strong>
    <div class="muted">${category} - ${location}</div>
    ${featured}
  </td>
  <td>${company}</td>
  <td><span class="badge ${badgeClass}">${status}</span></td>
  <td>${postedDate}</td>
  <td>${applicants}</td>
  <td>
    <div class="table-actions">
      <button class="action-btn" data-action="view" data-id="${jobId}"><i class="fa-solid fa-eye"></i> Details</button>
      <button class="action-btn" data-action="edit" data-id="${jobId}"><i class="fa-solid fa-pen"></i> Edit</button>
      ${deleteButton}
    </div>
  </td>
</tr>`;
      })
      .join('');

    bindRowEvents();
  };

  const renderLocalTable = () => {
    const filtered = getFilteredJobs();
    totalPages = Math.max(1, Math.ceil(filtered.length / pageSize));
    currentPage = Math.min(currentPage, totalPages);
    const start = (currentPage - 1) * pageSize;
    const pageItems = filtered.slice(start, start + pageSize);

    renderTableRows(pageItems);
    renderPagination(totalPages, (page) => {
      currentPage = page;
      renderLocalTable();
    });
    updateStats(computeLocalStats());
  };

  const buildListParams = (page) => {
    const params = new URLSearchParams();
    params.set('page', String(page));
    params.set('page_size', String(pageSize));
    const keyword = searchInput ? searchInput.value.trim() : '';
    if (keyword) params.set('search', keyword);
    const status = statusScope !== 'all' ? statusScope : filterStatus ? filterStatus.value : 'all';
    if (status) params.set('status', status);
    return params;
  };

  const fetchJobsFromApi = async (page = 1, silent = false) => {
    if (!silent) setLoading(true);
    try {
      const params = buildListParams(page);
      const data = await fetchJson(`/api/jobs/list/?${params.toString()}`);
      if (data.error) {
        if (!apiWarned) {
          showToast(data.error, 'danger');
          apiWarned = true;
        }
        useApi = false;
        return false;
      }
      useApi = true;
      apiWarned = false;
      currentPage = data.page || 1;
      totalPages = data.pages || 1;
      jobs = Array.isArray(data.results) ? data.results : [];
      renderTableRows(jobs);
      renderPagination(totalPages, (nextPage) => {
        currentPage = nextPage;
        fetchJobsFromApi(nextPage);
      });
      updateStats(data.stats);
      mergeLocalJobs(jobs);
      return true;
    } catch (error) {
      useApi = false;
      if (!apiWarned) {
        showToast('Unable to load jobs from server. Showing local data.', 'danger');
        apiWarned = true;
      }
      return false;
    } finally {
      if (!silent) setLoading(false);
    }
  };

  const refreshData = async (silent = false) => {
    const ok = await fetchJobsFromApi(currentPage, silent);
    if (!ok) {
      localJobs = loadLocalJobs();
      renderLocalTable();
    }
  };

  const fillForm = (job) => {
    if (!jobForm) return;
    const fields = [
      'title',
      'category',
      'location',
      'job_type',
      'salary',
      'experience',
      'skills',
      'posted_date',
      'status',
      'applicants',
      'verification',
      'company',
      'recruiter_name',
      'recruiter_email',
      'recruiter_phone',
      'description',
      'requirements',
    ];
    fields.forEach((field) => {
      const input = jobForm.querySelector(`[name="${field}"]`);
      if (input && job[field] !== undefined) {
        input.value = job[field] || '';
      }
    });
    const featured = jobForm.querySelector('[name="featured"]');
    if (featured) {
      featured.checked = Boolean(job.featured);
    }
  };

  const buildViewHtml = (job) => {
    return `
<div class="details-grid">
  <div class="details-card">
    <h6>Job Overview</h6>
    <div class="details-list">
      <div><span>Job ID</span> <strong>${safeText(job.id)}</strong></div>
      <div><span>Status</span> <strong>${safeText(job.status)}</strong></div>
      <div><span>Category</span> <strong>${safeText(job.category)}</strong></div>
      <div><span>Location</span> <strong>${safeText(job.location)}</strong></div>
      <div><span>Job Type</span> <strong>${safeText(job.job_type)}</strong></div>
      <div><span>Salary</span> <strong>${safeText(job.salary)}</strong></div>
      <div><span>Experience</span> <strong>${safeText(job.experience)}</strong></div>
      <div><span>Applicants</span> <strong>${safeText(job.applicants ?? 0, '0')}</strong></div>
      <div><span>Verification</span> <strong>${safeText(job.verification)}</strong></div>
    </div>
  </div>
  <div class="details-card">
    <h6>Recruiter Details</h6>
    <div class="details-list">
      <div><span>Company</span> <strong>${safeText(job.company)}</strong></div>
      <div><span>Name</span> <strong>${safeText(job.recruiter_name)}</strong></div>
      <div><span>Email</span> <strong>${safeText(job.recruiter_email)}</strong></div>
      <div><span>Phone</span> <strong>${safeText(job.recruiter_phone)}</strong></div>
      <div><span>Posted Date</span> <strong>${safeText(job.posted_date)}</strong></div>
      <div><span>Featured</span> <strong>${job.featured ? 'Yes' : 'No'}</strong></div>
    </div>
  </div>
  <div class="details-card" style="grid-column: 1 / -1;">
    <h6>Job Content</h6>
    <div class="details-list">
      <div><span>Description</span> <strong>${safeMultilineText(job.description)}</strong></div>
      <div><span>Requirements</span> <strong>${safeMultilineText(job.requirements)}</strong></div>
      <div><span>Skills</span> <strong>${safeText(job.skills)}</strong></div>
    </div>
  </div>
</div>
<div class="view-actions">
  <button class="btn ghost" data-view-action="approve">Approve</button>
  <button class="btn ghost" data-view-action="reject">Reject</button>
  <button class="btn ghost" data-view-action="report">Mark Reported</button>
  <button class="btn primary" data-view-action="feature">${job.featured ? 'Remove Featured' : 'Mark as Featured'}</button>
</div>
`;
  };

  const toFormData = (payload) => {
    const formData = new FormData();
    Object.entries(payload).forEach(([key, value]) => {
      if (key === 'id') return;
      if (key === 'featured') {
        if (value) formData.append('featured', 'true');
        return;
      }
      formData.append(key, value ?? '');
    });
    return formData;
  };

  const updateJob = async (job) => {
    if (useApi) {
      const formData = toFormData(job);
      const data = await fetchJson(`/api/jobs/${encodeURIComponent(job.id)}/update/`, {
        method: 'POST',
        headers: { 'X-CSRFToken': getCookie('csrftoken') },
        body: formData,
      });
      if (data && data.success) {
        updateLocalJob(data.item);
        await refreshData(true);
        return true;
      }
      useApi = false;
      showToast(data.error || 'Server error. Switching to local data.', 'danger');
    }

    const index = localJobs.findIndex((item) => item.id === job.id);
    if (index >= 0) {
      localJobs[index] = { ...localJobs[index], ...job };
      saveLocalJobs(localJobs);
      renderLocalTable();
      return true;
    }
    return false;
  };

  const deleteJob = async (id) => {
    if (useApi) {
      const data = await fetchJson(`/api/jobs/${encodeURIComponent(id)}/delete/`, {
        method: 'POST',
        headers: { 'X-CSRFToken': getCookie('csrftoken') },
      });
      if (data && data.success) {
        removeLocalJob(id);
        await refreshData(true);
        return true;
      }
      useApi = false;
      showToast(data.error || 'Server error. Switching to local data.', 'danger');
    }

    localJobs = localJobs.filter((item) => item.id !== id);
    saveLocalJobs(localJobs);
    renderLocalTable();
    return true;
  };

  const createJob = async (payload) => {
    if (useApi) {
      const formData = toFormData(payload);
      const data = await fetchJson('/api/jobs/create/', {
        method: 'POST',
        headers: { 'X-CSRFToken': getCookie('csrftoken') },
        body: formData,
      });
      if (data && data.success) {
        updateLocalJob(data.item);
        await refreshData(true);
        return true;
      }
      useApi = false;
      showToast(data.error || 'Server error. Switching to local data.', 'danger');
    }

    const nextId = `JOB-${Math.max(1000, localJobs.length + 1000 + Math.floor(Math.random() * 50))}`;
    payload.id = nextId;
    localJobs.unshift(payload);
    saveLocalJobs(localJobs);
    renderLocalTable();
    return true;
  };

  const openViewModal = (id) => {
    const job = jobs.find((item) => item.id === id) || localJobs.find((item) => item.id === id);
    if (!job || !viewContent) return;
    viewContent.innerHTML = buildViewHtml(job);
    const actionButtons = viewContent.querySelectorAll('[data-view-action]');
    actionButtons.forEach((btn) => {
      btn.addEventListener('click', async () => {
        const action = btn.dataset.viewAction;
        if (action === 'approve') job.status = 'Approved';
        if (action === 'reject') job.status = 'Rejected';
        if (action === 'report') job.status = 'Reported';
        if (action === 'feature') job.featured = !job.featured;
        const saved = await updateJob(job);
        if (saved) {
          showToast('Job updated', 'success');
          if (viewModal) viewModal.hide();
        }
      });
    });
    if (viewModal) {
      viewModal.show();
      return;
    }
    showToast('Details modal is unavailable. Refresh page and try again.', 'danger');
  };

  const openEditModal = (id) => {
    const job = jobs.find((item) => item.id === id) || localJobs.find((item) => item.id === id);
    if (!job) return;
    if (jobIdInput) jobIdInput.value = job.id;
    if (formTitle) formTitle.textContent = `Edit ${job.title}`;
    fillForm(job);
    if (formModal) {
      formModal.show();
      return;
    }
    showToast('Edit form modal is unavailable. Refresh page and try again.', 'danger');
  };

  const bindRowEvents = () => {
    const actionButtons = document.querySelectorAll('[data-action]');
    actionButtons.forEach((btn) => {
      btn.addEventListener('click', () => {
        const action = btn.dataset.action;
        const id = btn.dataset.id;
        if (action === 'view') {
          openViewModal(id);
        }
        if (action === 'edit') {
          openEditModal(id);
        }
        if (action === 'delete') {
          if (!canDelete) {
            showToast('Delete action is disabled for subadmin.', 'warning');
            return;
          }
          deleteTarget = id;
          if (deleteModal) {
            deleteModal.show();
            return;
          }
          showToast('Delete confirmation modal is unavailable. Refresh page and try again.', 'danger');
        }
      });
    });
  };

  const handleFormSubmit = async (event) => {
    event.preventDefault();
    if (!jobForm) return;
    const formData = new FormData(jobForm);
    const payload = {
      id: formData.get('job_id') || '',
      title: formData.get('title') || '',
      category: formData.get('category') || '',
      location: formData.get('location') || '',
      job_type: formData.get('job_type') || 'Full-time',
      salary: formData.get('salary') || '',
      experience: formData.get('experience') || '',
      skills: formData.get('skills') || '',
      posted_date: formData.get('posted_date') || new Date().toISOString().slice(0, 10),
      status: formData.get('status') || 'Pending',
      applicants: Number(formData.get('applicants') || 0),
      verification: formData.get('verification') || 'Pending',
      featured: Boolean(formData.get('featured')),
      company: formData.get('company') || '',
      recruiter_name: formData.get('recruiter_name') || '',
      recruiter_email: formData.get('recruiter_email') || '',
      recruiter_phone: formData.get('recruiter_phone') || '',
      description: formData.get('description') || '',
      requirements: formData.get('requirements') || '',
    };

    if (payload.id) {
      const saved = await updateJob(payload);
      if (saved) showToast('Job updated successfully', 'success');
    } else {
      const saved = await createJob(payload);
      if (saved) showToast('Job created successfully', 'success');
    }

    jobForm.reset();
    if (jobIdInput) jobIdInput.value = '';
    if (formModal) formModal.hide();
  };

  const handleDelete = async () => {
    if (!canDelete) {
      showToast('Delete action is disabled for subadmin.', 'warning');
      return;
    }
    if (!deleteTarget) return;
    await deleteJob(deleteTarget);
    deleteTarget = null;
    showToast('Job deleted', 'warning');
    if (deleteModal) deleteModal.hide();
  };

  const exportCsv = () => {
    if (useApi) {
      const params = buildListParams(1);
      window.location.href = `/api/jobs/export/?${params.toString()}`;
      return;
    }

    const rows = getFilteredJobs();
    if (!rows.length) {
      showToast('No data to export', 'warning');
      return;
    }
    const header = ['Job ID', 'Title', 'Company', 'Category', 'Location', 'Status', 'Posted Date', 'Applicants'];
    const csv = [header.join(',')]
      .concat(
        rows.map((job) =>
          [
            job.id,
            job.title,
            job.company,
            job.category,
            job.location,
            job.status,
            job.posted_date,
            job.applicants,
          ]
            .map((value) => `"${String(value).replace(/"/g, '""')}"`)
            .join(',')
        )
      )
      .join('\n');

    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'jobs.csv';
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

  if (jobForm) {
    jobForm.addEventListener('submit', handleFormSubmit);
  }

  if (addBtn && jobForm) {
    addBtn.addEventListener('click', () => {
      jobForm.reset();
      if (jobIdInput) jobIdInput.value = '';
      if (formTitle) formTitle.textContent = 'Add Job';
      if (formModal) {
        formModal.show();
        return;
      }
      showToast('Job form modal is unavailable. Refresh page and try again.', 'danger');
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

  window.addEventListener('storage', (event) => {
    if (event.key === STORAGE_KEY && !useApi) {
      localJobs = loadLocalJobs();
      renderLocalTable();
    }
  });

  initStatusFilter();
  refreshData();

  setInterval(() => {
    if (document.hidden) return;
    if (document.querySelector('.modal.show')) return;
    refreshData(true);
  }, pollInterval);
})();
