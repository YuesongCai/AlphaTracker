/** Radar — 发现引擎主页。
 *
 * 产品哲学的落点:引擎从全市场信息流里 cut through noise,把涌现的叙事喂给你,
 * 而不是等你输入 ticker 再去 monitor。
 */
import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  api, Candidate, DiscoverPayload, LANE_LABEL, Signal, timeAgo,
} from "../api";
import SignalRow from "../SignalRow";
import { Empty, Section, Spinner } from "../ui";

function ScoreBadge({ score, novelty }: { score: number; novelty: boolean }) {
  return (
    <div className="flex flex-col items-center shrink-0 w-14">
      <div className="num text-[22px] font-bold text-amber leading-none">{score.toFixed(0)}</div>
      <div className="text-[10px] text-fg3 mt-0.5">热度分</div>
      {novelty && (
        <span className="mt-1 text-[9.5px] border border-[#3fb95055] text-[#3fb950] bg-[#3fb95010] rounded px-1 py-px font-semibold">
          NEW
        </span>
      )}
    </div>
  );
}

function BreadthBadges({ c }: { c: Candidate }) {
  return (
    <div className="flex items-center gap-1.5 text-[10.5px] text-fg3">
      <span className="border border-edge rounded px-1 py-px num">{c.breadth_pub} 信源</span>
      <span className={`border rounded px-1 py-px num ${c.breadth_lane >= 2 ? "border-[#58a6ff55] text-[#58a6ff]" : "border-edge"}`}>
        {c.breadth_lane} 通道
      </span>
      <span className="border border-edge rounded px-1 py-px">
        {c.engine === "heuristic" ? "热度聚类" : "AI 合成"}
      </span>
    </div>
  );
}

function CandidateCard({ c, onAction }: { c: Candidate; onAction: () => void }) {
  const [expanded, setExpanded] = useState(false);
  const [busy, setBusy] = useState(false);
  const navigate = useNavigate();

  const promote = async () => {
    setBusy(true);
    try {
      const r = await api.post<{ ok: boolean; narrative: { id: number } }>(
        `/api/discover/candidates/${c.id}/promote`);
      navigate(`/narratives/${r.narrative.id}`);
    } catch { setBusy(false); }
  };
  const dismiss = async () => {
    setBusy(true);
    try { await api.post(`/api/discover/candidates/${c.id}/dismiss`); onAction(); }
    finally { setBusy(false); }
  };

  const evidence = expanded ? c.evidence : c.evidence.slice(0, 3);
  return (
    <div className="card p-4 fade-in flex gap-3.5">
      <ScoreBadge score={c.score} novelty={c.novelty} />
      <div className="min-w-0 flex-1">
        <div className="flex items-start justify-between gap-2">
          <div className="text-[14.5px] font-semibold leading-snug">{c.title || c.cluster_key}</div>
          <BreadthBadges c={c} />
        </div>
        {c.question && <div className="text-[12.5px] text-fg2 mt-1 leading-snug">{c.question}</div>}
        {c.why_now && (
          <div className="text-[12px] mt-2 leading-snug">
            <span className="text-[#3fb950] font-medium">为什么是现在 · </span>
            <span className="text-fg2">{c.why_now}</span>
          </div>
        )}
        {c.driver_question && (
          <div className="text-[12px] mt-1 leading-snug">
            <span className="text-amber font-medium">Key driver · </span>
            <span className="text-fg2">{c.driver_question}</span>
          </div>
        )}
        {(c.stance_bull || c.stance_bear) && (
          <div className="grid grid-cols-2 gap-2 mt-2">
            <div className="text-[11.5px] leading-snug border border-[#3fb95025] bg-[#3fb95008] rounded px-2 py-1.5">
              <span className="text-[#3fb950] font-semibold">多 </span>
              <span className="text-fg2">{c.stance_bull}</span>
            </div>
            <div className="text-[11.5px] leading-snug border border-[#f8514925] bg-[#f8514908] rounded px-2 py-1.5">
              <span className="text-[#ff7b72] font-semibold">空 </span>
              <span className="text-fg2">{c.stance_bear}</span>
            </div>
          </div>
        )}
        {(c.ticker_symbols.length > 0 || c.keywords.length > 0) && (
          <div className="flex items-center gap-1.5 mt-2 flex-wrap">
            {c.ticker_symbols.map((s) => (
              <span key={s} className="num text-[11px] font-semibold text-amber border border-[#f0b42944] rounded px-1.5 py-px">{s}</span>
            ))}
            {c.keywords.map((k) => (
              <span key={k} className="text-[11px] text-fg3 border border-edge rounded px-1.5 py-px">{k}</span>
            ))}
          </div>
        )}

        {c.evidence.length > 0 && (
          <div className="mt-2.5 border-t border-edge2 pt-1">
            {evidence.map((s: Signal) => (
              <div key={s.id} className="flex items-baseline gap-2 py-1 text-[12px] leading-snug">
                <span className="text-fg3 num shrink-0">{timeAgo(s.published_at)}</span>
                <span className="text-fg3 shrink-0">{s.publisher || LANE_LABEL[s.lane]}</span>
                {s.url ? (
                  <a href={s.url} target="_blank" rel="noreferrer"
                     className="text-fg2 no-underline hover:text-blue hover:underline truncate">{s.title}</a>
                ) : <span className="text-fg2 truncate">{s.title}</span>}
              </div>
            ))}
            {c.evidence.length > 3 && (
              <button className="text-[11.5px] text-fg3 hover:text-fg2 bg-transparent border-0 cursor-pointer px-0"
                      onClick={() => setExpanded(!expanded)}>
                {expanded ? "收起 ↑" : `全部 ${c.evidence.length} 条证据 ↓`}
              </button>
            )}
          </div>
        )}

        <div className="flex items-center gap-2 mt-3">
          <button className="btn btn-primary btn-sm" disabled={busy} onClick={promote}>▶ 开始追踪</button>
          <button className="btn btn-sm" disabled={busy} onClick={dismiss}>忽略</button>
          <span className="text-[11px] text-fg3 ml-auto">{timeAgo(c.created_at)} 发现</span>
        </div>
      </div>
    </div>
  );
}

const LANE_TABS = [
  ["", "全部"], ["macro", "宏观"], ["markets", "市场"], ["tech", "科技"],
  ["filings", "公告"], ["company", "个股"],
] as const;

export default function Radar() {
  const [data, setData] = useState<DiscoverPayload | null>(null);
  const [lane, setLane] = useState<string>("");
  const [feed, setFeed] = useState<Signal[] | null>(null);
  const [scanning, setScanning] = useState(false);
  const [showSkipped, setShowSkipped] = useState(false);

  const load = useCallback(() => {
    api.get<DiscoverPayload>("/api/discover").then(setData).catch(() => setData(null));
  }, []);
  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    const params = new URLSearchParams({ min_materiality: "3", days: "2", limit: "30" });
    if (lane) params.set("lane", lane);
    setFeed(null);
    api.get<{ items: Signal[] }>(`/api/signals?${params}`).then((r) => setFeed(r.items));
  }, [lane]);

  const scan = async () => {
    setScanning(true);
    try { await api.post("/api/discover/scan"); load(); }
    finally { setScanning(false); }
  };

  if (!data) return <Spinner label="加载雷达" />;
  const pending = data.candidates.filter((c) => c.status === "pending");
  const skipped = data.candidates.filter((c) => c.status === "ai_skip");
  const lanes = data.lanes_24h || {};

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-[17px] font-semibold">雷达</h1>
          <div className="text-[12px] text-fg3 mt-0.5">
            近24h 信号:{Object.entries(lanes).map(([k, v]) => `${LANE_LABEL[k] || k} ${v}`).join(" · ") || "—"}
          </div>
        </div>
        <button className="btn btn-sm" disabled={scanning} onClick={scan}>
          {scanning ? "扫描中…" : "◈ 立即扫描"}
        </button>
      </div>

      {data.calendar.length > 0 && (
        <div className="card px-3 py-2 flex items-center gap-2 overflow-x-auto">
          <span className="text-[11px] text-fg3 shrink-0 font-medium">今日日历</span>
          {data.calendar.map((c, i) => (
            <span key={i} title={`前值 ${c.previous ?? "—"} / 预期 ${c.consensus ?? "—"} / 实际 ${c.actual ?? "—"}`}
              className={`shrink-0 text-[11.5px] border rounded px-1.5 py-0.5 whitespace-nowrap ${
                c.star >= 3 ? "border-[#f0b42955] text-amber bg-[#f0b42908]" : "border-edge text-fg2"}`}>
              <span className="num">{(c.pub_time || "").slice(11, 16)}</span> {"★".repeat(Math.min(c.star, 3))} {c.title}
              {c.actual ? <span className="num text-fg"> {c.actual}</span> : null}
            </span>
          ))}
        </div>
      )}

      <Section title={<>涌现叙事候选 <span className="num text-fg3 font-normal normal-case">{pending.length}</span></>}
        extra={<span className="text-[11.5px] text-fg3">聚类 · 跨源验证 · 新颖度加权 —— 引擎喂给你,promote 后进入持续追踪</span>}>
        {pending.length === 0 ? (
          <Empty>暂无待审候选。信息流持续摄取中,下一轮扫描自动发现;也可点右上「立即扫描」。</Empty>
        ) : (
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-3">
            {pending.map((c) => <CandidateCard key={c.id} c={c} onAction={load} />)}
          </div>
        )}
        {skipped.length > 0 && (
          <div className="mt-3">
            <button className="text-[12px] text-fg3 hover:text-fg2 bg-transparent border-0 cursor-pointer px-0"
                    onClick={() => setShowSkipped(!showSkipped)}>
              {showSkipped ? "▾" : "▸"} AI 判为噪音的热点({skipped.length})
            </button>
            {showSkipped && skipped.map((c) => (
              <div key={c.id} className="flex items-center gap-2 py-1.5 border-b border-edge2 last:border-0 text-[12.5px]">
                <span className="num font-semibold text-fg2 shrink-0">{c.cluster_key}</span>
                <span className="text-fg3 truncate">{c.ai_rationale || c.title}</span>
                <button className="btn btn-sm ml-auto shrink-0"
                        onClick={async () => { await api.post(`/api/discover/candidates/${c.id}/promote`); load(); }}>
                  仍要追踪
                </button>
              </div>
            ))}
          </div>
        )}
      </Section>

      {data.trending.length > 0 && (
        <Section title="趋势实体 48H" extra={<span className="text-[11.5px] text-fg3">点击深挖相关信号</span>}>
          <div className="flex flex-wrap gap-2">
            {data.trending.map((t) => (
              <Link key={t.entity} to={`/signals?q=${encodeURIComponent(t.entity)}`}
                title={t.sample_title}
                className="group flex items-center gap-2 border border-edge rounded-md px-2.5 py-1.5 no-underline hover:border-[#f0b42966] hover:bg-[#f0b42906]">
                <span className="text-[13px] font-semibold text-fg group-hover:text-amber">{t.entity}</span>
                <span className="num text-[11px] text-amber">{t.score.toFixed(0)}</span>
                <span className="num text-[10.5px] text-fg3">{t.count}条</span>
                {t.novelty && <span className="text-[9px] text-[#3fb950]">●</span>}
              </Link>
            ))}
          </div>
        </Section>
      )}

      <Section title="全市场信号流"
        extra={
          <div className="flex gap-1">
            {LANE_TABS.map(([key, label]) => (
              <button key={key}
                className={`btn btn-sm ${lane === key ? "!border-[#f0b42966] !text-amber" : ""}`}
                onClick={() => setLane(key)}>
                {label}
              </button>
            ))}
          </div>
        }>
        {feed === null ? <Spinner /> : feed.length === 0 ? (
          <Empty>该通道近 48h 无重要性 ≥M3 的信号</Empty>
        ) : (
          feed.map((s) => <SignalRow key={s.id} signal={s} />)
        )}
      </Section>
    </div>
  );
}
