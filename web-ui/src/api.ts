const API_BASE = '/api';

export async function scrapeSync(url: string, mode = 'auto', format = 'json', extract?: string[]) {
  const res = await fetch(`${API_BASE}/scrape/sync`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url, mode, format, extract }),
  });
  if (!res.ok) throw new Error(`Scrape failed: ${res.status}`);
  return res.json();
}

export async function scrapeAsync(url: string, mode = 'auto', format = 'json', extract?: string[]) {
  const res = await fetch(`${API_BASE}/scrape`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url, mode, format, extract }),
  });
  if (!res.ok) throw new Error(`Scrape failed: ${res.status}`);
  return res.json();
}

export async function getJob(jobId: string) {
  const res = await fetch(`${API_BASE}/scrape/${jobId}`);
  if (!res.ok) throw new Error(`Job not found: ${res.status}`);
  return res.json();
}

export async function getJobs() {
  const res = await fetch(`${API_BASE}/jobs`);
  return res.json();
}

export async function clearJobs() {
  const res = await fetch(`${API_BASE}/jobs`, { method: 'DELETE' });
  return res.json();
}

export async function createSchedule(url: string, schedule: string, mode = 'auto', format = 'json', extract?: string[]) {
  const res = await fetch(`${API_BASE}/schedule`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url, schedule, mode, format, extract }),
  });
  if (!res.ok) throw new Error(`Schedule failed: ${res.status}`);
  return res.json();
}

export async function getSchedules() {
  const res = await fetch(`${API_BASE}/schedule`);
  return res.json();
}

export async function removeSchedule(jobId: string) {
  const res = await fetch(`${API_BASE}/schedule/${jobId}`, { method: 'DELETE' });
  return res.json();
}

export async function getScheduleResults(jobId: string) {
  const res = await fetch(`${API_BASE}/schedule/${jobId}/results`);
  return res.json();
}

export type JobItem = {
  job_id: string;
  url: string;
  status: string;
  created_at: string;
  result?: Record<string, unknown> | null;
  file?: string | null;
  error?: string | null;
  completed_at?: string | null;
};

export type ScheduleItem = {
  job_id: string;
  url: string;
  schedule: string;
  status: string;
};
