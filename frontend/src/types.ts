export interface LabInfo {
  key: string;
  name: string;
  layout: 'table' | 'cards' | 'paginated';
  has_captcha: boolean;
  reports_path: string;
}

export interface LabLoginCredential {
  enabled: boolean;
  username: string;
  password: string;
}

export interface RunSummary {
  id: string;
  patient_name: string;
  patient_id?: string;
  patient_key: string;
  date_from: string;
  date_to: string;
  labs: string[];
  status: string;
  error?: string;
  created_at: string;
  updated_at: string;
}

export interface DecisionCounts {
  keep: number;
  duplicate: number;
  exclude: number;
  reject: number;
  needs_review: number;
}

export interface RunDetailsResponse {
  run: RunSummary;
  decision_counts: DecisionCounts;
  total_candidates: number;
  waiting_captchas: string[];
}

export interface CandidateItem {
  id: string;
  run_id: string;
  lab: string;
  filename: string;
  source_url?: string;
  listing_title?: string;
  portal_report_id?: string;
  portal_date?: string;
  fetched_at: string;
  http_status: number;
  content_type: string;
  size_bytes: number;
  sha256: string;
  extract_ok?: boolean;
  extract_note?: string;
  extract_source?: string;
  x_name?: string;
  x_patient_id?: string;
  x_report_id?: string;
  x_date?: string;
  x_test?: string;
  legit_result?: any;
  duplicate_result?: any;
  decision?: 'keep' | 'duplicate' | 'exclude' | 'reject' | 'needs_review';
  decision_reason?: string;
  status: 'staging' | 'stored' | 'not_stored';
  recheck_ok?: boolean;
  recheck_note?: string;
}

export interface EventLogItem {
  id: number;
  run_id: string;
  agent: string;
  level: 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR';
  message: string;
  data?: any;
  created_at: string;
}

export interface TimelineReportItem {
  report_uuid: string;
  candidate_id?: string;
  patient_key: string;
  lab: string;
  report_id: string;
  test_name: string;
  report_date: string;
  sha256: string;
  created_at: string;
  filename?: string;
  x_name?: string;
  x_patient_id?: string;
  recheck_ok?: boolean;
  recheck_note?: string;
}
