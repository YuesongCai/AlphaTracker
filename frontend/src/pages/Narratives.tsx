/** Narratives — the debate wall with momentum scores. */
import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, Narrative, Ticker } from "../api";
import { Empty, Field, Modal, Spinner, StatusChip } from "../ui";

function NarrativeCard({ n }: { n: Narrative }) {
  return (
    <Link to={`/narratives/${n.id}`} className="card card-hover p-4 no-underline flex flex-col gap-2.5">
      <div className="flex items-start justify-between gap-3">
        <div className="text-[14px] font-semibold text-fg leading-snug">{n.title}</div>
        <div className="num text-[22px] font-bold shrink-0 leading-none"
             style={{ color: n.momentum_score >= 50 ? "#f0b429" : n.momentum_score >= 25 ? "#58a6ff" : "#5c6b7f" }}>
          {n.momentum_score}
        </div>
      </div>
      {n.question && <div className="text-[12.5px] text-fg2 leading-snug">{n.question}</div>}
      <div className="flex items-center gap-2 flex-wrap mt-auto pt-1">
        <StatusChip status={n.status} />
        <span className="num text-[11px] text-fg3">7d热度 {n.heat_7d}</span>
        <span className="num text-[11px] text-fg3">动量 ×{n.momentum_ratio}</span>
        {n.sentiment_shift !== 0 && (
          <span className="num text-[11px]" style={{ color: n.sentiment_shift > 0 ? "#3fb950" : "#f85149" }}>
            情绪{n.sentiment_shift > 0 ? "↑" : "↓"}
          </span>
        )}
        <span className="ml-auto flex gap-1">
          {n.tickers.map((t) => (
            <span key={t.id} className="num text-[11px] text-amber border border-[#f0b42933] rounded px-1">
              {t.symbol}
            </span>
          ))}
        </span>
      </div>
    </Link>
  );
}

export default function Narratives() {
  const [items, setItems] = useState<Narrative[] | null>(null);
  const [tickers, setTickers] = useState<Ticker[]>([]);
  const [showNew, setShowNew] = useState(false);
  const [suggesting, setSuggesting] = useState(false);
  const [error, setError] = useState("");
  const [form, setForm] = useState({
    title: "", question: "", stance_bull: "", stance_bear: "",
    keywords: "", ticker_ids: [] as number[], kind: "company",
  });

  const load = useCallback(() => {
    api.get<Narrative[]>("/api/narratives?include_resolved=true").then(setItems);
  }, []);
  useEffect(() => {
    load();
    api.get<Ticker[]>("/api/tickers").then(setTickers);
  }, [load]);

  const create = async () => {
    if (!form.title.trim()) return;
    await api.post("/api/narratives", {
      ...form,
      keywords: form.keywords.split(/[,,、\n]/).map((s) => s.trim()).filter(Boolean),
    });
    setShowNew(false);
    setForm({ title: "", question: "", stance_bull: "", stance_bear: "", keywords: "", ticker_ids: [], kind: "company" });
    load();
  };

  const suggest = async () => {
    setSuggesting(true);
    setError("");
    try {
      const r = await api.post<{ suggestions: any[] }>("/api/narratives/suggest");
      if (!r.suggestions.length) {
        setError("AI 没有从近期信号中发现新叙事");
      } else {
        for (const s of r.suggestions) {
          const tickerIds = tickers.filter((t) => (s.ticker_symbols || []).includes(t.symbol)).map((t) => t.id);
          await api.post("/api/narratives", { ...s, ticker_ids: tickerIds });
        }
        load();
      }
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSuggesting(false);
    }
  };

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-[17px] font-semibold">叙事</h1>
          <p className="text-[12.5px] text-fg3 mt-0.5">市场正在辩论的问题 —— narrative cycle 决定久期资产的重估节奏</p>
        </div>
        <div className="flex gap-2">
          <button className="btn btn-sm" onClick={suggest} disabled={suggesting}>
            {suggesting ? <span className="spinner" /> : "✦"} AI 发现新叙事
          </button>
          <button className="btn btn-sm btn-primary" onClick={() => setShowNew(true)}>+ 新建叙事</button>
        </div>
      </div>
      {error && <div className="text-[12px] text-down">{error}</div>}

      {items === null ? <Spinner /> : items.length === 0 ? (
        <Empty>还没有叙事</Empty>
      ) : (
        <div className="grid grid-cols-2 gap-4">
          {items.map((n) => <NarrativeCard key={n.id} n={n} />)}
        </div>
      )}

      <Modal open={showNew} onClose={() => setShowNew(false)} title="新建叙事" wide>
        <Field label="标题 *(格式建议:标的 × 主题:核心分歧?)">
          <input className="input" value={form.title} placeholder="例:UBER × 自动驾驶:顺风还是逆风?"
                 onChange={(e) => setForm({ ...form, title: e.target.value })} />
        </Field>
        <Field label="核心问题">
          <input className="input" value={form.question} placeholder="这场辩论到底在争什么?"
                 onChange={(e) => setForm({ ...form, question: e.target.value })} />
        </Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label="多方立场"><textarea className="input" rows={2} value={form.stance_bull}
            onChange={(e) => setForm({ ...form, stance_bull: e.target.value })} /></Field>
          <Field label="空方立场"><textarea className="input" rows={2} value={form.stance_bear}
            onChange={(e) => setForm({ ...form, stance_bear: e.target.value })} /></Field>
        </div>
        <Field label="追踪关键词(英文,逗号分隔 —— 用于新闻抓取)">
          <input className="input" value={form.keywords} placeholder="Uber robotaxi, Waymo partnership"
                 onChange={(e) => setForm({ ...form, keywords: e.target.value })} />
        </Field>
        <Field label="关联标的">
          <div className="flex flex-wrap gap-1.5">
            {tickers.map((t) => {
              const on = form.ticker_ids.includes(t.id);
              return (
                <button key={t.id} type="button"
                  className={`btn btn-sm num ${on ? "btn-primary" : ""}`}
                  onClick={() => setForm({
                    ...form,
                    ticker_ids: on ? form.ticker_ids.filter((x) => x !== t.id) : [...form.ticker_ids, t.id],
                  })}>
                  {t.symbol}
                </button>
              );
            })}
          </div>
        </Field>
        <div className="flex justify-end gap-2 mt-4">
          <button className="btn" onClick={() => setShowNew(false)}>取消</button>
          <button className="btn btn-primary" onClick={create}>创建</button>
        </div>
      </Modal>
    </div>
  );
}
