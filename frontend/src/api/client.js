const API_BASE = (import.meta.env.VITE_API_URL ? import.meta.env.VITE_API_URL.replace(/\/$/, '') : '') + '/api';

const TOKEN_KEY = 'command_centre_access_token';

export function getStoredToken() {
  return localStorage.getItem(TOKEN_KEY) || '';
}

export function setStoredToken(token) {
  if (token) {
    localStorage.setItem(TOKEN_KEY, token.trim());
  } else {
    localStorage.removeItem(TOKEN_KEY);
  }
}

export function clearStoredToken() {
  localStorage.removeItem(TOKEN_KEY);
}

export function getAuthHeaders() {
  const token = getStoredToken();
  return token ? { 'Authorization': `Bearer ${token}` } : {};
}

export async function fetchAuthStatus() {
  try {
    const res = await fetch(`${API_BASE}/auth/status`);
    if (!res.ok) return { auth_required: false };
    return res.json();
  } catch (err) {
    return { auth_required: false };
  }
}

export async function verifyAuthToken(token) {
  const res = await fetch(`${API_BASE}/auth/verify`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ token: token.trim() })
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || 'Invalid access passcode');
  }
  return res.json();
}

async function authFetch(url, options = {}) {
  const headers = {
    ...getAuthHeaders(),
    ...(options.headers || {})
  };
  const res = await fetch(url, { ...options, headers });
  if (res.status === 401) {
    window.dispatchEvent(new CustomEvent('command_centre_unauthorized'));
  }
  return res;
}

export async function fetchDailyMetrics(dateStr) {
  const res = await authFetch(`${API_BASE}/metrics/${dateStr}`);
  if (!res.ok) throw new Error(`Failed to load metrics: ${res.statusText}`);
  return res.json();
}

export async function syncGarmin(dateStr, forceDemo = false) {
  const res = await authFetch(`${API_BASE}/garmin/sync`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ date: dateStr, force_demo: forceDemo })
  });
  if (!res.ok) throw new Error(`Failed to sync Garmin data: ${res.statusText}`);
  return res.json();
}

export async function fetchGarminStatus() {
  const res = await authFetch(`${API_BASE}/garmin/status`);
  if (!res.ok) throw new Error(`Failed to get Garmin status: ${res.statusText}`);
  return res.json();
}

export async function fetchLLMStatus() {
  const res = await authFetch(`${API_BASE}/llm/status`);
  if (!res.ok) throw new Error(`Failed to get LLM status: ${res.statusText}`);
  return res.json();
}

export async function submitJournalEntry(dateStr, rawText) {
  const res = await authFetch(`${API_BASE}/journal`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ date: dateStr, raw_text: rawText })
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to submit journal entry: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchJournalEntriesForDate(dateStr) {
  const res = await authFetch(`${API_BASE}/journal/${dateStr}`);
  if (!res.ok) throw new Error(`Failed to get journal entries: ${res.statusText}`);
  return res.json();
}

export async function deleteJournalEntry(entryId) {
  const res = await authFetch(`${API_BASE}/journal/${entryId}`, {
    method: 'DELETE'
  });
  if (!res.ok) throw new Error(`Failed to delete journal entry: ${res.statusText}`);
  return res.json();
}

export async function fetchPeople(search = '', tag = '') {
  const params = new URLSearchParams();
  if (search) params.append('search', search);
  if (tag) params.append('tag', tag);
  const res = await authFetch(`${API_BASE}/people?${params.toString()}`);
  if (!res.ok) throw new Error(`Failed to load people directory: ${res.statusText}`);
  return res.json();
}

export async function fetchPersonDetail(personId) {
  const res = await authFetch(`${API_BASE}/people/${personId}`);
  if (!res.ok) throw new Error(`Failed to load person profile: ${res.statusText}`);
  return res.json();
}

export async function updatePerson(personId, data) {
  const res = await authFetch(`${API_BASE}/people/${personId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });
  if (!res.ok) throw new Error(`Failed to update person: ${res.statusText}`);
  return res.json();
}

export async function deletePerson(personId) {
  const res = await authFetch(`${API_BASE}/people/${personId}`, {
    method: 'DELETE'
  });
  if (!res.ok) throw new Error(`Failed to delete person: ${res.statusText}`);
  return res.json();
}

export async function seedDemoData() {
  const res = await authFetch(`${API_BASE}/seed`, {
    method: 'POST'
  });
  if (!res.ok) throw new Error(`Failed to seed demo data: ${res.statusText}`);
  return res.json();
}

// ----------------- UNIVERSITY API -----------------

export async function fetchModules() {
  const res = await authFetch(`${API_BASE}/modules`);
  if (!res.ok) throw new Error(`Failed to load modules: ${res.statusText}`);
  return res.json();
}

export async function createModule(data) {
  const res = await authFetch(`${API_BASE}/modules`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to create module: ${res.statusText}`);
  }
  return res.json();
}

export async function deleteModule(moduleId) {
  const res = await authFetch(`${API_BASE}/modules/${moduleId}`, {
    method: 'DELETE'
  });
  if (!res.ok) throw new Error(`Failed to delete module: ${res.statusText}`);
  return res.json();
}

export async function fetchDeadlines(moduleId = null, status = null) {
  const params = new URLSearchParams();
  if (moduleId) params.append('module_id', moduleId);
  if (status) params.append('status', status);
  const res = await authFetch(`${API_BASE}/deadlines?${params.toString()}`);
  if (!res.ok) throw new Error(`Failed to load deadlines: ${res.statusText}`);
  return res.json();
}

export async function createDeadline(data) {
  const res = await authFetch(`${API_BASE}/deadlines`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to create deadline: ${res.statusText}`);
  }
  return res.json();
}

export async function updateDeadline(deadlineId, data) {
  const res = await authFetch(`${API_BASE}/deadlines/${deadlineId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });
  if (!res.ok) throw new Error(`Failed to update deadline: ${res.statusText}`);
  return res.json();
}

export async function deleteDeadline(deadlineId) {
  const res = await authFetch(`${API_BASE}/deadlines/${deadlineId}`, {
    method: 'DELETE'
  });
  if (!res.ok) throw new Error(`Failed to delete deadline: ${res.statusText}`);
  return res.json();
}

export async function fetchAcademicTasks(moduleId = null, status = null) {
  const params = new URLSearchParams();
  if (moduleId) params.append('module_id', moduleId);
  if (status) params.append('status', status);
  const res = await authFetch(`${API_BASE}/tasks?${params.toString()}`);
  if (!res.ok) throw new Error(`Failed to load tasks: ${res.statusText}`);
  return res.json();
}

export async function createAcademicTask(data) {
  const res = await authFetch(`${API_BASE}/tasks`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });
  if (!res.ok) throw new Error(`Failed to create task: ${res.statusText}`);
  return res.json();
}

export async function updateAcademicTask(taskId, data) {
  const res = await authFetch(`${API_BASE}/tasks/${taskId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });
  if (!res.ok) throw new Error(`Failed to update task: ${res.statusText}`);
  return res.json();
}

export async function deleteAcademicTask(taskId) {
  const res = await authFetch(`${API_BASE}/tasks/${taskId}`, {
    method: 'DELETE'
  });
  if (!res.ok) throw new Error(`Failed to delete task: ${res.statusText}`);
  return res.json();
}

// ----------------- CHAT API -----------------

export async function sendChatMessage(message, history = []) {
  const res = await authFetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, history })
  });
  if (!res.ok) throw new Error(`Chat error: ${res.statusText}`);
  return res.json();
}

export async function streamChatMessage(message, history = [], { onTools, onDelta, onCitations, onDone, onError }) {
  try {
    const res = await authFetch(`${API_BASE}/chat/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, history })
    });

    if (!res.ok) throw new Error(`Stream error: ${res.statusText}`);

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n\n');
      buffer = lines.pop() || '';

      for (const block of lines) {
        if (!block.trim()) continue;
        const eventMatch = block.match(/event:\s*([^\n]+)/);
        const dataMatch = block.match(/data:\s*([^\n]+)/);

        const event = eventMatch ? eventMatch[1].trim() : 'message';
        const dataStr = dataMatch ? dataMatch[1].trim() : '{}';

        try {
          const data = JSON.parse(dataStr);
          if (event === 'tools' && onTools) onTools(data.tools || []);
          if (event === 'delta' && onDelta) onDelta(data.text || '');
          if (event === 'citations' && onCitations) onCitations(data.citations || []);
          if (event === 'done' && onDone) onDone();
        } catch (e) {
          console.warn('Could not parse SSE block:', block, e);
        }
      }
    }
    if (onDone) onDone();
  } catch (err) {
    if (onError) onError(err);
  }
}

// ----------------- TIMETABLE & SCHEDULE -----------------

export async function fetchTimetable(params = {}) {
  const query = new URLSearchParams();
  if (params.date) query.append('date', params.date);
  if (params.start_date) query.append('start_date', params.start_date);
  if (params.end_date) query.append('end_date', params.end_date);
  if (params.module_code) query.append('module_code', params.module_code);
  if (params.source) query.append('source', params.source);
  if (params.upcoming_only) query.append('upcoming_only', 'true');
  query.append('limit', String(params.limit || 2500));

  const res = await authFetch(`${API_BASE}/timetable?${query.toString()}`);
  if (!res.ok) throw new Error(`Failed to load timetable: ${res.statusText}`);
  return res.json();
}

export async function updateTimetableEvent(id, data) {
  const res = await authFetch(`${API_BASE}/timetable/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });
  if (!res.ok) throw new Error(`Failed to update event: ${res.statusText}`);
  return res.json();
}

export async function syncTimetableIcal(icalUrl = null, sourceName = null) {
  const body = {};
  if (icalUrl) body.ical_url = icalUrl;
  if (sourceName) body.source_name = sourceName;

  const res = await authFetch(`${API_BASE}/timetable/sync/ical`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  });
  if (!res.ok) throw new Error(`Failed to sync iCal feeds: ${res.statusText}`);
  return res.json();
}

export async function syncTimetableMongo(mongoUri = null) {
  const body = {};
  if (mongoUri) body.mongodb_uri = mongoUri;

  const res = await authFetch(`${API_BASE}/timetable/sync/mongodb`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  });
  if (!res.ok) throw new Error(`Failed to import from MongoDB: ${res.statusText}`);
  return res.json();
}

export async function fetchTimetableStatus() {
  const res = await authFetch(`${API_BASE}/timetable/status`);
  if (!res.ok) throw new Error(`Failed to get timetable status: ${res.statusText}`);
  return res.json();
}

export async function createManualTimetableEvent(data) {
  const res = await authFetch(`${API_BASE}/timetable`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });
  if (!res.ok) throw new Error(`Failed to create timetable event: ${res.statusText}`);
  return res.json();
}

export async function deleteTimetableEvent(id) {
  const res = await authFetch(`${API_BASE}/timetable/${id}`, {
    method: 'DELETE'
  });
  if (!res.ok) throw new Error(`Failed to delete timetable event: ${res.statusText}`);
  return res.json();
}

// ----------------- UNIFIED ASSIGNMENTS API (Personal Dashboard Compat) -----------------

export async function fetchAssignments() {
  const res = await authFetch(`${API_BASE}/assignments`);
  if (!res.ok) throw new Error(`Failed to load assignments: ${res.statusText}`);
  return res.json();
}

export async function updateAssignment(id, data) {
  const res = await authFetch(`${API_BASE}/assignments/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });
  if (!res.ok) throw new Error(`Failed to update assignment: ${res.statusText}`);
  return res.json();
}

export async function deleteAssignment(id) {
  const res = await authFetch(`${API_BASE}/assignments/${id}`, {
    method: 'DELETE'
  });
  if (!res.ok) throw new Error(`Failed to delete assignment: ${res.statusText}`);
  return res.json();
}

export async function createAssignment(data) {
  const res = await authFetch(`${API_BASE}/assignments`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });
  if (!res.ok) throw new Error(`Failed to create assignment: ${res.statusText}`);
  return res.json();
}

export async function syncCalendars() {
  const res = await authFetch(`${API_BASE}/calendar/sync`, {
    method: 'POST'
  });
  if (!res.ok) throw new Error(`Failed to sync calendars: ${res.statusText}`);
  return res.json();
}

