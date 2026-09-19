// WeAutomate Dashboard Frontend Controller

const API_BASE = '/api/v1';

let currentVms = [];
let metricsData = null;

// DOM Elements
const elAllocatedCores = document.getElementById('val-allocated-cores');
const elTotalCores = document.getElementById('val-total-cores');
const elAvailableCores = document.getElementById('val-available-cores');
const elGaugeFill = document.getElementById('gauge-bar-fill');
const elGaugePct = document.getElementById('gauge-percentage');

const elCountRunning = document.getElementById('count-running');
const elCountStopped = document.getElementById('count-stopped');
const elCountStopping = document.getElementById('count-stopping');
const elCountUnreachable = document.getElementById('count-unreachable');
const elActiveVmsCount = document.getElementById('active-vms-count');

const elVmsTableBody = document.getElementById('vms-table-body');
const elVmSearch = document.getElementById('vm-search');
const elBtnRefresh = document.getElementById('btn-refresh');
const elBtnReconcileNow = document.getElementById('btn-reconcile-now');
const elAuditTimeline = document.getElementById('audit-timeline');
const elAuditTotalCount = document.getElementById('audit-total-count');

// Modal Elements
const elModalStart = document.getElementById('modal-start');
const elBtnStartModal = document.getElementById('btn-start-modal');
const elModalClose = document.getElementById('modal-close');
const elModalCancel = document.getElementById('modal-cancel-btn');
const elSelectStartVm = document.getElementById('select-start-vm');
const elInputCores = document.getElementById('input-cores');
const elPreviewCapacity = document.getElementById('preview-capacity');
const elModalStartAlert = document.getElementById('modal-start-alert');
const elBtnConfirmStart = document.getElementById('modal-confirm-start-btn');

const elTriadCtrlVal = document.getElementById('triad-ctrl-val');
const elTriadHypVal = document.getElementById('triad-hyp-val');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
  fetchAllData();
  setupEventListeners();
  // Auto-refresh every 10 seconds
  setInterval(fetchAllData, 10000);
});

function setupEventListeners() {
  elBtnRefresh.addEventListener('click', () => {
    elBtnRefresh.style.transform = 'rotate(180deg)';
    setTimeout(() => { elBtnRefresh.style.transform = ''; }, 300);
    fetchAllData();
  });

  elVmSearch.addEventListener('input', renderVmsTable);

  elBtnReconcileNow.addEventListener('click', triggerReconciliation);

  // Modal Open/Close
  elBtnStartModal.addEventListener('click', () => {
    populateModalVms();
    elModalStart.classList.remove('hidden');
  });

  elModalClose.addEventListener('click', () => elModalStart.classList.add('hidden'));
  elModalCancel.addEventListener('click', () => elModalStart.classList.add('hidden'));

  elSelectStartVm.addEventListener('change', updateStartCapacityPreview);
  elInputCores.addEventListener('input', updateStartCapacityPreview);
  elBtnConfirmStart.addEventListener('click', handleAuthorizeStart);
}

async function fetchAllData() {
  await Promise.all([
    fetchMetrics(),
    fetchVms(),
    fetchAuditLogs(),
  ]);
}

async function fetchMetrics() {
  try {
    const res = await fetch(`${API_BASE}/dashboard/metrics`);
    if (!res.ok) return;
    metricsData = await res.json();

    elAllocatedCores.textContent = metricsData.allocated_cores;
    elTotalCores.textContent = metricsData.total_cores;
    elAvailableCores.textContent = `${metricsData.available_cores} Cores Available`;

    const pct = Math.min(100, Math.max(0, metricsData.utilization_percentage));
    elGaugeFill.style.width = `${pct}%`;
    elGaugePct.textContent = `${pct}% Allocated`;

    // State counts
    elCountRunning.textContent = metricsData.vms_by_state.RUNNING || 0;
    elCountStopped.textContent = metricsData.vms_by_state.STOPPED || 0;
    elCountStopping.textContent = metricsData.vms_by_state.STOPPING || 0;
    elCountUnreachable.textContent = metricsData.vms_by_state.UNREACHABLE || 0;
    elActiveVmsCount.textContent = `${metricsData.total_vms} Tracked`;

    elTriadCtrlVal.textContent = `${metricsData.active_leases_count} Leases`;
    elTriadHypVal.textContent = `${metricsData.vms_by_state.RUNNING || 0} Running`;
  } catch (err) {
    console.error('Error fetching metrics:', err);
  }
}

async function fetchVms() {
  try {
    const res = await fetch(`${API_BASE}/vms`);
    if (!res.ok) return;
    currentVms = await res.json();
    renderVmsTable();
  } catch (err) {
    console.error('Error fetching VMs:', err);
  }
}

function renderVmsTable() {
  const query = elVmSearch.value.trim().toLowerCase();
  const filtered = currentVms.filter(vm => 
    vm.hostname.toLowerCase().includes(query) ||
    vm.hypervisor_uuid.toLowerCase().includes(query) ||
    vm.current_state.toLowerCase().includes(query)
  );

  if (filtered.length === 0) {
    elVmsTableBody.innerHTML = `<tr><td colspan="7" class="loading-cell">No virtual machines match query.</td></tr>`;
    return;
  }

  elVmsTableBody.innerHTML = filtered.map(vm => {
    const timeStr = vm.last_heartbeat 
      ? new Date(vm.last_heartbeat).toLocaleTimeString() 
      : 'Never';

    return `
      <tr>
        <td><strong>${escapeHtml(vm.hostname)}</strong></td>
        <td><span class="uuid-badge">${escapeHtml(vm.hypervisor_uuid)}</span></td>
        <td>${vm.core_count} Cores</td>
        <td>
          <span class="status-badge ${vm.current_state}">
            <span class="status-dot"></span>
            ${vm.current_state}
          </span>
        </td>
        <td>${vm.current_state === 'RUNNING' || vm.current_state === 'UNREACHABLE' ? '<span class="tag tag-success">ACTIVE</span>' : '<span class="tag">NONE</span>'}</td>
        <td><span class="subtext">${timeStr}</span></td>
        <td>
          ${vm.current_state === 'RUNNING' || vm.current_state === 'UNREACHABLE' 
            ? `<button class="btn btn-secondary btn-sm" onclick="releaseVm('${vm.hypervisor_uuid}')">Release Lease</button>`
            : `<button class="btn btn-primary btn-sm" onclick="quickStartVm('${vm.hypervisor_uuid}')">Start (Gated)</button>`
          }
        </td>
      </tr>
    `;
  }).join('');
}

async function fetchAuditLogs() {
  try {
    const res = await fetch(`${API_BASE}/audit?limit=25`);
    if (!res.ok) return;
    const logs = await res.json();
    elAuditTotalCount.textContent = logs.length;

    if (logs.length === 0) {
      elAuditTimeline.innerHTML = `<div class="audit-loading">No audit events recorded yet.</div>`;
      return;
    }

    elAuditTimeline.innerHTML = logs.map(item => {
      const time = new Date(item.timestamp).toLocaleTimeString();
      return `
        <div class="audit-item ${escapeHtml(item.action)}">
          <span class="audit-time">${time}</span>
          <div>
            <span class="audit-action">${escapeHtml(item.action)}</span>
            <span class="subtext">by ${escapeHtml(item.actor)}</span>
            <div class="audit-notes">${escapeHtml(item.notes || '')}</div>
          </div>
        </div>
      `;
    }).join('');
  } catch (err) {
    console.error('Error fetching audit logs:', err);
  }
}

async function triggerReconciliation() {
  elBtnReconcileNow.disabled = true;
  elBtnReconcileNow.innerHTML = 'Reconciling...';
  try {
    const res = await fetch(`${API_BASE}/reconciliation/run`, { method: 'POST' });
    const data = await res.json();
    fetchAllData();
    renderDiscrepancies(data.discrepancies);
  } catch (err) {
    console.error('Reconciliation error:', err);
  } finally {
    elBtnReconcileNow.disabled = false;
    elBtnReconcileNow.innerHTML = `
      <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"/>
      </svg>
      Reconcile Now
    `;
  }
}

function renderDiscrepancies(discrepancies) {
  const container = document.getElementById('discrepancy-container');
  if (!discrepancies || discrepancies.length === 0) {
    container.classList.add('hidden');
    return;
  }

  container.classList.remove('hidden');
  container.innerHTML = `
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 8px;">
      <strong style="color: var(--accent-rose)">Reconciliation Discrepancies Detected (${discrepancies.length})</strong>
      <button class="btn btn-ghost btn-sm" onclick="document.getElementById('discrepancy-container').classList.add('hidden')">&times;</button>
    </div>
    ${discrepancies.map(d => `
      <div style="font-size:0.8rem; margin-top:4px;">
        <strong>[${d.type}]</strong> VM <em>${d.hostname}</em> — ${d.recommended_action} 
        <span class="tag ${d.resolution_status === 'AUTO_RESOLVED' ? 'tag-success' : 'tag-danger'}">${d.resolution_status}</span>
      </div>
    `).join('')}
  `;
}

function populateModalVms() {
  elSelectStartVm.innerHTML = currentVms.map(vm => `
    <option value="${vm.hypervisor_uuid}" data-cores="${vm.core_count}">
      ${vm.hostname} (${vm.core_count} cores, State: ${vm.current_state})
    </option>
  `).join('');
  updateStartCapacityPreview();
}

function updateStartCapacityPreview() {
  const reqCores = parseInt(elInputCores.value, 10) || 8;
  const avail = metricsData ? metricsData.available_cores : 0;
  if (reqCores <= avail) {
    elPreviewCapacity.innerHTML = `<span style="color: var(--accent-emerald);">Sufficient Capacity (${avail} cores available, requesting ${reqCores})</span>`;
    elBtnConfirmStart.disabled = false;
  } else {
    elPreviewCapacity.innerHTML = `<span style="color: var(--accent-rose);">Insufficient Capacity (${avail} cores available, requesting ${reqCores})</span>`;
    elBtnConfirmStart.disabled = true;
  }
}

async function handleAuthorizeStart() {
  const uuid = elSelectStartVm.value;
  const cores = parseInt(elInputCores.value, 10) || 8;
  elBtnConfirmStart.disabled = true;
  elModalStartAlert.className = 'alert-box hidden';

  try {
    const res = await fetch(`${API_BASE}/enforcement/request-start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ hypervisor_uuid: uuid, requested_cores: cores, actor: 'dashboard_operator' }),
    });

    const data = await res.json();
    if (res.ok && data.authorized) {
      elModalStartAlert.className = 'alert-box success';
      elModalStartAlert.textContent = data.message;
      setTimeout(() => {
        elModalStart.classList.add('hidden');
        fetchAllData();
      }, 1200);
    } else {
      elModalStartAlert.className = 'alert-box error';
      elModalStartAlert.textContent = data.detail ? data.detail.reason || data.detail : 'Start authorization denied.';
    }
  } catch (err) {
    elModalStartAlert.className = 'alert-box error';
    elModalStartAlert.textContent = `Network error: ${err.message}`;
  } finally {
    elBtnConfirmStart.disabled = false;
  }
}

async function quickStartVm(uuid) {
  try {
    const res = await fetch(`${API_BASE}/enforcement/request-start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ hypervisor_uuid: uuid, actor: 'dashboard_quickstart' }),
    });
    const data = await res.json();
    if (res.ok) {
      fetchAllData();
    } else {
      alert(`Admission Denied: ${data.detail ? data.detail.reason : 'Insufficient cores'}`);
    }
  } catch (err) {
    alert(`Error: ${err.message}`);
  }
}

async function releaseVm(uuid) {
  if (!confirm('Are you sure you want to release the dynamic core allocation for this VM?')) return;
  try {
    const res = await fetch(`${API_BASE}/leases/release`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ hypervisor_uuid: uuid, reason: 'operator_manual_release', force: true }),
    });
    if (res.ok) {
      fetchAllData();
    } else {
      const err = await res.json();
      alert(`Release Error: ${err.detail || 'Failed to release'}`);
    }
  } catch (e) {
    alert(`Error: ${e.message}`);
  }
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}
