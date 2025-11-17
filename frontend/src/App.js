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
            {tasks.map((task) => (
              <li key={task.task_id} className="task-item">
                <div className="task-header">
                  <span className="task-id">ID: {task.task_id}</span>
                  <span className={`status ${getStatusClass(task.status)}`}>
                    {task.status}
                  </span>
                </div>
                <div className="task-repo">{task.repo_url}</div>
                <div className="task-meta">
                  Created: {formatDate(task.created_at)} | 
                  Updated: {formatDate(task.updated_at)}
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

export default App;

