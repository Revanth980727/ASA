import React, { useState, useEffect } from 'react';
import './App.css';

const API_BASE_URL = 'http://localhost:8000';

function App() {
  const [repoUrl, setRepoUrl] = useState('');
  const [bugDescription, setBugDescription] = useState('');
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [selectedTask, setSelectedTask] = useState(null);
  const [feedbackModal, setFeedbackModal] = useState(null);
  const [expandedLogs, setExpandedLogs] = useState({});

  // Fetch tasks on component mount and periodically
  useEffect(() => {
    fetchTasks();
    const interval = setInterval(fetchTasks, 5000); // Poll every 5 seconds
    return () => clearInterval(interval);
  }, []);

  const fetchTasks = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/task`);
      if (response.ok) {
        const data = await response.json();
        setTasks(data);
      }
    } catch (err) {
      console.error('Error fetching tasks:', err);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setSuccess(null);

    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/task/submit`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          repo_url: repoUrl,
          bug_description: bugDescription,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        setSuccess(`Task submitted successfully! Task ID: ${data.task_id}`);
        setRepoUrl('');
        setBugDescription('');
        fetchTasks(); // Refresh task list
      } else {
        const errorData = await response.json();
        setError(errorData.detail || 'Failed to submit task');
      }
    } catch (err) {
      setError('Network error: Could not connect to the server');
    } finally {
      setLoading(false);
    }
  };

  const getStatusClass = (status) => {
    return status.toLowerCase().replace(/_/g, '-');
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleString();
  };

  const openFeedbackModal = (task) => {
    setFeedbackModal({
      taskId: task.task_id,
      rating: 3,
      approved: false,
      comment: '',
      issues: []
    });
  };

  const submitFeedback = async () => {
    if (!feedbackModal) return;

    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/task/${feedbackModal.taskId}/feedback`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          rating: feedbackModal.rating,
          approved: feedbackModal.approved,
          comment: feedbackModal.comment,
          issues: feedbackModal.issues
        }),
      });

      if (response.ok) {
        setSuccess('Feedback submitted successfully!');
        setFeedbackModal(null);
        fetchTasks();
      } else {
        const errorData = await response.json();
        setError(errorData.detail || 'Failed to submit feedback');
      }
    } catch (err) {
      setError('Network error: Could not submit feedback');
    }
  };

  const toggleLogs = (taskId) => {
    setExpandedLogs(prev => ({
      ...prev,
      [taskId]: !prev[taskId]
    }));
  };

  const cancelTask = async (taskId) => {
    if (!window.confirm('Are you sure you want to delete this task? This will remove it from the database and cancel any running jobs.')) return;

    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/task/${taskId}/cancel`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (response.ok) {
        setSuccess('Task deleted successfully!');
        fetchTasks();
      } else {
        const errorData = await response.json();
        setError(errorData.detail || 'Failed to delete task');
      }
    } catch (err) {
      setError('Network error: Could not cancel task');
    }
  };

  return (
    <div className="app">
      <div className="header">
        <h1>ASA MVP - Autonomous Bug Fixer</h1>
        <p>Submit a bug fix task for a repository</p>
      </div>

      <div className="form-section">
        <h2>Submit Bug Fix Task</h2>
        {error && <div className="error-message">{error}</div>}
        {success && <div className="success-message">{success}</div>}
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="repo_url">Repository URL</label>
            <input
              type="text"
              id="repo_url"
              value={repoUrl}
              onChange={(e) => setRepoUrl(e.target.value)}
              placeholder="https://github.com/user/repo.git"
              required
            />
          </div>
          <div className="form-group">
            <label htmlFor="bug_description">Bug Description</label>
            <textarea
              id="bug_description"
              value={bugDescription}
              onChange={(e) => setBugDescription(e.target.value)}
              placeholder="Describe the bug you want to fix..."
              required
            />
          </div>
          <button
            type="submit"
            className="submit-button"
            disabled={loading}
          >
            {loading ? 'Submitting...' : 'Submit Bug Fix Task'}
          </button>
        </form>
      </div>

      <div className="tasks-section">
        <h2>Tasks</h2>
        {tasks.length === 0 ? (
          <div className="loading">No tasks yet. Submit a task to get started!</div>
        ) : (
          <ul className="tasks-list">
            {tasks.map((task) => {
              // Handle both 'id' and 'task_id' field names
              const taskId = task.task_id || task.id;
              return (
                <li key={taskId} className="task-item">
                  <div className="task-header">
                    <span className="task-id">ID: {taskId ? taskId.substring(0, 8) : 'Unknown'}...</span>
                    <span className={`status ${getStatusClass(task.status || 'unknown')}`}>
                      {task.status || 'UNKNOWN'}
                    </span>
                  </div>
                  <div className="task-repo">{task.repo_url || 'No repo URL'}</div>
                  <div className="task-bug">{task.bug_description || 'No description'}</div>
                  {task.pr_url && (
                    <div className="task-pr">
                      <a href={task.pr_url} target="_blank" rel="noopener noreferrer">
                        View Pull Request
                      </a>
                    </div>
                  )}
                  <div className="task-meta">
                    Created: {task.created_at ? formatDate(task.created_at) : 'N/A'} |
                    Updated: {task.updated_at ? formatDate(task.updated_at) : 'N/A'}
                  </div>

                  {/* Logs Section */}
                  {task.logs && (
                    <div className="task-logs">
                      <button
                        className="logs-toggle"
                        onClick={() => toggleLogs(taskId)}
                      >
                        {expandedLogs[taskId] ? '▼ Hide Logs' : '▶ View Logs'}
                      </button>
                      {expandedLogs[taskId] && (
                        <pre className="logs-content">
                          {task.logs || 'No logs available yet...'}
                        </pre>
                      )}
                    </div>
                  )}

                  <div className="task-actions">
                    {task.status === 'COMPLETED' && (
                      <button
                        className="feedback-button"
                        onClick={() => openFeedbackModal(task)}
                      >
                        Give Feedback
                      </button>
                    )}
                    <button
                      className="cancel-button"
                      onClick={() => cancelTask(taskId)}
                      title={task.status === 'COMPLETED' || task.status === 'FAILED' ? 'Delete task and history' : 'Cancel and delete task'}
                    >
                      {['COMPLETED', 'FAILED'].includes(task.status) ? 'Delete' : 'Cancel'}
                    </button>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </div>

      {/* Feedback Modal */}
      {feedbackModal && (
        <div className="modal-overlay" onClick={() => setFeedbackModal(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h2>Submit Feedback</h2>
            <div className="feedback-form">
              <div className="form-group">
                <label>Rating (1-5)</label>
                <div className="rating-stars">
                  {[1, 2, 3, 4, 5].map((star) => (
                    <span
                      key={star}
                      className={`star ${star <= feedbackModal.rating ? 'active' : ''}`}
                      onClick={() => setFeedbackModal({ ...feedbackModal, rating: star })}
                    >
                      ★
                    </span>
                  ))}
                </div>
              </div>

              <div className="form-group">
                <label>
                  <input
                    type="checkbox"
                    checked={feedbackModal.approved}
                    onChange={(e) => setFeedbackModal({ ...feedbackModal, approved: e.target.checked })}
                  />
                  I approve this fix
                </label>
              </div>

              <div className="form-group">
                <label>Comment (optional)</label>
                <textarea
                  value={feedbackModal.comment}
                  onChange={(e) => setFeedbackModal({ ...feedbackModal, comment: e.target.value })}
                  placeholder="Any additional feedback..."
                  rows="4"
                />
              </div>

              <div className="modal-actions">
                <button className="submit-button" onClick={submitFeedback}>
                  Submit Feedback
                </button>
                <button className="cancel-button" onClick={() => setFeedbackModal(null)}>
                  Cancel
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;

