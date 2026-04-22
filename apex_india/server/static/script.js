/**
 * APEX INDIA — Frontend Logic
 * ===========================
 * Handles WebSocket connection, UI state management,
 * and real-time Chart.js updates.
 */

// ═══════════════════════════════════════════════════════════════
// CONFIG & STATE
// ═══════════════════════════════════════════════════════════════

const CONFIG = {
    WS_URL: `ws://${window.location.host}/ws`,
    API_URL: `http://${window.location.host}/api`
};

let state = {
    mode: 'paper',
    running: false,
    equity: 10000,
    day_pnl: 0,
    positions: [],
    signals: [],
    history: [] // For equity chart
};

let equityChart;

// ═══════════════════════════════════════════════════════════════
// INITIALIZATION
// ═══════════════════════════════════════════════════════════════

document.addEventListener('DOMContentLoaded', () => {
    initChart();
    connectWebSocket();
    startTimeUpdate();
    setupEventListeners();
});

// ═══════════════════════════════════════════════════════════════
// WEBSOCKET & API
// ═══════════════════════════════════════════════════════════════

function connectWebSocket() {
    console.log(`Connecting to WebSocket: ${CONFIG.WS_URL}`);
    const socket = new WebSocket(CONFIG.WS_URL);

    socket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        updateState(data);
    };

    socket.onclose = () => {
        console.warn('WebSocket closed. Reconnecting in 5s...');
        setTimeout(connectWebSocket, 5000);
    };

    socket.onerror = (err) => {
        console.error('WebSocket Error:', err);
    };
}

async function callApi(endpoint, method = 'GET', data = null) {
    try {
        const options = {
            method,
            headers: { 'Content-Type': 'application/json' }
        };
        if (data) options.body = JSON.stringify(data);
        
        const response = await fetch(`${CONFIG.API_URL}${endpoint}`, options);
        return await response.json();
    } catch (err) {
        console.error(`API Error (${endpoint}):`, err);
    }
}

// ═══════════════════════════════════════════════════════════════
// UI UPDATES
// ═══════════════════════════════════════════════════════════════

function updateState(newData) {
    state = { ...state, ...newData };
    renderUI();
}

function renderUI() {
    // 1. Status Badges
    const marketBadge = document.getElementById('market-status');
    marketBadge.textContent = state.market_open ? 'OPEN' : 'CLOSED';
    marketBadge.className = `status-badge ${state.market_open ? 'open' : 'closed'}`;

    const modeBadge = document.getElementById('mode-status');
    modeBadge.textContent = state.mode.toUpperCase();
    modeBadge.className = `status-badge ${state.mode}`;

    const modeToggle = document.getElementById('mode-toggle');
    modeToggle.checked = state.mode === 'real';

    // 2. Metrics
    const equityVal = document.getElementById('val-equity');
    equityVal.textContent = `₹${state.equity.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;

    const pnlVal = document.getElementById('val-pnl');
    const pnlPct = document.getElementById('val-pnl-pct');
    const isPositive = state.day_pnl >= 0;
    
    pnlVal.textContent = `₹${state.day_pnl.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;
    pnlVal.className = `card-value text-mono ${isPositive ? 'positive' : 'negative'}`;
    
    const pct = ((state.day_pnl / (state.equity - state.day_pnl)) * 100).toFixed(2);
    pnlPct.textContent = `${isPositive ? '+' : ''}${pct}%`;
    pnlPct.className = `card-footer ${isPositive ? 'positive' : 'negative'}`;

    document.getElementById('val-trades').textContent = state.positions.length;

    // 3. Tables & Lists
    renderPositions();
    renderSignals();
    updateChart();
}

function renderPositions() {
    const tableBody = document.getElementById('position-table-body');
    const emptyState = document.getElementById('position-empty');

    if (!state.positions || state.positions.length === 0) {
        tableBody.innerHTML = '';
        emptyState.style.display = 'block';
        return;
    }

    emptyState.style.display = 'none';
    tableBody.innerHTML = state.positions.map(p => `
        <tr>
            <td class="symbol-col">${p.symbol}</td>
            <td><span class="direction-badge ${p.direction.toLowerCase()}">${p.direction}</span></td>
            <td class="text-mono">${p.quantity}</td>
            <td class="text-mono">₹${p.entry.toLocaleString()}</td>
            <td class="text-mono">₹${p.ltp.toLocaleString()}</td>
            <td class="text-mono ${p.pnl >= 0 ? 'positive' : 'negative'}">
                ₹${p.pnl.toLocaleString()}
            </td>
            <td><span class="status-badge ${p.pnl >= 0 ? 'open' : 'closed'}">ACTIVE</span></td>
        </tr>
    `).join('');
}

function renderSignals() {
    const list = document.getElementById('signal-list');
    if (!state.signals || state.signals.length === 0) {
        list.innerHTML = '<div class="empty-state">Waiting for alpha...</div>';
        return;
    }

    list.innerHTML = state.signals.map(s => `
        <div class="activity-item">
            <div class="activity-icon ${s.type === 'LONG' ? 'positive' : 'negative'}">
                <i data-lucide="${s.type === 'LONG' ? 'arrow-up-right' : 'arrow-down-right'}"></i>
            </div>
            <div class="activity-content">
                <div style="font-weight: 600;">${s.symbol} <span class="small text-secondary">${s.strategy}</span></div>
                <div class="small text-secondary">${s.time} • Confidence: ${s.confidence}%</div>
            </div>
        </div>
    `).join('');
    lucide.createIcons();
}

// ═══════════════════════════════════════════════════════════════
// INTERACTIVE ELEMENTS
// ═══════════════════════════════════════════════════════════════

function setupEventListeners() {
    // Mode Toggle
    document.getElementById('mode-toggle').addEventListener('change', async (e) => {
        const newMode = e.target.checked ? 'real' : 'paper';
        await callApi(`/mode?mode=${newMode}`, 'POST');
    });

    // Halt Button
    document.getElementById('halt-button').addEventListener('click', async () => {
        if (confirm('🚨 EMERGENCY SHUTDOWN: Are you sure you want to stop all trading?')) {
            await callApi('/halt', 'POST');
        }
    });

    // Nav Items
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', () => {
            document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
            item.classList.add('active');
            const view = item.getAttribute('data-view');
            document.getElementById('view-title').textContent = item.querySelector('span').textContent;
        });
    });
}

// ═══════════════════════════════════════════════════════════════
// CHARTS & UTILS
// ═══════════════════════════════════════════════════════════════

function initChart() {
    const ctx = document.getElementById('equityChart').getContext('2d');
    const gradient = ctx.createLinearGradient(0, 0, 0, 400);
    gradient.addColorStop(0, 'rgba(0, 210, 255, 0.2)');
    gradient.addColorStop(1, 'rgba(0, 210, 255, 0)');

    equityChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Equity (₹)',
                data: [],
                borderColor: '#00d2ff',
                backgroundColor: gradient,
                fill: true,
                tension: 0.4,
                borderWidth: 3,
                pointRadius: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { display: false },
                y: {
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: { color: '#8b949e', font: { family: 'JetBrains Mono', size: 10 } }
                }
            }
        }
    });
}

function updateChart() {
    if (!equityChart) return;
    
    // Simple mock history for visualization if none exists
    if (state.history.length === 0) {
        let val = state.equity - 500;
        for (let i = 0; i < 20; i++) {
            state.history.push(val + Math.random() * 50);
            val += 20;
        }
    }

    equityChart.data.labels = state.history.map((_, i) => i);
    equityChart.data.datasets[0].data = state.history;
    equityChart.update('none');
}

function startTimeUpdate() {
    const timeEl = document.getElementById('ist-time');
    setInterval(() => {
        const now = new Date();
        const istTime = now.toLocaleTimeString('en-US', { 
            timeZone: 'Asia/Kolkata', 
            hour12: false 
        });
        timeEl.textContent = istTime;
    }, 1000);
}
