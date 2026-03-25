const API_URL = '';

const getAuthHeaders = () => {
  const token = localStorage.getItem('inkognito_token');
  return token ? { 'Authorization': `Bearer ${token}` } : {};
};

const handleResponse = async (response) => {
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'Network response was not ok' }));
    throw new Error(errorData.detail || 'Something went wrong');
  }
  return response.json();
};

export const api = {
  async login(username, password) {
    const formData = new FormData();
    formData.append('username', username);
    formData.append('password', password);
    
    const data = await fetch(`${API_URL}/api/token`, {
      method: 'POST',
      body: formData,
    }).then(handleResponse);
    
    localStorage.setItem('inkognito_token', data.access_token);
    return data;
  },

  async register(username, password) {
    return fetch(`${API_URL}/api/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    }).then(handleResponse);
  },

  async logout() {
    localStorage.removeItem('inkognito_token');
  },

  async getCurrentUser() {
    return fetch(`${API_URL}/api/user`, {
      headers: getAuthHeaders(),
    }).then(handleResponse);
  },

  async runVerification(payload) {
    return fetch(`${API_URL}/api/run`, {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        ...getAuthHeaders()
      },
      body: JSON.stringify(payload),
    }).then(handleResponse);
  },

  async getJobStatus(jobId) {
    return fetch(`${API_URL}/api/jobs/${jobId}`, {
      headers: getAuthHeaders(),
    }).then(handleResponse);
  },

  async getReports() {
    return fetch(`${API_URL}/api/reports`, {
      headers: getAuthHeaders(),
    }).then(handleResponse);
  },

  async getHistoricalReport(reportId) {
    return fetch(`${API_URL}/api/jobs/report-${reportId}`, {
      headers: getAuthHeaders(),
    }).then(handleResponse);
  }
};
