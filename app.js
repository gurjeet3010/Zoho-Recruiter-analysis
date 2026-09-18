// CEO Hiring Dashboard Logic
// Current Date Reference: 2026-06-29

// Global charts references to allow updates
let globalPipelineChart = null;
let globalSourceChart = null;
let modalSourceChart = null;

// DOM Cache to avoid querying the DOM multiple times
const domCache = {};
function getDom(id) {
  if (!domCache[id]) {
    domCache[id] = document.getElementById(id);
  }
  return domCache[id];
}

// Application State
let state = {
  jobs: [], // Initially empty, populated from server API
  filteredJobs: [],
  filters: {
    search: '',
    company: 'all',
    status: 'all',
    recruiter: 'all'
  },
  sortBy: {
    field: 'daysOpen',
    direction: 'desc'
  }
};

// Initialize Application
document.addEventListener('DOMContentLoaded', () => {
  fetchJobs();
  setupEventListeners();
});

// Setup dynamic options in filter dropdowns
function setupFilterDropdowns() {
  const companies = [...new Set(state.jobs.map(j => j.companyName))];

  const companySelect = document.getElementById('company-filter');

  // Clear existing options except "All"
  companySelect.innerHTML = '<option value="all">All Companies</option>';

  companies.forEach(company => {
    const opt = document.createElement('option');
    opt.value = company;
    opt.textContent = company;
    companySelect.appendChild(opt);
  });
}

// Perform filters & sort and update UI elements
function renderDashboard() {
  applyFilters();
  applySorting();
  
  // Calculate aggregate metrics for filtered data
  const metrics = getSummaryMetrics(state.filteredJobs);
  
  // Populate KPI Cards
  updateKPICards(metrics);
  
  // Render visual charts
  renderAggregateCharts(metrics);
  
  // Render jobs table
  renderJobsTable();
}

// Apply searches and filter dropdown options to data
function applyFilters() {
  state.filteredJobs = state.jobs.filter(job => {
    // Search filter
    const matchesSearch = 
      job.jobTitle.toLowerCase().includes(state.filters.search.toLowerCase()) ||
      job.companyName.toLowerCase().includes(state.filters.search.toLowerCase()) ||
      job.recruiter.toLowerCase().includes(state.filters.search.toLowerCase());

    // Company filter
    const matchesCompany = state.filters.company === 'all' || job.companyName === state.filters.company;

    // Status filter
    const matchesStatus = state.filters.status === 'all' || job.status === state.filters.status;

    return matchesSearch && matchesCompany && matchesStatus;
  });
}

// Sort jobs table data
function applySorting() {
  const { field, direction } = state.sortBy;
  const isAsc = direction === 'asc';
  
  state.filteredJobs.sort((a, b) => {
    let valA = a[field];
    let valB = b[field];
    
    // Handle string values for case-insensitive sort
    if (typeof valA === 'string') {
      valA = valA.toLowerCase();
      valB = valB.toLowerCase();
    }
    
    if (valA < valB) return isAsc ? -1 : 1;
    if (valA > valB) return isAsc ? 1 : -1;
    return 0;
  });
}

// Populate KPI elements with calculated values
function updateKPICards(metrics) {
  if (state.globalMetrics) {
    // 1. Active Jobs
    getDom('val-active-jobs').textContent = state.globalMetrics.activeJobs;
    // 2. Applicants
    getDom('val-applicants').textContent = state.globalMetrics.applicants;
    
    // 3. Interviews
    const intMetrics = state.globalMetrics.interviews || { total: 0, completed: 0, cancelled: 0, pending: 0 };
    getDom('val-interviews-total').textContent = intMetrics.total;
    getDom('val-interviews-completed').textContent = intMetrics.completed;
    getDom('val-interviews-cancelled').textContent = intMetrics.cancelled;
    getDom('val-interviews-pending').textContent = intMetrics.pending;
    
    // 4. Submissions
    getDom('val-submissions').textContent = state.globalMetrics.submissions || 0;
    
    // 5. Offers
    const offMetrics = state.globalMetrics.offers || { total: 0, accepted: 0, declined: 0, pending: 0 };
    getDom('val-offers-total').textContent = offMetrics.total;
    getDom('val-offers-accepted').textContent = offMetrics.accepted;
    getDom('val-offers-declined').textContent = offMetrics.declined;
    getDom('val-offers-pending').textContent = offMetrics.pending;
    
    // 6. Hires
    getDom('val-hires').textContent = state.globalMetrics.hires;
  } else {
    // Fallback/Demo calculations based on currently loaded jobs list
    const activeJobsCount = state.filteredJobs.length;
    const totalApplicants = state.filteredJobs.reduce((sum, j) => {
      const jobApplied = (j.sources.naukri || 0) + (j.sources.linkedin || 0) + (j.sources.referral || 0) + (j.sources.website || 0);
      return sum + jobApplied;
    }, 0);
    
    const totalInterviews = state.filteredJobs.reduce((sum, j) => sum + (j.pipeline.interview || 0), 0);
    const interviewsCompleted = Math.round(totalInterviews * 0.1);
    const interviewsCancelled = Math.round(totalInterviews * 0.3);
    const interviewsPending = totalInterviews - interviewsCompleted - interviewsCancelled;
    
    const totalSubmissions = 0;
    
    const totalOffers = state.filteredJobs.reduce((sum, j) => sum + (j.pipeline.offered || 0), 0);
    const offersAccepted = Math.round(totalOffers * 0.6);
    const offersDeclined = Math.round(totalOffers * 0.3);
    const offersPending = totalOffers - offersAccepted - offersDeclined;
    
    const totalHired = state.filteredJobs.reduce((sum, j) => sum + (j.pipeline.hired || 0), 0);
    
    // Populate
    getDom('val-active-jobs').textContent = activeJobsCount;
    getDom('val-applicants').textContent = totalApplicants;
    
    getDom('val-interviews-total').textContent = totalInterviews;
    getDom('val-interviews-completed').textContent = interviewsCompleted;
    getDom('val-interviews-cancelled').textContent = interviewsCancelled;
    getDom('val-interviews-pending').textContent = interviewsPending;
    
    getDom('val-submissions').textContent = totalSubmissions;
    
    getDom('val-offers-total').textContent = totalOffers;
    getDom('val-offers-accepted').textContent = offersAccepted;
    getDom('val-offers-declined').textContent = offersDeclined;
    getDom('val-offers-pending').textContent = offersPending;
    
    getDom('val-hires').textContent = totalHired;
  }
}

// Render chart.js visualizations
function renderAggregateCharts(metrics) {
  // 1. Pipeline Funnel Chart (Horizontal Bar Chart representation)
  const pipelineCtx = document.getElementById('pipelineChart').getContext('2d');
  
  const pipelineData = [
    metrics.pipelineTotals.screening + metrics.pipelineTotals.interview + metrics.pipelineTotals.offered + metrics.pipelineTotals.hired + metrics.pipelineTotals.rejected, // Approximated Total Applied
    metrics.pipelineTotals.screening,
    metrics.pipelineTotals.interview,
    metrics.pipelineTotals.offered,
    metrics.pipelineTotals.hired
  ];

  if (globalPipelineChart) {
    globalPipelineChart.data.datasets[0].data = pipelineData;
    globalPipelineChart.update();
  } else {
    globalPipelineChart = new Chart(pipelineCtx, {
      type: 'bar',
      data: {
        labels: ['Applied (Total Sourced)', 'Screening', 'Interview', 'Offered', 'Hired (Closed)'],
        datasets: [{
          label: 'Candidates',
          data: pipelineData,
          backgroundColor: [
            'rgba(59, 130, 246, 0.7)',  // Blue
            'rgba(139, 92, 246, 0.7)', // Purple
            'rgba(245, 158, 11, 0.7)',  // Orange
            'rgba(234, 179, 8, 0.7)',   // Yellow
            'rgba(16, 185, 129, 0.7)'   // Green
          ],
          borderColor: [
            '#3b82f6',
            '#8b5cf6',
            '#f59e0b',
            '#eab308',
            '#10b981'
          ],
          borderWidth: 1.5,
          borderRadius: 6,
          barPercentage: 0.6
        }]
      },
      options: {
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: (context) => {
                const val = context.raw;
                const total = pipelineData[0];
                const pct = total > 0 ? ((val / total) * 100).toFixed(1) : 0;
                return ` Candidates: ${val} (${pct}% of total sourced)`;
              }
            }
          }
        },
        scales: {
          x: {
            grid: { color: '#e2e8f0' },
            ticks: { color: '#64748b', font: { family: 'Inter' } }
          },
          y: {
            grid: { display: false },
            ticks: { color: '#0f172a', font: { family: 'Outfit', weight: '600' } }
          }
        }
      }
    });
  }

  // 2. Application Channels Chart (Doughnut Chart)
  const sourceCtx = document.getElementById('sourceChart').getContext('2d');
  const sourceData = [
    metrics.sourceTotals.linkedin,
    metrics.sourceTotals.referral,
    metrics.sourceTotals.website
  ];

  if (globalSourceChart) {
    globalSourceChart.data.datasets[0].data = sourceData;
    globalSourceChart.update();
  } else {
    globalSourceChart = new Chart(sourceCtx, {
      type: 'doughnut',
      data: {
        labels: ['LinkedIn', 'Referral', 'Website'],
        datasets: [{
          data: sourceData,
          backgroundColor: ['#7c3aed', '#059669', '#ea580c'],
          borderColor: '#ffffff',
          borderWidth: 2,
          hoverOffset: 8
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'bottom',
            labels: {
              color: '#64748b',
              font: { family: 'Inter', size: 11 },
              padding: 15
            }
          },
          tooltip: {
            callbacks: {
              label: (context) => {
                const val = context.raw;
                const sum = sourceData.reduce((a, b) => a + b, 0);
                const pct = sum > 0 ? ((val / sum) * 100).toFixed(1) : 0;
                return ` ${context.label}: ${val} (${pct}%)`;
              }
            }
          }
        },
        cutout: '65%'
      }
    });
  }
}

// Formatting helpers for cleaner table representation
function formatTargetDate(dateStr) {
  if (!dateStr) return 'N/A';
  try {
    const parts = dateStr.split('-');
    if (parts.length !== 3) return dateStr;
    const date = new Date(parts[0], parts[1] - 1, parts[2]);
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    return `${parts[2]} ${months[parseInt(parts[1], 10) - 1]} ${parts[0]}`;
  } catch {
    return dateStr;
  }
}

function getDaysOpenStyle(days) {
  if (days <= 15) {
    return `color: var(--accent-green); background-color: rgba(5, 150, 105, 0.06); padding: 4px 8px; border-radius: 6px; font-weight: 600; font-size: 11px; display: inline-block;`;
  } else if (days <= 30) {
    return `color: var(--accent-orange); background-color: rgba(234, 88, 12, 0.06); padding: 4px 8px; border-radius: 6px; font-weight: 600; font-size: 11px; display: inline-block;`;
  } else {
    return `color: var(--accent-red); background-color: rgba(220, 38, 38, 0.06); padding: 4px 8px; border-radius: 6px; font-weight: 700; font-size: 11px; display: inline-block; border: 1px solid rgba(220, 38, 38, 0.1);`;
  }
}

function getRecruiterHTML(name) {
  const initials = name ? name.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase() : 'AG';
  const colors = [
    { bg: 'rgba(37, 99, 235, 0.08)', text: 'var(--accent-blue)' },
    { bg: 'rgba(124, 58, 237, 0.08)', text: 'var(--accent-purple)' },
    { bg: 'rgba(5, 150, 105, 0.08)', text: 'var(--accent-green)' },
    { bg: 'rgba(234, 88, 12, 0.08)', text: 'var(--accent-orange)' }
  ];
  const color = colors[initials.charCodeAt(0) % colors.length];
  
  return `
    <div class="recruiter-pill" style="display: flex; align-items: center; gap: 8px;">
      <span class="avatar-circle" style="display: inline-flex; align-items: center; justify-content: center; width: 26px; height: 26px; border-radius: 50%; font-size: 10px; font-weight: 700; background-color: ${color.bg}; color: ${color.text}; text-transform: uppercase;">${initials}</span>
      <span class="recruiter-name" style="font-weight: 500; font-size: 12px; color: var(--text-main);">${name}</span>
    </div>
  `;
}

// Render dynamic Jobs Table rows
function renderJobsTable() {
  const tbody = document.getElementById('jobs-table-body');
  tbody.innerHTML = '';
  
  document.getElementById('jobs-shown-count').textContent = `${state.filteredJobs.length} openings shown`;

  if (state.filteredJobs.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="7" style="text-align: center; padding: 40px; color: var(--text-muted);">
          <i class="fa-regular fa-folder-open" style="font-size: 24px; margin-bottom: 8px; display: block;"></i>
          No job openings matching selected filters.
        </td>
      </tr>
    `;
    return;
  }

  state.filteredJobs.forEach(job => {
    const tr = document.createElement('tr');
    tr.dataset.id = job.id;
    
    // Calculate total applications for the specific job
    const jobTotalApplied = (job.sources.linkedin || 0) + (job.sources.referral || 0) + (job.sources.website || 0);
    
    // Calculate percentage widths for stacked source bar
    const lnPct = jobTotalApplied > 0 ? ((job.sources.linkedin || 0) / jobTotalApplied) * 100 : 0;
    const refPct = jobTotalApplied > 0 ? ((job.sources.referral || 0) / jobTotalApplied) * 100 : 0;
    const webPct = jobTotalApplied > 0 ? ((job.sources.website || 0) / jobTotalApplied) * 100 : 0;

    // Check status design classes
    const statusBadgeHTML = job.status === 'Delayed' 
      ? `<span class="badge" style="background-color: rgba(220, 38, 38, 0.06); color: var(--accent-red); border: 1px solid rgba(220, 38, 38, 0.15); padding: 4px 8px; border-radius: 6px; font-size: 11px; font-weight: 600; display: inline-flex; align-items: center; gap: 4px;"><i class="fa-solid fa-circle-exclamation"></i> Delayed</span>`
      : `<span class="badge" style="background-color: rgba(5, 150, 105, 0.06); color: var(--accent-green); border: 1px solid rgba(5, 150, 105, 0.15); padding: 4px 8px; border-radius: 6px; font-size: 11px; font-weight: 600; display: inline-flex; align-items: center; gap: 4px;"><i class="fa-solid fa-circle-check"></i> On Track</span>`;

    const positionsHTML = `<span class="positions-badge" style="background-color: var(--bg-app); border: 1px solid var(--border-color); padding: 4px 8px; border-radius: 6px; font-weight: 600; font-size: 12px; color: var(--text-main); display: inline-block;">${job.totalPositions} ${job.totalPositions === 1 ? 'role' : 'roles'}</span>`;

    tr.innerHTML = `
      <td data-label="Job Openings">
        <div class="job-title-col">
          <span class="job-role-name">${job.jobTitle}</span>
          <span class="job-company">${job.companyName} • <span style="font-size:10px; color:#64748b">${job.jobCode}</span></span>
        </div>
      </td>
      <td data-label="Positions">${positionsHTML}</td>
      <td data-label="Target Date"><span style="font-weight: 500; font-size: 12px; color: var(--text-main);">${formatTargetDate(job.targetHireDate)}</span></td>
      <td data-label="Days Open">
        <span style="${getDaysOpenStyle(job.daysOpen)}">
          ${job.daysOpen > 30 ? '<i class="fa-solid fa-clock-rotate-left" style="margin-right: 3px;"></i> ' : ''}${job.daysOpen} days
        </span>
      </td>
      <td data-label="Sources Split">
        <div class="source-bar-wrapper">
          <div class="source-bar-labels">
            <span>Total Applied</span>
            <span class="source-bar-count">${jobTotalApplied}</span>
          </div>
          <div class="source-stacked-bar" title="LinkedIn: ${job.sources.linkedin || 0} | Referral: ${job.sources.referral || 0} | Website: ${job.sources.website || 0}">
            <div class="bar-segment seg-linkedin" style="width: ${lnPct}%"></div>
            <div class="bar-segment seg-referral" style="width: ${refPct}%"></div>
            <div class="bar-segment seg-website" style="width: ${webPct}%"></div>
          </div>
          <div class="source-legend-tooltip">
            <span class="dot-linkedin">${job.sources.linkedin || 0}</span>
            <span class="dot-referral">${job.sources.referral || 0}</span>
            <span class="dot-website">${job.sources.website || 0}</span>
          </div>
        </div>
      </td>
      <td data-label="Hiring Pipeline">
        <div class="pipeline-flow">
          <span class="flow-step ${job.pipeline.screening > 0 ? 'active-step' : ''}" title="Screening"><strong>${job.pipeline.screening}</strong> SCR</span>
          <span class="flow-separator">➔</span>
          <span class="flow-step ${job.pipeline.interview > 0 ? 'active-step' : ''}" title="Interview"><strong>${job.pipeline.interview}</strong> INT</span>
          <span class="flow-separator">➔</span>
          <span class="flow-step ${job.pipeline.offered > 0 ? 'active-step' : ''}" title="Offered"><strong>${job.pipeline.offered}</strong> OFF</span>
          <span class="flow-separator">➔</span>
          <span class="flow-step hired-step ${job.pipeline.hired > 0 ? 'active-step' : ''}" title="Hired"><strong>${job.pipeline.hired}</strong> HRD</span>
          <span class="flow-separator">➔</span>
          <span class="flow-step rejected-step ${job.pipeline.rejected > 0 ? 'active-step' : ''}" title="Rejected"><strong>${job.pipeline.rejected || 0}</strong> REJ</span>
          <span class="flow-separator">➔</span>
          <span class="flow-step archived-step ${(job.pipeline.archived || 0) > 0 ? 'active-step' : ''}" title="Archived"><strong>${job.pipeline.archived || 0}</strong> ARC</span>
        </div>
      </td>
      <td data-label="Track Status">
        ${statusBadgeHTML}
      </td>
    `;
    
    // Attach click listener for detailing modal
    tr.addEventListener('click', () => openJobModal(job.id));
    tbody.appendChild(tr);
  });
}

// Open Detail Modal for Selected Job
function openJobModal(jobId) {
  const job = state.jobs.find(j => j.id === jobId);
  if (!job) return;

  // Map elements
  document.getElementById('modal-job-id').textContent = job.jobCode;
  document.getElementById('modal-job-title').textContent = job.jobTitle;
  document.getElementById('modal-company-name').textContent = job.companyName;
  document.getElementById('modal-dept').textContent = job.department;
  document.getElementById('modal-positions').textContent = job.totalPositions;
  document.getElementById('modal-target-date').textContent = job.targetHireDate;
  document.getElementById('modal-days-open').textContent = `${job.daysOpen} days`;
  
  // Status Badge in modal
  const mStatus = document.getElementById('modal-status-badge');
  mStatus.textContent = job.status;
  mStatus.className = `badge ${job.status === 'Delayed' ? 'badge-delayed' : 'badge-track'}`;
  
  document.getElementById('modal-recruiter').textContent = job.recruiter;

  // Pipeline Counts
  const totalApplied = (job.sources.linkedin || 0) + (job.sources.referral || 0) + (job.sources.website || 0);
  document.getElementById('m-stage-applied').textContent = totalApplied;
  document.getElementById('m-stage-screening').textContent = job.pipeline.screening;
  document.getElementById('m-stage-interview').textContent = job.pipeline.interview;
  document.getElementById('m-stage-offered').textContent = job.pipeline.offered;
  document.getElementById('m-stage-hired').textContent = job.pipeline.hired;
  document.getElementById('m-stage-rejected').textContent = job.pipeline.rejected || 0;
  document.getElementById('m-stage-archived').textContent = job.pipeline.archived || 0;

  // Calculate widths for visual funnel stages
  const scrWidth = totalApplied > 0 ? (job.pipeline.screening / totalApplied) * 100 : 0;
  const intWidth = totalApplied > 0 ? (job.pipeline.interview / totalApplied) * 100 : 0;
  const offWidth = totalApplied > 0 ? (job.pipeline.offered / totalApplied) * 100 : 0;
  const hrdWidth = totalApplied > 0 ? (job.pipeline.hired / totalApplied) * 100 : 0;
  const rejWidth = totalApplied > 0 ? ((job.pipeline.rejected || 0) / totalApplied) * 100 : 0;
  const arcWidth = totalApplied > 0 ? ((job.pipeline.archived || 0) / totalApplied) * 100 : 0;

  document.getElementById('m-bar-screening').style.width = `${scrWidth}%`;
  document.getElementById('m-bar-interview').style.width = `${intWidth}%`;
  document.getElementById('m-bar-offered').style.width = `${offWidth}%`;
  document.getElementById('m-bar-hired').style.width = `${hrdWidth}%`;
  document.getElementById('m-bar-rejected').style.width = `${rejWidth}%`;
  document.getElementById('m-bar-archived').style.width = `${arcWidth}%`;



  // Draw or update the modal source split chart
  const modalSourceCtx = document.getElementById('modalSourceChart').getContext('2d');
  const mSourceData = [
    job.sources.linkedin || 0,
    job.sources.referral || 0,
    job.sources.website || 0
  ];

  if (modalSourceChart) {
    modalSourceChart.data.datasets[0].data = mSourceData;
    modalSourceChart.update();
  } else {
    modalSourceChart = new Chart(modalSourceCtx, {
      type: 'bar',
      data: {
        labels: ['LinkedIn', 'Referral', 'Website'],
        datasets: [{
          label: 'Applications',
          data: mSourceData,
          backgroundColor: ['#8b5cf6', '#10b981', '#f59e0b'],
          borderRadius: 4
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { grid: { display: false }, ticks: { color: '#64748b' } },
          y: { grid: { color: '#e2e8f0' }, ticks: { color: '#64748b' } }
        }
      }
    });
  }

  // Open the Modal
  document.getElementById('job-modal').classList.add('active');
}

// Close Detail Modal Dialog
function closeJobModal() {
  document.getElementById('job-modal').classList.remove('active');
}

// Wire events
function setupEventListeners() {
  // Search keyup
  document.getElementById('search-input').addEventListener('keyup', (e) => {
    state.filters.search = e.target.value;
    renderDashboard();
  });

  // Company change
  document.getElementById('company-filter').addEventListener('change', (e) => {
    state.filters.company = e.target.value;
    renderDashboard();
  });

  // Status change
  document.getElementById('status-filter').addEventListener('change', (e) => {
    state.filters.status = e.target.value;
    renderDashboard();
  });

  // Clear filters
  document.getElementById('clear-filters-btn').addEventListener('click', () => {
    document.getElementById('search-input').value = '';
    document.getElementById('company-filter').value = 'all';
    document.getElementById('status-filter').value = 'all';
    
    state.filters = { search: '', company: 'all', status: 'all', recruiter: 'all' };
    renderDashboard();
  });

  // Refresh button
  document.getElementById('refresh-btn').addEventListener('click', () => {
    const btn = document.getElementById('refresh-btn');
    btn.innerHTML = '<i class="fa-solid fa-arrows-rotate fa-spin"></i> Refreshing...';
    btn.disabled = true;
    
    fetchJobs().finally(() => {
      btn.innerHTML = '<i class="fa-solid fa-arrows-rotate"></i> Refresh';
      btn.disabled = false;
    });
  });

  // Modal Close buttons
  document.getElementById('modal-close-btn').addEventListener('click', closeJobModal);
  
  // Close modal when clicking outside content area
  document.getElementById('job-modal').addEventListener('click', (e) => {
    if (e.target.id === 'job-modal') {
      closeJobModal();
    }
  });

  // Column sorting configuration
  const headers = document.querySelectorAll('.jobs-table th.sortable');
  headers.forEach(header => {
    header.addEventListener('click', () => {
      const field = header.dataset.sort;
      const currentDir = state.sortBy.direction;
      
      // If we are clicking same header, toggle direction, otherwise default to desc
      const newDir = (state.sortBy.field === field && currentDir === 'desc') ? 'asc' : 'desc';
      
      state.sortBy = { field, direction: newDir };
      
      // Update UI Header icons
      headers.forEach(h => {
        const icon = h.querySelector('i');
        icon.className = 'fa-solid fa-sort';
      });
      
      const activeIcon = header.querySelector('i');
      activeIcon.className = `fa-solid fa-sort-${newDir === 'asc' ? 'up' : 'down'}`;
      
      renderDashboard();
    });
  });

  // Auth button click listeners to trigger Zoho OAuth flow redirect
  document.getElementById('auth-btn').addEventListener('click', () => {
    window.location.href = '/api/auth';
  });
  document.getElementById('banner-auth-btn').addEventListener('click', () => {
    window.location.href = '/api/auth';
  });
}

// Fetch live jobs data from Python OAuth proxy backend
function fetchJobs() {
  const banner = document.getElementById('connection-banner');
  const bannerText = document.getElementById('banner-text');
  const bannerAuthBtn = document.getElementById('banner-auth-btn');
  const headerAuthBtn = document.getElementById('auth-btn');

  return fetch('/api/jobs')
    .then(res => res.json())
    .then(data => {
      state.jobs = data.jobs || [];
      state.filteredJobs = [...state.jobs];
      state.globalMetrics = data.globalMetrics; // Save Zoho Org Overview metrics
      
      setupFilterDropdowns();
      renderDashboard();

      banner.style.display = 'flex';
      if (data.status === 'live') {
        banner.className = 'status-banner banner-live';
        bannerText.innerHTML = '<i class="fa-solid fa-circle-check"></i> Live connection active: Synchronized with your Zoho Recruit account.';
        bannerAuthBtn.style.display = 'none';
        headerAuthBtn.style.display = 'none';
      } else if (data.status === 'empty_live') {
        banner.className = 'status-banner banner-live';
        bannerText.innerHTML = '<i class="fa-solid fa-circle-info"></i> Connected to Zoho: No records found in your Zoho Recruit account. Showing demo data.';
        bannerAuthBtn.style.display = 'none';
        headerAuthBtn.style.display = 'none';
      } else {
        // Fallback or demo mode
        banner.className = 'status-banner banner-demo';
        bannerText.innerHTML = `<i class="fa-solid fa-triangle-exclamation"></i> ${data.message || 'Demo Mode: Displaying sample datasets. Connect your Zoho Recruit account for real-time tracking.'}`;
        bannerAuthBtn.style.display = 'inline-block';
        headerAuthBtn.style.display = 'inline-block';

        // Auto-poll if Zoho background sync is active
        if (data.message && data.message.includes("Syncing")) {
          bannerAuthBtn.style.display = 'none';
          setTimeout(fetchJobs, 3000);
        }
      }
      return data;
    })
    .catch(err => {
      console.error("Failed to fetch jobs from backend server API:", err);
      banner.style.display = 'flex';
      banner.className = 'status-banner banner-demo';
      bannerText.innerHTML = '<i class="fa-solid fa-triangle-exclamation"></i> Offline: Could not communicate with API proxy server. Showing cached demo data.';
      bannerAuthBtn.style.display = 'inline-block';
      headerAuthBtn.style.display = 'inline-block';
      
      // Attempt absolute fallback using standard data.js variable if available
      if (typeof jobOpeningsData !== 'undefined') {
        state.jobs = [...jobOpeningsData];
        state.filteredJobs = [...state.jobs];
        setupFilterDropdowns();
        renderDashboard();
      }
    });
}
