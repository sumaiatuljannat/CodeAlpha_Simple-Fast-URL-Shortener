/**
 * LinkSnap - Production Client-Side Application Logic
 * Handles asynchronous REST API calls, dynamic UI updates, Chart.js visualizations,
 * QR code handling, modals, and notifications.
 */

let currentResultCode = null;
let currentResultUrl = null;
let currentTagFilter = '';
let searchDebounceTimer = null;

// Chart.js instances for dynamic destruction and re-creation
let timelineChartInstance = null;
let devicesChartInstance = null;
let referrersChartInstance = null;

document.addEventListener('DOMContentLoaded', () => {
    loadDashboardLinks();

    // Check if opened via /stats/<short_code> deep link
    if (window.INITIAL_STATS_CODE) {
        openStatsForShortCode(window.INITIAL_STATS_CODE);
    }
});

// ============================================================================
// TOAST NOTIFICATIONS
// ============================================================================

function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = 'toast';
    
    let icon = 'ℹ️';
    if (type === 'success') icon = '✅';
    if (type === 'error') icon = '⚠️';
    
    toast.innerHTML = `<span>${icon}</span> <span>${escapeHtml(message)}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(10px)';
        toast.style.transition = 'all 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// ============================================================================
// ADVANCED OPTIONS TOGGLE
// ============================================================================

function toggleAdvancedOptions() {
    const panel = document.getElementById('advancedOptionsPanel');
    const arrow = document.getElementById('advToggleArrow');
    if (panel.classList.contains('hidden')) {
        panel.classList.remove('hidden');
        arrow.textContent = '▲';
    } else {
        panel.classList.add('hidden');
        arrow.textContent = '▼';
    }
}

// ============================================================================
// CREATE SHORT URL (FORM SUBMISSION)
// ============================================================================

async function handleShortenSubmit(e) {
    e.preventDefault();
    const alertBox = document.getElementById('shortenAlert');
    const submitBtn = document.getElementById('shortenSubmitBtn');
    const btnText = document.getElementById('shortenBtnText');
    const btnSpinner = document.getElementById('shortenBtnSpinner');

    alertBox.className = 'alert hidden';
    alertBox.textContent = '';
    btnText.textContent = 'Shortening...';
    btnSpinner.classList.remove('hidden');
    submitBtn.disabled = true;

    const originalUrl = document.getElementById('originalUrlInput').value.trim();
    const customCode = document.getElementById('customCodeInput').value.trim();
    const title = document.getElementById('titleInput').value.trim();
    const tags = document.getElementById('tagsInput').value.trim();
    const expiresAt = document.getElementById('expiresAtInput').value.trim();

    try {
        const response = await fetch('/api/shorten', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                original_url: originalUrl,
                custom_code: customCode || undefined,
                title: title || undefined,
                tags: tags || undefined,
                expires_at: expiresAt || undefined
            })
        });

        const data = await response.json();

        if (!response.ok || !data.success) {
            throw new Error(data.error || 'Failed to shorten URL.');
        }

        // Display Success in Result Card
        currentResultCode = data.link.short_code;
        currentResultUrl = data.link.short_url;

        document.getElementById('resultShortUrl').textContent = data.link.short_url;
        document.getElementById('resultShortUrl').href = data.link.short_url;
        document.getElementById('resultOriginalUrl').textContent = data.link.original_url;
        document.getElementById('resultOriginalUrl').title = data.link.original_url;
        document.getElementById('resultQrImg').src = data.link.qr_data_uri;
        document.getElementById('resultQrDownloadBtn').href = `/api/links/${data.link.short_code}/qr?download=1&format=png`;

        document.getElementById('resultCard').classList.remove('hidden');
        document.getElementById('resultCard').scrollIntoView({ behavior: 'smooth', block: 'nearest' });

        // Reset form inputs
        document.getElementById('originalUrlInput').value = '';
        document.getElementById('customCodeInput').value = '';
        document.getElementById('titleInput').value = '';
        document.getElementById('tagsInput').value = '';
        document.getElementById('expiresAtInput').value = '';

        showToast('Short link generated successfully!', 'success');
        loadDashboardLinks();

    } catch (err) {
        alertBox.className = 'alert error';
        alertBox.textContent = err.message;
        alertBox.classList.remove('hidden');
    } finally {
        btnText.textContent = 'Shorten URL';
        btnSpinner.classList.add('hidden');
        submitBtn.disabled = false;
    }
}

// Copy from main result card
function copyResultUrl() {
    if (!currentResultUrl) return;
    copyToClipboard(currentResultUrl);
}

function copyToClipboard(text) {
    if (navigator.clipboard) {
        navigator.clipboard.writeText(text).then(() => {
            showToast('Copied to clipboard: ' + text, 'success');
        }).catch(() => fallbackCopy(text));
    } else {
        fallbackCopy(text);
    }
}

function fallbackCopy(text) {
    const el = document.createElement('textarea');
    el.value = text;
    document.body.appendChild(el);
    el.select();
    document.execCommand('copy');
    document.body.removeChild(el);
    showToast('Copied to clipboard!', 'success');
}

// ============================================================================
// DASHBOARD & LINKS TABLE
// ============================================================================

async function loadDashboardLinks() {
    const tbody = document.getElementById('linksTableBody');
    const emptyState = document.getElementById('emptyState');
    const searchVal = document.getElementById('dashboardSearchInput').value.trim();
    const statusVal = document.getElementById('statusFilterSelect').value;

    const params = new URLSearchParams();
    if (searchVal) params.append('search', searchVal);
    if (statusVal !== 'all') params.append('status', statusVal);
    if (currentTagFilter) params.append('tag', currentTagFilter);

    try {
        const response = await fetch(`/api/links?${params.toString()}`);
        const data = await response.json();

        if (!response.ok || !data.success) {
            tbody.innerHTML = `<tr><td colspan="7" class="loading-cell text-center" style="color:var(--danger)">Failed to load links: ${data.error || 'Unknown error'}</td></tr>`;
            return;
        }

        renderLinks(data.links);
        updateKpis(data.links);
        updateTagPills(data.links);

    } catch (err) {
        tbody.innerHTML = `<tr><td colspan="7" class="loading-cell text-center" style="color:var(--danger)">Error connecting to server.</td></tr>`;
    }
}

function renderLinks(links) {
    const tbody = document.getElementById('linksTableBody');
    const emptyState = document.getElementById('emptyState');

    if (!links || links.length === 0) {
        tbody.innerHTML = '';
        emptyState.classList.remove('hidden');
        return;
    }

    emptyState.classList.add('hidden');
    tbody.innerHTML = links.map(link => {
        const tagsHtml = link.tags && link.tags.length > 0
            ? link.tags.map(t => `<span class="tag-pill" onclick="filterByTag('${escapeHtml(t)}')">${escapeHtml(t)}</span>`).join('')
            : '<span class="label-muted">-</span>';

        const statusClass = link.status;
        const statusLabel = link.status === 'active' ? '● Active' : (link.status === 'expired' ? '⏳ Expired' : '○ Inactive');

        return `
            <tr>
                <td>
                    <a href="${escapeHtml(link.short_url)}" target="_blank" class="short-code-link">
                        /${escapeHtml(link.short_code)}
                    </a>
                </td>
                <td class="title-dest-cell">
                    <span class="link-title-text">${escapeHtml(link.title || link.short_code)}</span>
                    <span class="link-dest-text" title="${escapeHtml(link.original_url)}">${escapeHtml(link.original_url)}</span>
                </td>
                <td>
                    <div class="tag-pills-row">${tagsHtml}</div>
                </td>
                <td>
                    <strong>${link.click_count}</strong>
                </td>
                <td>
                    <span class="badge-status ${statusClass}">${statusLabel}</span>
                </td>
                <td style="font-size:0.8rem; color:var(--slate-500)">
                    ${formatDate(link.created_at)}
                </td>
                <td class="text-right">
                    <div class="action-btns-group">
                        <button class="icon-btn" title="Copy Short Link" onclick="copyToClipboard('${escapeHtml(link.short_url)}')">📋</button>
                        <button class="icon-btn" title="View QR Code" onclick="openQrModal('${escapeHtml(link.short_code)}', '${escapeHtml(link.short_url)}')">📷</button>
                        <button class="icon-btn" title="View Click Analytics" onclick="openStatsForShortCode('${escapeHtml(link.short_code)}')">📊</button>
                        <button class="icon-btn" title="Edit Link" onclick="openEditModal('${escapeHtml(link.short_code)}')">✏️</button>
                        <button class="icon-btn danger" title="Delete Link" onclick="deleteLink('${escapeHtml(link.short_code)}')">🗑️</button>
                    </div>
                </td>
            </tr>
        `;
    }).join('');
}

function updateKpis(links) {
    const totalLinks = links.length;
    let totalClicks = 0;
    let activeCount = 0;
    let inactiveCount = 0;

    links.forEach(l => {
        totalClicks += (l.click_count || 0);
        if (l.status === 'active') activeCount++;
        else inactiveCount++;
    });

    document.getElementById('kpiTotalLinks').textContent = totalLinks;
    document.getElementById('kpiTotalClicks').textContent = totalClicks;
    document.getElementById('kpiActiveLinks').textContent = activeCount;
    document.getElementById('kpiInactiveLinks').textContent = inactiveCount;
}

function updateTagPills(links) {
    const container = document.getElementById('tagPillsContainer');
    const allTags = new Set();
    links.forEach(l => {
        if (l.tags && Array.isArray(l.tags)) {
            l.tags.forEach(t => allTags.add(t));
        }
    });

    if (allTags.size === 0) {
        container.innerHTML = '';
        return;
    }

    let html = `<span class="tag-pill ${!currentTagFilter ? 'active' : ''}" onclick="filterByTag('')">All</span>`;
    allTags.forEach(tag => {
        const isActive = currentTagFilter === tag ? 'active' : '';
        html += `<span class="tag-pill ${isActive}" onclick="filterByTag('${escapeHtml(tag)}')">#${escapeHtml(tag)}</span>`;
    });
    container.innerHTML = html;
}

function filterByTag(tag) {
    currentTagFilter = tag;
    loadDashboardLinks();
}

function debounceSearch() {
    clearTimeout(searchDebounceTimer);
    searchDebounceTimer = setTimeout(() => {
        loadDashboardLinks();
    }, 250);
}

async function deleteLink(shortCode) {
    if (!confirm(`Are you sure you want to permanently delete /${shortCode}? This will remove all its click analytics.`)) {
        return;
    }

    try {
        const response = await fetch(`/api/links/${encodeURIComponent(shortCode)}`, {
            method: 'DELETE'
        });
        const data = await response.json();
        if (!response.ok || !data.success) {
            throw new Error(data.error || 'Failed to delete link.');
        }

        showToast(`Link /${shortCode} deleted.`, 'success');
        loadDashboardLinks();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

// ============================================================================
// ANALYTICS MODAL & CHART.JS
// ============================================================================

async function openStatsForShortCode(shortCode) {
    openModal('analyticsModal');
    document.getElementById('statsLoading').classList.remove('hidden');
    document.getElementById('statsContent').classList.add('hidden');
    document.getElementById('statsModalSubtitle').textContent = `Analytics for /${shortCode}`;

    try {
        const response = await fetch(`/api/links/${encodeURIComponent(shortCode)}/stats`);
        const data = await response.json();

        if (!response.ok || !data.success) {
            throw new Error(data.error || 'Failed to load analytics.');
        }

        renderAnalytics(data.link, data.analytics);
    } catch (err) {
        document.getElementById('statsLoading').innerHTML = `<span style="color:var(--danger)">⚠️ ${err.message}</span>`;
    }
}

function renderAnalytics(link, analytics) {
    document.getElementById('statsLoading').classList.add('hidden');
    document.getElementById('statsContent').classList.remove('hidden');

    document.getElementById('modalTotalClicks').textContent = analytics.total_clicks;
    document.getElementById('modalTopReferrer').textContent = analytics.referrers[0]?.name || 'Direct';
    document.getElementById('modalTopDevice').textContent = analytics.devices[0]?.name || 'Desktop';

    // 1. Timeline Chart
    renderTimelineChart(analytics.timeline);

    // 2. Devices Doughnut Chart
    renderDevicesChart(analytics.devices);

    // 3. Referrers Bar Chart
    renderReferrersChart(analytics.referrers);

    // 4. Browser / OS List
    const browserList = document.getElementById('browserBreakdownList');
    let bHtml = '';
    const browsers = analytics.browsers || [];
    const oss = analytics.operating_systems || [];

    if (browsers.length === 0 && oss.length === 0) {
        bHtml = '<span class="label-muted">No visitor data yet.</span>';
    } else {
        bHtml += '<strong>Top Browsers:</strong>';
        browsers.forEach(b => {
            bHtml += `<div class="breakdown-item"><span>${escapeHtml(b.name)}</span><span>${b.clicks} clicks</span></div>`;
        });
        bHtml += '<strong style="margin-top:0.5rem">Top OS:</strong>';
        oss.forEach(o => {
            bHtml += `<div class="breakdown-item"><span>${escapeHtml(o.name)}</span><span>${o.clicks} clicks</span></div>`;
        });
    }
    browserList.innerHTML = bHtml;

    // 5. Recent Clicks Log Table
    const recentTbody = document.getElementById('recentClicksTableBody');
    if (!analytics.recent_clicks || analytics.recent_clicks.length === 0) {
        recentTbody.innerHTML = `<tr><td colspan="5" class="text-center label-muted">No visits recorded yet.</td></tr>`;
    } else {
        recentTbody.innerHTML = analytics.recent_clicks.map(rc => `
            <tr>
                <td>${formatDate(rc.clicked_at)}</td>
                <td>${escapeHtml(rc.referrer)}</td>
                <td>${escapeHtml(rc.device_type)}</td>
                <td>${escapeHtml(rc.browser)}</td>
                <td>${escapeHtml(rc.os)}</td>
            </tr>
        `).join('');
    }
}

function renderTimelineChart(timeline) {
    const ctx = document.getElementById('timelineChart').getContext('2d');
    if (timelineChartInstance) timelineChartInstance.destroy();

    const labels = timeline.length > 0 ? timeline.map(t => t.date) : ['No Data'];
    const dataPoints = timeline.length > 0 ? timeline.map(t => t.clicks) : [0];

    timelineChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Clicks',
                data: dataPoints,
                borderColor: '#4f46e5',
                backgroundColor: 'rgba(79, 70, 229, 0.1)',
                borderWidth: 2,
                fill: true,
                tension: 0.3,
                pointRadius: 4,
                pointBackgroundColor: '#4f46e5'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                y: { beginAtZero: true, ticks: { precision: 0 } }
            }
        }
    });
}

function renderDevicesChart(devices) {
    const ctx = document.getElementById('devicesChart').getContext('2d');
    if (devicesChartInstance) devicesChartInstance.destroy();

    const labels = devices.length > 0 ? devices.map(d => d.name) : ['None'];
    const dataPoints = devices.length > 0 ? devices.map(d => d.clicks) : [1];
    const colors = ['#4f46e5', '#10b981', '#f59e0b', '#64748b'];

    devicesChartInstance = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: dataPoints,
                backgroundColor: colors.slice(0, labels.length)
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'bottom' }
            }
        }
    });
}

function renderReferrersChart(referrers) {
    const ctx = document.getElementById('referrersChart').getContext('2d');
    if (referrersChartInstance) referrersChartInstance.destroy();

    const labels = referrers.length > 0 ? referrers.map(r => r.name) : ['No Referrers'];
    const dataPoints = referrers.length > 0 ? referrers.map(r => r.clicks) : [0];

    referrersChartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Clicks',
                data: dataPoints,
                backgroundColor: '#10b981',
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { ticks: { autoSkip: false } },
                y: { beginAtZero: true, ticks: { precision: 0 } }
            }
        }
    });
}

// ============================================================================
// QR CODE MODAL
// ============================================================================

function openQrModalForResult() {
    if (!currentResultCode || !currentResultUrl) return;
    openQrModal(currentResultCode, currentResultUrl);
}

function openQrModal(shortCode, shortUrl) {
    document.getElementById('qrModalUrl').textContent = shortUrl;
    document.getElementById('modalQrImg').src = `/api/links/${encodeURIComponent(shortCode)}/qr?format=svg`;
    document.getElementById('modalQrSvgBtn').href = `/api/links/${encodeURIComponent(shortCode)}/qr?format=svg&download=1`;
    document.getElementById('modalQrPngBtn').href = `/api/links/${encodeURIComponent(shortCode)}/qr?format=png&download=1`;
    openModal('qrModal');
}

// ============================================================================
// EDIT LINK MODAL
// ============================================================================

async function openEditModal(shortCode) {
    const alertBox = document.getElementById('editAlert');
    alertBox.className = 'alert hidden';

    try {
        const response = await fetch(`/api/links/${encodeURIComponent(shortCode)}`);
        const data = await response.json();
        if (!response.ok || !data.success) {
            throw new Error(data.error || 'Failed to fetch link details.');
        }

        const link = data.link;
        document.getElementById('editShortCode').value = link.short_code;
        document.getElementById('editOriginalUrl').value = link.original_url;
        document.getElementById('editTitle').value = link.title || '';
        document.getElementById('editTags').value = link.tags ? link.tags.join(', ') : '';
        document.getElementById('editExpiresAt').value = link.expires_at ? link.expires_at.slice(0, 16) : '';
        document.getElementById('editIsActive').checked = link.is_active;

        openModal('editModal');
    } catch (err) {
        showToast(err.message, 'error');
    }
}

async function handleEditSubmit(e) {
    e.preventDefault();
    const shortCode = document.getElementById('editShortCode').value;
    const alertBox = document.getElementById('editAlert');

    alertBox.className = 'alert hidden';

    const originalUrl = document.getElementById('editOriginalUrl').value.trim();
    const title = document.getElementById('editTitle').value.trim();
    const tags = document.getElementById('editTags').value.trim();
    const expiresAt = document.getElementById('editExpiresAt').value.trim();
    const isActive = document.getElementById('editIsActive').checked;

    try {
        const response = await fetch(`/api/links/${encodeURIComponent(shortCode)}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                original_url: originalUrl,
                title: title,
                tags: tags,
                expires_at: expiresAt || null,
                is_active: isActive
            })
        });

        const data = await response.json();
        if (!response.ok || !data.success) {
            throw new Error(data.error || 'Failed to update link.');
        }

        showToast('Link updated successfully!', 'success');
        closeModal('editModal');
        loadDashboardLinks();
    } catch (err) {
        alertBox.className = 'alert error';
        alertBox.textContent = err.message;
        alertBox.classList.remove('hidden');
    }
}

// ============================================================================
// AUTHENTICATION MODAL & LOGIC
// ============================================================================

let currentAuthMode = 'login';

function openAuthModal(mode = 'login') {
    switchAuthTab(mode);
    openModal('authModal');
}

function switchAuthTab(mode) {
    currentAuthMode = mode;
    const loginBtn = document.getElementById('tabLoginBtn');
    const registerBtn = document.getElementById('tabRegisterBtn');
    const emailGroup = document.getElementById('authEmailGroup');
    const submitBtn = document.getElementById('authSubmitBtn');
    const alertBox = document.getElementById('authAlert');

    alertBox.className = 'alert hidden';

    if (mode === 'login') {
        loginBtn.classList.add('active');
        registerBtn.classList.remove('active');
        emailGroup.classList.add('hidden');
        submitBtn.textContent = 'Sign In';
    } else {
        loginBtn.classList.remove('active');
        registerBtn.classList.add('active');
        emailGroup.classList.remove('hidden');
        submitBtn.textContent = 'Create Account';
    }
}

async function handleAuthSubmit(e) {
    e.preventDefault();
    const alertBox = document.getElementById('authAlert');
    alertBox.className = 'alert hidden';

    const username = document.getElementById('authUsername').value.trim();
    const password = document.getElementById('authPassword').value;
    const email = document.getElementById('authEmail').value.trim();

    const endpoint = currentAuthMode === 'login' ? '/api/auth/login' : '/api/auth/register';
    const payload = currentAuthMode === 'login'
        ? { username: username, password: password }
        : { username: username, email: email, password: password };

    try {
        const response = await fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await response.json();
        if (!response.ok || !data.success) {
            throw new Error(data.error || 'Authentication failed.');
        }

        showToast(currentAuthMode === 'login' ? 'Signed in successfully!' : 'Account registered successfully!', 'success');
        closeModal('authModal');
        // Refresh page to render authenticated navbar and user links
        window.location.reload();
    } catch (err) {
        alertBox.className = 'alert error';
        alertBox.textContent = err.message;
        alertBox.classList.remove('hidden');
    }
}

async function handleLogout() {
    try {
        await fetch('/api/auth/logout', { method: 'POST' });
        showToast('Logged out.', 'info');
        window.location.reload();
    } catch (err) {
        showToast('Failed to log out.', 'error');
    }
}

// ============================================================================
// MODAL CONTROLS & UTILITIES
// ============================================================================

function openModal(id) {
    const modal = document.getElementById(id);
    if (modal) modal.classList.remove('hidden');
}

function closeModal(id) {
    const modal = document.getElementById(id);
    if (modal) modal.classList.add('hidden');
}

function handleModalBackdropClick(e, id) {
    if (e.target.id === id) {
        closeModal(id);
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

function formatDate(isoStr) {
    if (!isoStr) return '-';
    try {
        const d = new Date(isoStr);
        if (isNaN(d.getTime())) return isoStr;
        return d.toLocaleDateString(undefined, {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    } catch {
        return isoStr;
    }
}
