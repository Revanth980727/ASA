// ASA Frontend Application
const API_BASE = 'http://localhost:8000/api/v1';
const WS_BASE = 'ws://localhost:8000/api/v1';

// WebSocket connections for active tasks
const activeWebSockets = new Map();

// Initialize dashboard
async function initDashboard() {
    console.log('Initializing ASA Dashboard...');

    // Load initial data
    await loadMetrics();
    await loadRecentTasks();

    // Start periodic updates
    setInterval(loadMetrics, 30000);  // Update metrics every 30s
    setInterval(loadRecentTasks, 10000);  // Update tasks every 10s
}

// Load metrics
async function loadMetrics() {
    try {
        const response = await fetch(`${API_BASE}/metrics?time_window_hours=24`);
        const data = await response.json();

        document.getElementById('stat-total').textContent = data.total_tasks;
        document.getElementById('stat-completed').textContent = data.completed;
        document.getElementById('stat-failed').textContent = data.failed;
        document.getElementById('stat-success-rate').textContent =
            `${data.success_rate.toFixed(1)}%`;
    } catch (error) {
        console.error('Failed to load metrics:', error);
    }
}

// Load recent tasks
async function loadRecentTasks() {
    try {
        const response = await fetch(`${API_BASE}/task`);
        const tasks = await response.json();

        // Split into active and completed
        const activeTasks = tasks.filter(t =>
            !['COMPLETED', 'FAILED', 'TIMEOUT'].includes(t.status)
        );
        const recentTasks = tasks.slice(0, 10);

        renderActiveTasks(activeTasks);
        renderRecentTasks(recentTasks);
    } catch (error) {
        console.error('Failed to load tasks:', error);
    }
}

// Render active tasks
function renderActiveTasks(tasks) {
    const container = document.getElementById('active-tasks');

    if (tasks.length === 0) {
        container.innerHTML = '<p style="color: #666;">No active tasks</p>';
        return;
    }

    container.innerHTML = tasks.map(task => createTaskCard(task, true)).join('');

    // Setup WebSockets for active tasks
    tasks.forEach(task => setupWebSocket(task.task_id));
}

// Render recent tasks
function renderRecentTasks(tasks) {
    const container = document.getElementById('recent-tasks');

    if (tasks.length === 0) {
        container.innerHTML = '<p style="color: #666;">No tasks yet</p>';
        return;
    }

    container.innerHTML = tasks.map(task => createTaskCard(task, false)).join('');
}

// Create task card HTML
function createTaskCard(task, isActive) {
    const taskId = task.task_id || task.id;

    return `
        <div class="task-item" id="task-${taskId}">
            <div class="task-header">
                <span class="task-id">${taskId}</span>
                <span class="status-badge status-${task.status}">${task.status}</span>
            </div>

            ${isActive ? `
                <div class="progress-bar">
                    <div class="progress-fill" id="progress-${taskId}" style="width: 0%"></div>
                </div>
            ` : ''}

            <div style="margin: 10px 0;">
                <strong>Repository:</strong> ${task.repo_url}
            </div>

            <div id="details-${taskId}" class="hidden">
                <div style="margin: 10px 0;">
                    <strong>Description:</strong> ${task.bug_description || 'N/A'}
                </div>

                ${task.pr_url ? `
                    <a href="${task.pr_url}" target="_blank" class="pr-link">
                        🔗 View Pull Request
                    </a>
                ` : ''}

                ${task.branch_name ? `
                    <div style="margin: 10px 0;">
                        <strong>Branch:</strong> <code>${task.branch_name}</code>
                    </div>
                ` : ''}

                <div style="margin: 10px 0;">
                    <button class="btn btn-primary" onclick="showLogs('${taskId}')">
                        View Logs
                    </button>
                    ${task.status === 'COMPLETED' ? `
                        <button class="btn btn-success" onclick="showFeedback('${taskId}')">
                            ✓ Approve
                        </button>
                        <button class="btn btn-danger" onclick="showFeedback('${taskId}', false)">
                            ✗ Reject
                        </button>
                    ` : ''}
                </div>

                <div id="logs-${taskId}" class="hidden">
                    <h4>Execution Logs:</h4>
                    <div class="logs" id="logs-content-${taskId}">Loading...</div>
                </div>

                <div id="feedback-${taskId}" class="feedback-section hidden">
                    <h4>Submit Feedback (RLHF)</h4>
                    <div class="rating-stars" id="rating-${taskId}">
                        ${[1,2,3,4,5].map(i => `<span class="star" data-rating="${i}">★</span>`).join('')}
                    </div>
                    <textarea id="feedback-comment-${taskId}" placeholder="Optional feedback..."
                              style="width: 100%; margin: 10px 0; padding: 10px;"></textarea>
                    <button class="btn btn-primary" onclick="submitFeedback('${taskId}')">
                        Submit Feedback
                    </button>
                </div>
            </div>

            <button class="btn btn-primary" style="margin-top: 10px;"
                    onclick="toggleDetails('${taskId}')">
                Show Details
            </button>
        </div>
    `;
}

// Setup WebSocket for real-time updates
function setupWebSocket(taskId) {
    // Don't create duplicate connections
    if (activeWebSockets.has(taskId)) {
        return;
    }

    const ws = new WebSocket(`${WS_BASE}/ws/task/${taskId}`);

    ws.onopen = () => {
        console.log(`WebSocket connected for task ${taskId}`);
    };

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleWebSocketUpdate(taskId, data);
    };

    ws.onclose = () => {
        console.log(`WebSocket closed for task ${taskId}`);
        activeWebSockets.delete(taskId);
    };

    ws.onerror = (error) => {
        console.error(`WebSocket error for task ${taskId}:`, error);
    };

    activeWebSockets.set(taskId, ws);
}

// Handle WebSocket update
function handleWebSocketUpdate(taskId, data) {
    console.log(`Update for ${taskId}:`, data);

    // Update status badge
    const statusBadge = document.querySelector(`#task-${taskId} .status-badge`);
    if (statusBadge) {
        statusBadge.textContent = data.status;
        statusBadge.className = `status-badge status-${data.status}`;
    }

    // Update progress bar
    updateProgress(taskId, data.status);

    // If final state, close WebSocket and reload tasks
    if (data.type === 'final') {
        const ws = activeWebSockets.get(taskId);
        if (ws) {
            ws.close();
        }
        setTimeout(() => loadRecentTasks(), 1000);
    }
}

// Update progress bar based on status
function updateProgress(taskId, status) {
    const progressBar = document.getElementById(`progress-${taskId}`);
    if (!progressBar) return;

    const progressMap = {
        'QUEUED': 0,
        'INIT': 5,
        'CLONING_REPO': 10,
        'INDEXING_CODE': 20,
        'VERIFYING_BUG_BEHAVIOR': 30,
        'RUNNING_TESTS_BEFORE_FIX': 40,
        'GENERATING_FIX': 60,
        'RUNNING_TESTS_AFTER_FIX': 80,
        'VERIFYING_FIX_BEHAVIOR': 85,
        'CREATING_PR_BRANCH': 95,
        'COMPLETED': 100,
    };

    const progress = progressMap[status] || 0;
    progressBar.style.width = `${progress}%`;
}

// Toggle task details
function toggleDetails(taskId) {
    const details = document.getElementById(`details-${taskId}`);
    const button = event.target;

    if (details.classList.contains('hidden')) {
        details.classList.remove('hidden');
        button.textContent = 'Hide Details';
    } else {
        details.classList.add('hidden');
        button.textContent = 'Show Details';
    }
}

// Show logs
async function showLogs(taskId) {
    const logsDiv = document.getElementById(`logs-${taskId}`);
    const logsContent = document.getElementById(`logs-content-${taskId}`);

    if (logsDiv.classList.contains('hidden')) {
        logsDiv.classList.remove('hidden');

        // Fetch logs
        try {
            const response = await fetch(`${API_BASE}/task/${taskId}/logs`);
            const data = await response.json();
            logsContent.textContent = data.logs || 'No logs available';
        } catch (error) {
            logsContent.textContent = 'Failed to load logs';
        }
    } else {
        logsDiv.classList.add('hidden');
    }
}

// Show feedback form
function showFeedback(taskId, approved = true) {
    const feedbackDiv = document.getElementById(`feedback-${taskId}`);
    feedbackDiv.classList.toggle('hidden');

    // Setup star rating
    const stars = document.querySelectorAll(`#rating-${taskId} .star`);
    stars.forEach(star => {
        star.onclick = () => {
            const rating = parseInt(star.dataset.rating);
            stars.forEach((s, i) => {
                s.classList.toggle('active', i < rating);
            });
        };
    });
}

// Submit feedback
async function submitFeedback(taskId) {
    const stars = document.querySelectorAll(`#rating-${taskId} .star.active`);
    const rating = stars.length || 3;  // Default to 3 if not rated
    const comment = document.getElementById(`feedback-comment-${taskId}`).value;

    const feedback = {
        rating: rating,
        approved: rating >= 3,
        comment: comment,
        issues: []
    };

    try {
        const response = await fetch(`${API_BASE}/task/${taskId}/feedback`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(feedback)
        });

        if (response.ok) {
            alert('Thank you for your feedback!');
            document.getElementById(`feedback-${taskId}`).classList.add('hidden');
        } else {
            alert('Failed to submit feedback');
        }
    } catch (error) {
        console.error('Failed to submit feedback:', error);
        alert('Failed to submit feedback');
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', initDashboard);
