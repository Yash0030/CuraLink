import type {
  LabInfo,
  RunSummary,
  RunDetailsResponse,
  CandidateItem,
  EventLogItem,
  TimelineReportItem,
  LabLoginCredential
} from './types';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export async function fetchHealth(): Promise<any> {
  const res = await fetch(`${API_BASE}/health`);
  return res.json();
}

export async function fetchLabs(): Promise<LabInfo[]> {
  const res = await fetch(`${API_BASE}/api/labs`);
  if (!res.ok) throw new Error('Failed to load labs');
  return res.json();
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
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to create run' }));
    throw new Error(err.detail || 'Failed to start run');
  }
  return res.json();
}

export async function fetchAllRuns(): Promise<RunSummary[]> {
  const res = await fetch(`${API_BASE}/api/runs`);
  if (!res.ok) throw new Error('Failed to load runs');
  return res.json();
}

export async function fetchRunDetails(runId: string): Promise<RunDetailsResponse> {
  const res = await fetch(`${API_BASE}/api/runs/${runId}`);
  if (!res.ok) throw new Error(`Failed to load run ${runId}`);
  return res.json();
}

export async function fetchRunEvents(runId: string, after: number = 0): Promise<EventLogItem[]> {
  const res = await fetch(`${API_BASE}/api/runs/${runId}/events?after=${after}`);
  if (!res.ok) throw new Error('Failed to load events');
  return res.json();
}

export async function fetchRunCandidates(runId: string): Promise<CandidateItem[]> {
  const res = await fetch(`${API_BASE}/api/runs/${runId}/candidates`);
  if (!res.ok) throw new Error('Failed to load candidates');
  return res.json();
}

export function getCaptchaImageUrl(runId: string, lab: string): string {
  return `${API_BASE}/api/runs/${runId}/captcha/${lab}/image?t=${Date.now()}`;
}

export async function submitCaptchaResolution(
  runId: string,
  lab: string,
  data: { answer?: string; solved_live?: boolean }
): Promise<any> {
  const res = await fetch(`${API_BASE}/api/runs/${runId}/captcha/${lab}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
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
    headers: { 'Content-Type': 'application/json' },
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
  const res = await fetch(url);
  if (!res.ok) throw new Error('Failed to fetch timeline');
  return res.json();
}

export function getPdfFileUrl(candidateId: string): string {
  return `${API_BASE}/api/files/${candidateId}`;
}
