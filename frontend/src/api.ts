/** API client + shared types (mirrors backend serializers). */

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!resp.ok) {
    let detail = resp.statusText;
    try {
      const body = await resp.json();
      detail = body.detail || JSON.stringify(body);
    } catch { /* keep statusText */ }
    throw new ApiError(resp.status, detail);
  }
  return resp.json();
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "POST", body: body ? JSON.stringify(body) : undefined }),
  put: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "PUT", body: JSON.stringify(body) }),
  patch: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "PATCH", body: JSON.stringify(body) }),
  del: <T>(path: string) => request<T>(path, { method: "DELETE" }),
};

// ---------------------------------------------------------------- types ----

export interface TickerLite {
  id: number; symbol: string; name?: string;
  last_price?: number | null; change_pct?: number | null; currency?: string;
}

export interface Ticker extends TickerLite {
  market: string; sector: string; news_query: string; active: boolean;
  next_earnings?: string | null;
  st_bull_ratio?: number | null; st_watchers?: number | null;
  quote_updated_at?: string | null;
  signals_7d?: number; idea_count?: number;
}

export interface Signal {
  id: number;
  ticker: { id: number; symbol: string } | null;
  lane: string; entities: string[];
  source: string; publisher: string; title: string; url: string; summary: string;
  published_at: string;
  triaged: boolean; triage_engine: string;
  relevance: number; materiality: number; sentiment: number;
  event_type: string; so_what: string; variant: boolean;
  narratives: { id: number; title: string }[];
}

export interface Narrative {
  id: number; title: string; question: string; description: string;
  stance_bull: string; stance_bear: string; kind: string; status: string;
  keywords: string[];
  heat_7d: number; momentum_ratio: number; momentum_score: number;
  sentiment_7d: number; sentiment_shift: number;
  created_at: string;
  tickers: { id: number; symbol: string }[];
}

export interface NarrativeDetail extends Narrative {
  signals: Signal[];
  timeline: { date: string; heat: number }[];
}

export interface Signpost { text: string; direction: "confirm" | "refute"; hit: boolean }

export interface EvidenceItem {
  id: number; stance: string; note: string; created_at: string;
  signal: { id: number; title: string; url: string; published_at: string; materiality: number };
}

export interface Driver {
  id: number; name: string; description: string;
  signposts: Signpost[]; evidence: EvidenceItem[];
  confirm_count: number; refute_count: number;
}

export interface JournalEntry {
  id: number; entry_type: string; content: string; created_at: string;
}

export interface ScenarioLeg { name: string; target: number; prob: number }
export interface EV {
  ev_return: number; upside: number; downside: number;
  skew: number | null; legs: ScenarioLeg[];
}

export interface Idea {
  id: number; title: string; direction: string; stage: string; is_demo: boolean;
  ticker: TickerLite;
  created_at: string; updated_at: string;
  ev: EV | null; driver_count: number; has_sniff: boolean; has_plan: boolean;
  sniff?: Record<string, any>; hypothesis?: Record<string, any>;
  research_plan?: Record<string, any>; thesis?: Record<string, any>;
  notes?: string; drivers?: Driver[]; journal?: JournalEntry[];
}

export interface Brief {
  id: number; kind: string; title: string; content_md: string;
  created_at: string; sent: boolean; send_error: string;
}

export interface Candidate {
  id: number; cluster_key: string; title: string; question: string;
  why_now: string; driver_question: string;
  stance_bull: string; stance_bear: string;
  ticker_symbols: string[]; keywords: string[];
  score: number; heat: number; breadth_pub: number; breadth_lane: number;
  novelty: boolean; status: string; engine: string; ai_rationale: string;
  created_at: string; updated_at: string; evidence: Signal[];
}

export interface TrendingEntity {
  entity: string; score: number; heat: number; breadth_pub: number;
  breadth_lane: number; novelty: boolean; count: number; sample_title: string;
}

export interface CalendarItem {
  pub_time: string; star: number; title: string;
  consensus?: string | null; previous?: string | null; actual?: string | null;
  affect?: string;
}

export interface DiscoverPayload {
  candidates: Candidate[];
  trending: TrendingEntity[];
  calendar: CalendarItem[];
  lanes_24h: Record<string, number>;
}

export interface Dashboard {
  top_signals: Signal[];
  movers: Narrative[];
  tickers: Ticker[];
  earnings_week: Ticker[];
  driver_alerts: {
    id: number; stance: string; driver: string; idea_id: number; symbol: string;
    signal_title: string; signal_url: string; created_at: string;
  }[];
  latest_brief: Brief | null;
  pipeline_counts: Record<string, number>;
  llm: { backend: string; detail: string };
}

// -------------------------------------------------------------- helpers ----

export function fmtPct(v: number | null | undefined, digits = 2): string {
  if (v === null || v === undefined) return "—";
  return `${v >= 0 ? "+" : ""}${v.toFixed(digits)}%`;
}

export function fmtPrice(v: number | null | undefined): string {
  if (v === null || v === undefined) return "—";
  return v >= 1000 ? v.toFixed(0) : v.toFixed(2);
}

export function timeAgo(iso: string): string {
  const then = new Date(iso).getTime();
  const mins = Math.max(0, Math.round((Date.now() - then) / 60000));
  if (mins < 60) return `${mins}m`;
  const hours = Math.round(mins / 60);
  if (hours < 24) return `${hours}h`;
  return `${Math.round(hours / 24)}d`;
}

export function fmtDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return `${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")} ${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}

export const EVENT_LABEL: Record<string, string> = {
  earnings: "财报", guidance: "指引", mna: "并购", product: "产品",
  regulatory: "监管", macro: "宏观", management: "管理层", analyst: "评级",
  capital: "资本", legal: "法律", insider: "内部人", other: "其他",
};

export const STAGE_LABEL: Record<string, string> = {
  hunch: "Hunch", hypothesis: "Hypothesis", thesis: "Thesis", killed: "Killed",
};

export const STATUS_LABEL: Record<string, string> = {
  forming: "酝酿中", accelerating: "升温", cooling: "降温", resolved: "已了结",
};

export const LANE_LABEL: Record<string, string> = {
  company: "个股", markets: "市场", macro: "宏观", tech: "科技", filings: "公告",
};
