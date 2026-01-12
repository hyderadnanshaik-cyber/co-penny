// Auth Check
if (localStorage.getItem('copenny_authenticated') !== 'true') {
    window.location.href = '/landing';
}

function handleLogout() {
    localStorage.removeItem('copenny_authenticated');
    window.location.href = '/landing';
}

// Tab Switching
function switchTab(tab) {
    document.querySelectorAll('.tab-content').forEach(el => {
        el.classList.add('hidden');
        el.classList.remove('flex');
    });

    const activeTab = document.getElementById('tab-' + tab);
    if (activeTab) {
        activeTab.classList.remove('hidden');
        if (tab === 'chat') {
            activeTab.classList.add('flex');
        }
    }

    document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active-nav'));
    const navItem = document.getElementById('nav-' + tab);
    if (navItem) navItem.classList.add('active-nav');

    const title = document.getElementById('tabTitle');
    if (title) {
        const titles = {
            'overview': 'Dashboard',
            'chat': 'AI Advisor',
            'data': 'Data Management',
            'plans': 'Pricing Plans'
        };
        title.textContent = titles[tab] || (tab.charAt(0).toUpperCase() + tab.slice(1));
    }
}

// Appearance Mode
function toggleTheme() {
    const isLight = document.documentElement.classList.toggle('light-mode');
    localStorage.setItem('copenny_theme', isLight ? 'light' : 'dark');
    updateThemeIcons();
}

function updateThemeIcons() {
    const isLight = document.documentElement.classList.contains('light-mode');
    const sunIcon = document.getElementById('sunIcon');
    const moonIcon = document.getElementById('moonIcon');
    if (sunIcon && moonIcon) {
        sunIcon.classList.toggle('hidden', isLight);
        moonIcon.classList.toggle('hidden', !isLight);
    }
}

// App Logic
let currentUserId = localStorage.getItem('copenny_user_id') || 'guest';
let currentUserName = localStorage.getItem('copenny_user_name') || 'Investor';

function updateUserIdDisplay() {
    const display = document.getElementById('userIdDisplay');
    if (display) display.textContent = currentUserId;

    const nameDisplay = document.getElementById('userNameDisplay');
    if (nameDisplay) {
        nameDisplay.textContent = currentUserName;
        const initials = document.getElementById('userInitials');
        if (initials) initials.textContent = currentUserName.charAt(0).toUpperCase();
    }
    updateSubscriptionStatus();
}

async function updateSubscriptionStatus() {
    try {
        const res = await fetch(`/subscription/status?user_id=${currentUserId}`);
        const data = await res.json();
        const badge = document.getElementById('tierBadge');
        if (badge) {
            badge.textContent = data.tier || 'Free';
            // Update badge style based on tier
            if (data.tier === 'pro') {
                badge.className = 'text-[9px] px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-500 font-bold uppercase tracking-wider';
            } else if (data.tier === 'enterprise') {
                badge.className = 'text-[9px] px-1.5 py-0.5 rounded bg-purple-500/20 text-purple-400 font-bold uppercase tracking-wider';
            } else {
                badge.className = 'text-[9px] px-1.5 py-0.5 rounded bg-slate-500/20 text-slate-400 font-bold uppercase tracking-wider';
            }
        }
    } catch (e) {
        console.error('Error fetching subscription status:', e);
    }
}

function appendMessage(who, text, visualizations = null) {
    const container = document.getElementById('chat-messages');
    if (!container) return;

    const div = document.createElement('div');
    div.className = (who === 'user' ? 'msg-user self-end' : 'msg-bot') + ' p-4 rounded-2xl max-w-2xl text-sm leading-relaxed animate-fade-in flex flex-col gap-4';

    const textDiv = document.createElement('div');
    textDiv.textContent = text;
    div.appendChild(textDiv);

    if (visualizations) {
        for (const [type, data] of Object.entries(visualizations)) {
            if (data && data.startsWith('data:image')) {
                const vizWrapper = document.createElement('div');
                vizWrapper.className = 'bg-slate-900/50 p-4 rounded-xl border border-slate-800';
                const img = document.createElement('img');
                img.src = data;
                img.className = 'w-full rounded-lg shadow-xl';
                vizWrapper.innerHTML = `<p class="text-[10px] uppercase font-bold text-slate-500 mb-2">${type.replace('_', ' ')}</p>`;
                vizWrapper.appendChild(img);
                div.appendChild(vizWrapper);
            }
        }
    }

    container.appendChild(div);
    div.scrollIntoView({ behavior: 'smooth' });
}

async function handleChat(ev) {
    if (ev) ev.preventDefault();
    const input = document.getElementById('chatInput');
    const msg = input.value.trim();
    if (!msg) return;

    input.value = '';
    appendMessage('user', msg);

    const btn = document.getElementById('sendBtn');
    btn.disabled = true;
    const originalText = btn.textContent;
    btn.textContent = '...';

    try {
        const res = await fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: 'local', message: msg, context: [], user_id: currentUserId })
        });
        const data = await res.json();

        if (data.status === 'limit_reached') {
            appendMessage('bot', data.answer + ' 🚀');
            // Add a "Go Pro" button/link in the chat if possible, or just the text
        } else {
            appendMessage('bot', data.answer || "I'm not sure how to respond to that.", data.visualizations);
        }
        updateSubscriptionStatus(); // Refresh usage numbers if we had them in UI
    } catch (e) {
        appendMessage('bot', 'Connection error: ' + e.message);
    } finally {
        btn.disabled = false;
        btn.textContent = originalText;
    }
}

// Data Management
async function checkStatus() {
    try {
        const res = await fetch(`/personalization/status/${currentUserId}`);
        const data = await res.json();
        const statusDiv = document.getElementById('personalizationStatus');
        if (!statusDiv) return;

        if (data.has_data) {
            statusDiv.innerHTML = `<div class="bg-emerald-500/10 text-emerald-400 p-4 rounded-2xl border border-emerald-500/20 text-xs">
        <strong>✓ Data Synchronized</strong><br>${data.metadata.total_transactions} records found
      </div>`;
            if (data.has_model) {
                document.getElementById('modelStatusMsg').textContent = 'High Accuracy Active';
            }
        }
    } catch (e) { }
}

async function uploadCSV() {
    const fileInput = document.getElementById('csvFile');
    const file = fileInput ? fileInput.files[0] : null;
    if (!file) return alert('Select a file');

    const formData = new FormData();
    formData.append('file', file);
    formData.append('user_id', currentUserId);
    formData.append('overwrite', document.getElementById('overwriteCheck').checked);

    const btn = document.getElementById('uploadBtn');
    btn.disabled = true;
    const originalText = btn.textContent;
    btn.textContent = 'Processing...';

    try {
        const res = await fetch('/personalization/upload', { method: 'POST', body: formData });
        const data = await res.json();

        if (data.success === false && data.error && data.error.includes('limit')) {
            document.getElementById('uploadStatus').innerHTML = `<p class="text-[10px] mt-2 text-amber-500 uppercase font-bold">${data.error}</p>
            <button onclick="window.location.href='/landing#pricing'" class="text-[9px] text-indigo-400 hover:underline mt-1 font-bold">UPGRADE PLAN</button>`;
        } else {
            document.getElementById('uploadStatus').innerHTML = `<p class="text-[10px] mt-2 ${data.success ? 'text-emerald-400' : 'text-red-400'} uppercase font-bold">${data.message || data.error}</p>`;
        }

        if (data.success) {
            // Refresh dashboard immediately after successful upload
            await refreshDashboard();
            await loadAlertHistory();
        }
        checkStatus();
        updateSubscriptionStatus();
    } catch (e) {
        document.getElementById('uploadStatus').innerHTML = `<p class="text-[10px] mt-2 text-red-400 uppercase font-bold">Upload Error</p>`;
    } finally {
        btn.disabled = false;
        btn.textContent = originalText;
    }
}

async function trainModel() {
    const btn = document.getElementById('trainBtn');
    btn.disabled = true;
    const originalText = btn.textContent;
    btn.textContent = 'Calibrating...';

    try {
        const formData = new FormData();
        formData.append('user_id', currentUserId);
        formData.append('retrain', true);
        const res = await fetch('/personalization/train', { method: 'POST', body: formData });
        const data = await res.json();
        const status = document.getElementById('trainStatus');
        if (data.success) {
            status.innerHTML = `<p class="text-[10px] mt-2 text-emerald-400 uppercase font-bold">Success: ${Math.round(data.test_accuracy * 100)}% Accuracy</p>`;
            document.getElementById('modelStatusMsg').textContent = 'Personalized Intelligence Ready';
            await refreshDashboard();
        } else {
            status.innerHTML = `<p class="text-[10px] mt-2 text-red-400 uppercase font-bold">${data.error}</p>`;
        }
    } catch (e) {
        document.getElementById('trainStatus').innerHTML = `<p class="text-[10px] mt-2 text-red-400 uppercase font-bold">Calibration Failed</p>`;
    } finally {
        btn.disabled = false;
        btn.textContent = originalText;
    }
}

// Delete User Data
async function deleteUserData() {
    if (!confirm('Are you sure you want to delete all your data? This cannot be undone.')) {
        return;
    }

    const btn = document.getElementById('deleteDataBtn');
    if (btn) {
        btn.disabled = true;
        btn.textContent = 'Deleting...';
    }

    try {
        const res = await fetch(`/personalization/data?user_id=${currentUserId}`, { method: 'DELETE' });
        const data = await res.json();

        if (data.success) {
            document.getElementById('uploadStatus').innerHTML = `<p class="text-[10px] mt-2 text-emerald-400 uppercase font-bold">Data deleted successfully</p>`;
            document.getElementById('personalizationStatus').innerHTML = '';
            document.getElementById('modelStatusMsg').textContent = 'Ready for Calibration';
            await refreshDashboard();
            await loadAlertHistory();
        } else {
            document.getElementById('uploadStatus').innerHTML = `<p class="text-[10px] mt-2 text-red-400 uppercase font-bold">${data.error}</p>`;
        }
    } catch (e) {
        document.getElementById('uploadStatus').innerHTML = `<p class="text-[10px] mt-2 text-red-400 uppercase font-bold">Delete Error</p>`;
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.textContent = 'Delete All Data';
        }
    }
}

// Alert History
async function loadAlertHistory() {
    try {
        const res = await fetch(`/alerts/history?user_id=${currentUserId}`);
        const data = await res.json();

        const container = document.getElementById('alertHistoryContainer');
        if (!container) return;

        if (data.success && data.alerts && data.alerts.length > 0) {
            container.innerHTML = data.alerts.map(alert => `
                <div class="flex gap-4 items-start p-4 rounded-xl hover:bg-white/5 transition-all ${alert.severity === 'high' ? 'border-l-4 border-red-500' :
                    alert.severity === 'medium' ? 'border-l-4 border-amber-500' :
                        'border-l-4 border-blue-500'
                }">
                    <div class="w-10 h-10 rounded-full ${alert.severity === 'high' ? 'bg-red-500/20' :
                    alert.severity === 'medium' ? 'bg-amber-500/20' :
                        'bg-blue-500/20'
                } flex items-center justify-center shrink-0 text-xs font-bold">
                        ${alert.type === 'large_transaction' ? '💰' :
                    alert.type === 'negative_balance' ? '⚠️' :
                        alert.type === 'unusual_spending' ? '📊' : '🔔'}
                    </div>
                    <div class="flex-1">
                        <p class="text-sm font-medium text-white mb-1">${alert.title || 'Financial Alert'}</p>
                        <p class="text-xs text-slate-400">${alert.message}</p>
                        <p class="text-[10px] text-slate-600 mt-2">${new Date(alert.created_at).toLocaleDateString()}</p>
                    </div>
                </div>
            `).join('');
        } else {
            container.innerHTML = `
                <div class="text-center py-8 text-slate-500">
                    <p class="text-sm">No alerts yet</p>
                    <p class="text-xs mt-1">Upload transaction data to receive financial insights</p>
                </div>
            `;
        }
    } catch (e) {
        console.error('Error loading alert history:', e);
    }
}

async function clearAlertHistory() {
    if (!confirm('Clear all alert history?')) return;

    try {
        const res = await fetch(`/alerts/history?user_id=${currentUserId}`, { method: 'DELETE' });
        const data = await res.json();
        if (data.success) {
            await loadAlertHistory();
        }
    } catch (e) {
        console.error('Error clearing alerts:', e);
    }
}

// Dashboard Metrics
async function refreshDashboard() {
    try {
        const res = await fetch(`/dashboard/summary?user_id=${currentUserId}`);
        const data = await res.json();

        if (data.has_data) {
            document.getElementById('stat-balance').textContent = '₹ ' + data.balance.toLocaleString();
            document.getElementById('stat-expense').textContent = '₹ ' + data.monthly_expense.toLocaleString();
            document.getElementById('stat-confidence').textContent = data.confidence + '%';

            document.getElementById('stat-balance-note').textContent = '+12.5% vs last month'; // Note can be static or dynamic
            document.getElementById('stat-expense-note').textContent = 'Based on ' + data.transaction_count + ' records';
            document.getElementById('stat-confidence-note').textContent = 'Data Range: ' + data.date_range;
        } else {
            document.getElementById('stat-balance').textContent = '₹ --';
            document.getElementById('stat-expense').textContent = '₹ --';
            document.getElementById('stat-confidence').textContent = '0%';

            document.getElementById('stat-balance-note').textContent = 'Upload CSV to see balance';
            document.getElementById('stat-expense-note').textContent = 'No data available';
            document.getElementById('stat-confidence-note').textContent = 'Waiting for calibration';
        }
    } catch (e) {
        console.error('Error fetching dashboard stats:', e);
    }
}

// Initialization
document.addEventListener('DOMContentLoaded', () => {
    // Theme init
    if (localStorage.getItem('copenny_theme') === 'light') {
        document.documentElement.classList.add('light-mode');
    }
    updateThemeIcons();

    updateUserIdDisplay();
    refreshDashboard();
    loadAlertHistory();

    const chatForm = document.getElementById('chatForm');
    if (chatForm) chatForm.addEventListener('submit', handleChat);

    const uploadBtn = document.getElementById('uploadBtn');
    if (uploadBtn) uploadBtn.addEventListener('click', uploadCSV);

    const trainBtn = document.getElementById('trainBtn');
    if (trainBtn) trainBtn.addEventListener('click', trainModel);

    const deleteDataBtn = document.getElementById('deleteDataBtn');
    if (deleteDataBtn) deleteDataBtn.addEventListener('click', deleteUserData);

    const clearHistoryBtn = document.getElementById('clearHistoryBtn');
    if (clearHistoryBtn) clearHistoryBtn.addEventListener('click', clearAlertHistory);

    const csvFile = document.getElementById('csvFile');
    if (csvFile) {
        csvFile.addEventListener('change', (e) => {
            document.getElementById('fileNameDisplay').textContent = e.target.files[0] ? e.target.files[0].name : 'Choose CSV File';
        });
    }
    checkStatus();
});
