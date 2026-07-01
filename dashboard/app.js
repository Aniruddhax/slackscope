/**
 * SlackScope Dashboard — Frontend Application
 * Fetches data from API, renders charts, cards, and real-time updates.
 */

const API_BASE = window.location.origin + '/api';
const REFRESH_INTERVAL = 60000; // 60 seconds

let trendChart = null;
let heatmapChart = null;
let sentimentChart = null;

// ── Initialize ──────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    refreshData();
    setInterval(refreshData, REFRESH_INTERVAL);
});

// ── Main Refresh ────────────────────────────────────
async function refreshData() {
    const btn = document.getElementById('refreshBtn');
    btn.classList.add('loading');

    try {
        const [health, trends, team, alerts] = await Promise.all([
            fetchJSON('/api/health'),
            fetchJSON('/api/trends'),
            fetchJSON('/api/team'),
            fetchJSON('/api/alerts'),
        ]);

        renderStats(health);
        renderChannelCards(health.channels || []);
        renderTrendChart(trends);
        renderHeatmap(team.activity_hours || {});
        renderSentimentChart(health.channels || []);
        renderAlerts(alerts.alerts || []);
        renderTeamLeaderboard(team.leaderboard || []);

        document.getElementById('lastUpdate').textContent =
            `Last updated: ${new Date().toLocaleTimeString()}`;
    } catch (err) {
        console.error('Refresh failed:', err);
    } finally {
        btn.classList.remove('loading');
    }
}

async function fetchJSON(url) {
    try {
        const res = await fetch(url);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return await res.json();
    } catch (e) {
        console.warn(`Fetch ${url} failed:`, e);
        return {};
    }
}

// ── Stats Bar ───────────────────────────────────────
function renderStats(health) {
    const channels = health.channels || [];
    const scores = channels.map(c => c.score || 0);
    const avg = scores.length ? Math.round(scores.reduce((a, b) => a + b, 0) / scores.length) : 0;
    const totalBlockers = channels.reduce((sum, c) => sum + (c.blocker_count || 0), 0);

    animateNumber('avgScore', avg);
    animateNumber('channelCount', channels.length);
    animateNumber('totalBlockers', totalBlockers);
    animateNumber('alertCount', health.alert_count || 0);
}

function animateNumber(id, target) {
    const el = document.getElementById(id);
    const current = parseInt(el.textContent) || 0;
    const diff = target - current;
    const steps = 20;
    const stepVal = diff / steps;
    let step = 0;

    const timer = setInterval(() => {
        step++;
        if (step >= steps) {
            el.textContent = target;
            clearInterval(timer);
        } else {
            el.textContent = Math.round(current + stepVal * step);
        }
    }, 30);
}

// ── Channel Cards ───────────────────────────────────
function renderChannelCards(channels) {
    const container = document.getElementById('channelCards');

    if (!channels.length) {
        container.innerHTML = '<div class="loading-placeholder">No channels monitored yet. Use <code>/slackscope report</code> to start.</div>';
        return;
    }

    container.innerHTML = channels.map(ch => {
        const score = ch.score || 0;
        const status = ch.status || 'yellow';
        const statusEmoji = { green: '🟢', yellow: '🟡', red: '🔴' }[status] || '⚪';
        const circumference = 2 * Math.PI * 34;
        const offset = circumference - (score / 100) * circumference;
        const strokeColor = { green: '#10b981', yellow: '#f59e0b', red: '#ef4444' }[status] || '#6366f1';
        const change = ch.score_change || 0;
        const changeIcon = change > 0 ? `📈+${change}` : change < 0 ? `📉${change}` : '➡️0';

        return `
            <div class="channel-card status-${status}">
                <div class="channel-header">
                    <span class="channel-name">#${ch.name}</span>
                    <span class="channel-status">${statusEmoji}</span>
                </div>
                <div class="score-ring">
                    <svg width="80" height="80" viewBox="0 0 80 80">
                        <circle class="bg-circle" cx="40" cy="40" r="34"/>
                        <circle class="progress-circle" cx="40" cy="40" r="34"
                            stroke="${strokeColor}"
                            stroke-dasharray="${circumference}"
                            stroke-dashoffset="${offset}"/>
                    </svg>
                    <span class="score-text">${score}</span>
                </div>
                <div class="channel-metrics">
                    <div class="metric-item">💬 ${ch.sentiment || 'neutral'}</div>
                    <div class="metric-item">📊 ${ch.activity || 'unknown'}</div>
                    <div class="metric-item">🚧 ${ch.blocker_count || 0} blockers</div>
                    <div class="metric-item">${changeIcon}</div>
                </div>
            </div>
        `;
    }).join('');
}

// ── Trend Chart ─────────────────────────────────────
function renderTrendChart(trends) {
    const ctx = document.getElementById('trendChart').getContext('2d');
    const channels = trends.channels || {};
    const channelNames = Object.keys(channels);

    if (!channelNames.length) return;

    const colors = ['#6366f1', '#8b5cf6', '#10b981', '#f59e0b', '#ef4444', '#ec4899'];
    const datasets = channelNames.map((name, i) => {
        const entries = channels[name] || [];
        return {
            label: `#${name}`,
            data: entries.map(e => e.score),
            borderColor: colors[i % colors.length],
            backgroundColor: colors[i % colors.length] + '20',
            fill: true,
            tension: 0.4,
            pointRadius: 3,
            pointHoverRadius: 6,
            borderWidth: 2,
        };
    });

    // Use labels from first channel
    const firstChannel = channels[channelNames[0]] || [];
    const labels = firstChannel.map(e => {
        const d = new Date(e.timestamp);
        return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    });

    if (trendChart) trendChart.destroy();

    trendChart = new Chart(ctx, {
        type: 'line',
        data: { labels, datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    labels: { color: '#94a3b8', font: { family: 'Inter', size: 12 } }
                },
            },
            scales: {
                y: {
                    min: 0, max: 100,
                    grid: { color: 'rgba(255,255,255,0.04)' },
                    ticks: { color: '#64748b', font: { family: 'Inter' } },
                },
                x: {
                    grid: { color: 'rgba(255,255,255,0.04)' },
                    ticks: { color: '#64748b', font: { family: 'Inter' }, maxTicksLimit: 8 },
                },
            },
        },
    });
}

// ── Activity Heatmap ────────────────────────────────
function renderHeatmap(activityHours) {
    const ctx = document.getElementById('heatmapChart').getContext('2d');
    const channels = Object.keys(activityHours);

    if (!channels.length) return;

    // Aggregate all channels
    const hourTotals = new Array(24).fill(0);
    for (const ch of channels) {
        const hours = activityHours[ch] || [];
        hours.forEach((count, i) => { hourTotals[i] += count; });
    }

    const labels = Array.from({ length: 24 }, (_, i) => `${i.toString().padStart(2, '0')}:00`);
    const maxVal = Math.max(...hourTotals, 1);

    const colors = hourTotals.map(v => {
        const intensity = v / maxVal;
        if (intensity > 0.7) return 'rgba(99, 102, 241, 0.9)';
        if (intensity > 0.4) return 'rgba(99, 102, 241, 0.5)';
        if (intensity > 0) return 'rgba(99, 102, 241, 0.2)';
        return 'rgba(255, 255, 255, 0.03)';
    });

    if (heatmapChart) heatmapChart.destroy();

    heatmapChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels,
            datasets: [{
                label: 'Messages',
                data: hourTotals,
                backgroundColor: colors,
                borderRadius: 4,
                borderSkipped: false,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
            },
            scales: {
                y: {
                    grid: { color: 'rgba(255,255,255,0.04)' },
                    ticks: { color: '#64748b', font: { family: 'Inter' } },
                },
                x: {
                    grid: { display: false },
                    ticks: { color: '#64748b', font: { family: 'Inter', size: 10 }, maxRotation: 0 },
                },
            },
        },
    });
}

// ── Sentiment Chart ─────────────────────────────────
function renderSentimentChart(channels) {
    const ctx = document.getElementById('sentimentChart').getContext('2d');

    const sentimentCounts = { positive: 0, neutral: 0, negative: 0, mixed: 0 };
    channels.forEach(ch => {
        const s = ch.sentiment || 'neutral';
        sentimentCounts[s] = (sentimentCounts[s] || 0) + 1;
    });

    const labels = Object.keys(sentimentCounts).filter(k => sentimentCounts[k] > 0);
    const data = labels.map(k => sentimentCounts[k]);
    const colors = {
        positive: '#10b981',
        neutral: '#6366f1',
        negative: '#ef4444',
        mixed: '#f59e0b',
    };

    if (sentimentChart) sentimentChart.destroy();

    sentimentChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels.map(l => l.charAt(0).toUpperCase() + l.slice(1)),
            datasets: [{
                data,
                backgroundColor: labels.map(l => colors[l] || '#64748b'),
                borderWidth: 0,
                hoverOffset: 8,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '65%',
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { color: '#94a3b8', font: { family: 'Inter', size: 12 }, padding: 16 },
                },
            },
        },
    });
}

// ── Alerts Feed ─────────────────────────────────────
function renderAlerts(alerts) {
    const container = document.getElementById('alertsFeed');

    if (!alerts.length) {
        container.innerHTML = '<div class="loading-placeholder">✅ No active alerts — all channels healthy!</div>';
        return;
    }

    container.innerHTML = alerts.slice(0, 10).map(alert => {
        const time = new Date(alert.timestamp).toLocaleString();
        const emoji = alert.type === 'critical_health' ? '🔴' :
                      alert.type === 'blocker_alert' ? '🚧' :
                      alert.type === 'score_drop' ? '📉' :
                      alert.type === 'negative_sentiment' ? '😟' : '💤';

        return `
            <div class="alert-item">
                <span class="alert-emoji">${emoji}</span>
                <div class="alert-content">
                    <div class="alert-title">${alert.title || alert.type}</div>
                    <div class="alert-message">${alert.message || ''}</div>
                    <div class="alert-time">${time}</div>
                </div>
            </div>
        `;
    }).join('');
}

// ── Team Leaderboard ────────────────────────────────
function renderTeamLeaderboard(leaderboard) {
    const container = document.getElementById('teamLeaderboard');

    if (!leaderboard.length) {
        container.innerHTML = '<div class="loading-placeholder">Run /slackscope team to generate team data</div>';
        return;
    }

    const maxMsgs = Math.max(...leaderboard.map(m => m.count || 1), 1);
    const rankClasses = ['gold', 'silver', 'bronze'];

    container.innerHTML = leaderboard.slice(0, 8).map((member, i) => {
        const rankClass = i < 3 ? rankClasses[i] : '';
        const initial = (member.user || 'U').charAt(0).toUpperCase();
        const pct = Math.round(((member.count || 0) / maxMsgs) * 100);

        return `
            <div class="team-member">
                <span class="team-rank ${rankClass}">${i + 1}</span>
                <div class="team-avatar">${initial}</div>
                <div class="team-info">
                    <div class="team-name">${member.user || 'Unknown'}</div>
                    <div class="team-stat">${member.count || 0} messages</div>
                </div>
                <div class="team-bar">
                    <div class="team-bar-fill" style="width: ${pct}%"></div>
                </div>
            </div>
        `;
    }).join('');
}
