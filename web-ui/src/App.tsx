import { useState } from 'react';
import { Search, Loader2, Globe, Bot, Zap, CheckCircle, XCircle, Clock, Trash2, Calendar, Copy, Check } from 'lucide-react';
import { scrapeSync, getJobs, clearJobs, createSchedule, getSchedules, removeSchedule, type ScheduleItem, type JobItem } from './api';

type Tab = 'scrape' | 'jobs' | 'schedules';

export default function App() {
  const [tab, setTab] = useState<Tab>('scrape');
  const [url, setUrl] = useState('');
  const [mode, setMode] = useState<'auto' | 'static' | 'headless'>('auto');
  const [format, setFormat] = useState<'json' | 'markdown' | 'html' | 'csv'>('json');
  const [extract, setExtract] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState('');
  const [jobs, setJobs] = useState<JobItem[]>([]);
  const [schedules, setSchedules] = useState<ScheduleItem[]>([]);
  const [copied, setCopied] = useState(false);

  // Schedule form
  const [schedUrl, setSchedUrl] = useState('');
  const [schedInterval, setSchedInterval] = useState('30m');

  const handleScrape = async () => {
    if (!url.trim()) return;
    setLoading(true);
    setError('');
    setResult(null);
    try {
      const extractList = extract ? extract.split(',').map(s => s.trim()).filter(Boolean) : undefined;
      const data = await scrapeSync(url, mode, format, extractList);
      setResult(data);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const loadJobs = async () => {
    const data = await getJobs();
    setJobs(data);
  };

  const loadSchedules = async () => {
    const data = await getSchedules();
    setSchedules(data);
  };

  const handleTabChange = (t: Tab) => {
    setTab(t);
    if (t === 'jobs') loadJobs();
    if (t === 'schedules') loadSchedules();
  };

  const handleSchedule = async () => {
    if (!schedUrl.trim()) return;
    await createSchedule(schedUrl, schedInterval);
    setSchedUrl('');
    loadSchedules();
  };

  const handleRemoveSchedule = async (id: string) => {
    await removeSchedule(id);
    loadSchedules();
  };

  const copyResult = () => {
    if (result) {
      navigator.clipboard.writeText(JSON.stringify(result, null, 2));
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="min-h-screen bg-[#0d1117] text-[#c9d1d9]">
      {/* Header */}
      <header className="border-b border-[#30363d] bg-[#161b22] px-6 py-4">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-[#58a6ff] text-white">
            <Globe size={20} />
          </div>
          <div>
            <h1 className="text-lg font-bold text-white">WebScraper</h1>
            <p className="text-xs text-[#8b949e]">Paste any URL, scrape everything</p>
          </div>
        </div>
      </header>

      {/* Tabs */}
      <div className="flex border-b border-[#30363d]">
        {(['scrape', 'jobs', 'schedules'] as Tab[]).map(t => (
          <button
            key={t}
            onClick={() => handleTabChange(t)}
            className={`px-6 py-3 text-sm font-medium capitalize transition-colors ${
              tab === t
                ? 'border-b-2 border-[#58a6ff] text-[#58a6ff]'
                : 'text-[#8b949e] hover:text-white'
            }`}
          >
            {t === 'scrape' ? <><Search size={14} className="mr-1 inline" /> Scrape</> :
             t === 'jobs' ? <><Clock size={14} className="mr-1 inline" /> Jobs</> :
             <><Calendar size={14} className="mr-1 inline" /> Schedules</>}
          </button>
        ))}
      </div>

      <main className="mx-auto max-w-5xl p-6">
        {/* SCRAPE TAB */}
        {tab === 'scrape' && (
          <div className="space-y-4">
            {/* URL Input */}
            <div className="flex gap-2">
              <div className="relative flex-1">
                <Globe size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#8b949e]" />
                <input
                  type="url"
                  placeholder="https://example.com"
                  value={url}
                  onChange={e => setUrl(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && handleScrape()}
                  className="w-full rounded-lg border border-[#30363d] bg-[#0d1117] py-3 pl-10 pr-4 text-sm text-white placeholder-[#484f58] focus:border-[#58a6ff] focus:outline-none"
                />
              </div>
              <button
                onClick={handleScrape}
                disabled={loading || !url.trim()}
                className="flex items-center gap-2 rounded-lg bg-[#238636] px-5 py-3 text-sm font-medium text-white transition-colors hover:bg-[#2ea043] disabled:opacity-50"
              >
                {loading ? <Loader2 size={16} className="animate-spin" /> : <Search size={16} />}
                {loading ? 'Scraping...' : 'Scrape'}
              </button>
            </div>

            {/* Options Row */}
            <div className="flex flex-wrap gap-3">
              {/* Mode */}
              <div className="flex items-center gap-2 rounded-lg border border-[#30363d] bg-[#161b22] p-1">
                {([
                  { key: 'auto', icon: <Zap size={13} />, label: 'auto' },
                  { key: 'static', icon: <Globe size={13} />, label: 'static' },
                  { key: 'headless', icon: <Bot size={13} />, label: 'headless' },
                ]).map(({ key, icon, label }) => (
                  <button
                    key={key}
                    onClick={() => setMode(key as 'auto' | 'static' | 'headless')}
                    className={`flex items-center gap-1 rounded-md px-3 py-1.5 text-xs capitalize transition-colors ${
                      mode === key ? 'bg-[#58a6ff] text-white' : 'text-[#8b949e] hover:text-white'
                    }`}
                  >
                    {icon} {label}
                  </button>
                ))}
              </div>

              {/* Format */}
              <select
                value={format}
                onChange={e => setFormat(e.target.value as any)}
                className="rounded-lg border border-[#30363d] bg-[#161b22] px-3 py-2 text-xs text-[#c9d1d9] focus:border-[#58a6ff] focus:outline-none"
              >
                <option value="json">JSON</option>
                <option value="markdown">Markdown</option>
                <option value="html">HTML Report</option>
                <option value="csv">CSV</option>
              </select>

              {/* Extract filter */}
              <input
                type="text"
                placeholder="Extract filter: emails, phones, links, tables, social_links"
                value={extract}
                onChange={e => setExtract(e.target.value)}
                className="flex-1 rounded-lg border border-[#30363d] bg-[#161b22] px-3 py-2 text-xs text-[#c9d1d9] placeholder-[#484f58] focus:border-[#58a6ff] focus:outline-none"
              />
            </div>

            {/* Error */}
            {error && (
              <div className="flex items-center gap-2 rounded-lg border border-red-800 bg-red-900/30 px-4 py-3 text-sm text-red-400">
                <XCircle size={16} /> {error}
              </div>
            )}

            {/* Result */}
            {result && (
              <div className="space-y-4">
                {/* Summary Cards - only for JSON format */}
                {result.format === 'json' && (
                  <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                    {[
                      { label: 'Title', value: result.title || 'N/A', icon: <Globe size={14} /> },
                      { label: 'Links', value: result.links?.length ?? 0, icon: <Search size={14} /> },
                      { label: 'Images', value: result.images?.length ?? 0, icon: <Globe size={14} /> },
                      { label: 'Emails', value: result.emails?.length ?? 0, icon: <Globe size={14} /> },
                    ].map((card, i) => (
                      <div key={i} className="rounded-lg border border-[#30363d] bg-[#161b22] p-3">
                        <div className="flex items-center gap-1 text-xs text-[#8b949e]">{card.icon} {card.label}</div>
                        <div className="mt-1 truncate text-sm font-medium text-white">{card.value}</div>
                      </div>
                    ))}
                  </div>
                )}

                {/* Content */}
                <div className="rounded-lg border border-[#30363d] bg-[#161b22]">
                  <div className="flex items-center justify-between border-b border-[#30363d] px-4 py-2">
                    <span className="text-xs font-medium text-[#8b949e] uppercase">
                      {result.format === 'json' ? 'JSON Result' : `${result.format.toUpperCase()} Result`}
                    </span>
                    <button onClick={copyResult} className="flex items-center gap-1 text-xs text-[#8b949e] hover:text-white">
                      {copied ? <Check size={13} className="text-green-400" /> : <Copy size={13} />} {copied ? 'Copied' : 'Copy'}
                    </button>
                  </div>
                  {result.format === 'html' ? (
                    <iframe
                      srcDoc={result.content}
                      className="h-[600px] w-full border-0"
                      sandbox="allow-same-origin"
                      title="Scrape Result"
                    />
                  ) : (
                    <pre className="max-h-[600px] overflow-auto p-4 text-xs leading-relaxed text-[#c9d1d9] whitespace-pre-wrap">
                      {result.format === 'json'
                        ? JSON.stringify(result, null, 2)
                        : result.content || JSON.stringify(result, null, 2)}
                    </pre>
                  )}
                </div>
              </div>
            )}

            {/* Empty State */}
            {!result && !loading && !error && (
              <div className="flex flex-col items-center justify-center py-20 text-[#484f58]">
                <Globe size={48} className="mb-4 opacity-30" />
                <p className="text-lg">Paste a URL and hit Scrape</p>
                <p className="mt-1 text-sm">Supports static pages, React/Vue SPAs, and more</p>
              </div>
            )}
          </div>
        )}

        {/* JOBS TAB */}
        {tab === 'jobs' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-sm text-[#8b949e]">{jobs.length} jobs</span>
              <button
                onClick={async () => { await clearJobs(); loadJobs(); }}
                className="flex items-center gap-1 rounded-lg border border-[#30363d] px-3 py-1.5 text-xs text-[#8b949e] hover:text-white"
              >
                <Trash2 size={13} /> Clear All
              </button>
            </div>
            {jobs.length === 0 ? (
              <div className="flex flex-col items-center py-16 text-[#484f58]">
                <Clock size={48} className="mb-4 opacity-30" />
                <p>No jobs yet. Use the Scrape tab to create one.</p>
              </div>
            ) : (
              <div className="space-y-2">
                {jobs.map((job: any) => (
                  <div key={job.job_id} className="flex items-center gap-3 rounded-lg border border-[#30363d] bg-[#161b22] p-3">
                    {job.status === 'completed' ? <CheckCircle size={16} className="text-green-400" /> :
                     job.status === 'failed' ? <XCircle size={16} className="text-red-400" /> :
                     job.status === 'processing' ? <Loader2 size={16} className="animate-spin text-[#58a6ff]" /> :
                     <Clock size={16} className="text-[#8b949e]" />}
                    <div className="flex-1 min-w-0">
                      <div className="truncate text-sm text-white">{job.url}</div>
                      <div className="text-xs text-[#8b949e]">{job.job_id} · {job.created_at}</div>
                    </div>
                    <span className={`rounded-full px-2 py-0.5 text-xs ${
                      job.status === 'completed' ? 'bg-green-900/50 text-green-400' :
                      job.status === 'failed' ? 'bg-red-900/50 text-red-400' :
                      'bg-[#58a6ff]/20 text-[#58a6ff]'
                    }`}>{job.status}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* SCHEDULES TAB */}
        {tab === 'schedules' && (
          <div className="space-y-4">
            {/* New schedule */}
            <div className="flex gap-2">
              <input
                type="url"
                placeholder="https://example.com"
                value={schedUrl}
                onChange={e => setSchedUrl(e.target.value)}
                className="flex-1 rounded-lg border border-[#30363d] bg-[#0d1117] px-4 py-2.5 text-sm text-white placeholder-[#484f58] focus:border-[#58a6ff] focus:outline-none"
              />
              <select
                value={schedInterval}
                onChange={e => setSchedInterval(e.target.value)}
                className="rounded-lg border border-[#30363d] bg-[#161b22] px-3 text-sm text-[#c9d1d9] focus:border-[#58a6ff] focus:outline-none"
              >
                <option value="5m">Every 5 min</option>
                <option value="30m">Every 30 min</option>
                <option value="1h">Every hour</option>
                <option value="6h">Every 6 hours</option>
                <option value="1d">Every day</option>
                <option value="0 9 * * *">Daily at 9 AM</option>
                <option value="0 */6 * * *">Every 6 hours (cron)</option>
              </select>
              <button
                onClick={handleSchedule}
                disabled={!schedUrl.trim()}
                className="rounded-lg bg-[#238636] px-5 py-2.5 text-sm font-medium text-white hover:bg-[#2ea043] disabled:opacity-50"
              >
                Schedule
              </button>
            </div>

            {schedules.length === 0 ? (
              <div className="flex flex-col items-center py-16 text-[#484f58]">
                <Calendar size={48} className="mb-4 opacity-30" />
                <p>No scheduled scrapes</p>
              </div>
            ) : (
              <div className="space-y-2">
                {schedules.map((s: any) => (
                  <div key={s.job_id} className="flex items-center gap-3 rounded-lg border border-[#30363d] bg-[#161b22] p-3">
                    <Calendar size={16} className="text-[#58a6ff]" />
                    <div className="flex-1 min-w-0">
                      <div className="truncate text-sm text-white">{s.url}</div>
                      <div className="text-xs text-[#8b949e]">{s.job_id} · {s.schedule} · {s.total_runs} runs · {s.last_status}</div>
                    </div>
                    <button
                      onClick={() => handleRemoveSchedule(s.job_id)}
                      className="rounded-lg border border-red-800 p-1.5 text-red-400 hover:bg-red-900/30"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
