import type {
  LabInfo,
  RunSummary,
  RunDetailsResponse,
  CandidateItem,
  EventLogItem,
  TimelineReportItem,
  LabLoginCredential,
  UserProfile,
  AuthResponse
} from './types';
const rawApiBase = import.meta.env.VITE_API_URL || 'http://localhost:8000';
export const API_BASE = rawApiBase.replace(/\/+$/, '');
export function getAuthToken(): string | null {
  return localStorage.getItem('phr_auth_token');
}

export function setAuthToken(token: string | null): void {
  if (token) {
    localStorage.setItem('phr_auth_token', token);
  } else {
    localStorage.removeItem('phr_auth_token');
  }
}

export function getAuthHeaders(extraHeaders: Record<string, string> = {}): Record<string, string> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...extraHeaders,
  };
  const token = getAuthToken();
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

export async function signup(payload: { name: string; email: string; password: string }): Promise<AuthResponse> {
  const res = await fetch(`${API_BASE}/api/auth/signup`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Signup failed' }));
    throw new Error(err.detail || 'Signup failed');
  }
  const data: AuthResponse = await res.json();
  setAuthToken(data.token);
  return data;
}

export async function login(payload: { email: string; password: string }): Promise<AuthResponse> {
  const res = await fetch(`${API_BASE}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Login failed' }));
    throw new Error(err.detail || 'Login failed');
  }
  const data: AuthResponse = await res.json();
  setAuthToken(data.token);
  return data;
}

export async function fetchCurrentUser(): Promise<UserProfile | null> {
  const token = getAuthToken();
  if (!token) return null;
  const res = await fetch(`${API_BASE}/api/auth/me`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    setAuthToken(null);
    return null;
  }
  const data = await res.json();
  const profile = data.user || data;
  if (!profile || !profile.name) {
    // If name is nested or stored in token
    return profile;
  }
  return profile;
}

export async function logout(): Promise<void> {
  try {
    await fetch(`${API_BASE}/api/auth/logout`, {
      method: 'POST',
      headers: getAuthHeaders(),
    });
  } catch (err) {
    // Ignore error on network fail
  } finally {
    setAuthToken(null);
  }
}

export async function fetchHealth(): Promise<any> {
  const res = await fetch(`${API_BASE}/health`);
  return res.json();
}

export async function fetchLabs(): Promise<LabInfo[]> {
  const res = await fetch(`${API_BASE}/api/labs`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error('Failed to load labs');
  return res.json();
}

export async function addCustomLab(data: {
  name: string;
  url: string;
  username?: string;
  password?: string;
}): Promise<LabInfo> {
  const res = await fetch(`${API_BASE}/api/labs`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to add lab portal' }));
    throw new Error(err.detail || 'Failed to add lab portal');
  }
  return res.json();
}

export async function deleteCustomLab(labKey: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/labs/${encodeURIComponent(labKey)}`, {
    method: 'DELETE',
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to delete lab portal' }));
    throw new Error(err.detail || 'Failed to delete lab portal');
  }
}

export async function createNewRun(payload: {
  patient_name: string;
  patient_id?: string;
  date_from: string;
  date_to: string;
  logins: Record<string, LabLoginCredential>;
}): Promise<{ run_id: string; patient_key: string; status: string; labs: string[] }> {
  const res = await fetch(`${API_BASE}/api/runs`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to create run' }));
    throw new Error(err.detail || 'Failed to start run');
  }
  return res.json();
}

export async function fetchAllRuns(): Promise<RunSummary[]> {
  const res = await fetch(`${API_BASE}/api/runs`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error('Failed to load runs');
  return res.json();
}

export async function fetchRunDetails(runId: string): Promise<RunDetailsResponse> {
  const res = await fetch(`${API_BASE}/api/runs/${runId}`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error(`Failed to load run ${runId}`);
  return res.json();
}

export async function fetchRunEvents(runId: string, after: number = 0): Promise<EventLogItem[]> {
  const res = await fetch(`${API_BASE}/api/runs/${runId}/events?after=${after}`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error('Failed to load events');
  return res.json();
}

export async function fetchRunCandidates(runId: string): Promise<CandidateItem[]> {
  const res = await fetch(`${API_BASE}/api/runs/${runId}/candidates`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error('Failed to load candidates');
  return res.json();
}

export function getCaptchaImageUrl(runId: string, lab: string): string {
  const token = getAuthToken();
  const authQuery = token ? `&token=${encodeURIComponent(token)}` : '';
  return `${API_BASE}/api/runs/${runId}/captcha/${lab}/image?t=${Date.now()}${authQuery}`;
}

export async function submitCaptchaResolution(
  runId: string,
  lab: string,
  data: { answer?: string; solved_live?: boolean }
): Promise<any> {
  const res = await fetch(`${API_BASE}/api/runs/${runId}/captcha/${lab}`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to submit captcha' }));
    throw new Error(err.detail || 'Failed to submit captcha answer');
  }
  return res.json();
}

export async function submitApproval(
  runId: string,
  approved: boolean,
  overrides: Record<string, string>
): Promise<any> {
  const res = await fetch(`${API_BASE}/api/runs/${runId}/approve`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ approved, overrides }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to submit approval' }));
    throw new Error(err.detail || 'Failed to submit approval');
  }
  return res.json();
}

export async function fetchTimeline(patientKey?: string): Promise<TimelineReportItem[]> {
  const url = patientKey
    ? `${API_BASE}/api/timeline?patient_key=${encodeURIComponent(patientKey)}`
    : `${API_BASE}/api/timeline`;
  const res = await fetch(url, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error('Failed to fetch timeline');
  return res.json();
}

export function getPdfFileUrl(candidateId: string): string {
  return `${API_BASE}/api/files/${candidateId}`;
}

export async function cancelRun(runId: string): Promise<{ status: string; run_id: string }> {
  const res = await fetch(`${API_BASE}/api/runs/${runId}/cancel`, {
    method: 'POST',
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to cancel run' }));
    throw new Error(err.detail || 'Failed to cancel run');
  }
  return res.json();
}

export async function deleteRun(runId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/runs/${runId}`, {
    method: 'DELETE',
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to delete run' }));
    throw new Error(err.detail || 'Failed to delete run');
  }
}

export async function deleteRuns(runIds?: string[]): Promise<{ status: string; count: number }> {
  const payload = JSON.stringify(runIds && runIds.length > 0 ? { run_ids: runIds } : {});
  let res = await fetch(`${API_BASE}/api/runs`, {
    method: 'DELETE',
    headers: getAuthHeaders(),
    body: payload,
  });
  if (!res.ok && res.status === 405) {
    res = await fetch(`${API_BASE}/api/runs/delete`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: payload,
    });
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to delete runs' }));
    throw new Error(err.detail || 'Failed to delete runs');
  }
  return res.json();
}
