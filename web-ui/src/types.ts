export interface ScrapeResult {
  format: string;
  url: string;
  status_code: number;
  title: string;
  description: string;
  text_content: string;
  links: { text: string; href: string }[];
  images: { src: string; alt: string }[];
  videos: { src: string; type: string }[];
  emails: string[];
  phones: string[];
  metadata: Record<string, string>;
  social_links: { text: string; href: string }[];
  tables: { headers: string[]; rows: Record<string, string>[] }[];
  forms: { action: string; method: string; fields: any[] }[];
  scripts: string[];
  stylesheets: string[];
  og_tags: Record<string, string>;
  structured_data: any[];
  headers: Record<string, string>;
  content?: string;
}

export interface AsyncScrapeResponse {
  job_id: string;
  url: string;
  status: string;
  created_at: string;
}

export interface JobItem {
  job_id: string;
  url: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  result: ScrapeResult | null;
  file: string | null;
  error: string | null;
  created_at: string;
  completed_at: string | null;
}

export interface ScheduleItem {
  job_id: string;
  url: string;
  schedule: string;
  mode: string;
  active: boolean;
  last_run: string | null;
  last_status: string | null;
  total_runs: number;
}
