/** Pipeline — Hunch / Hypothesis / Thesis / Killed kanban + AI sniff entry. */
import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, fmtPct, Idea, Ticker } from "../api";
import { Chg, DemoBadge, Empty, Field, Modal, Spinner } from "../ui";

const COLUMNS: { stage: string; label: string; hint: string; color: string }[] = [
  { stage: "hunch", label: "Hunch", hint: "低成本好奇 · filter-or-kill", color: "#bc8cff" },
  { stage: "hypothesis", label: "Hypothesis", hint: "可检验命题 + 研究计划", color: "#58a6ff" },
  { stage: "thesis", label: "Thesis", hint: "已建立观点 · 监控 drivers", color: "#f0b429" },
  { stage: "killed", label: "Killed", hint: "否决留痕", color: "#5c6b7f" },
];

function IdeaCard({ idea }: { idea: Idea }) {
  return (
    <Link to={`/ideas/${idea.id}`} className="card card-hover p-3 no-underline flex flex-col gap-1.5">
      <div className="flex items-center gap-2">
        <span className="num text-[12.5px] font-bold text-amber">{idea.ticker.symbol}</span>
        <span className={`text-[10.5px] border rounded px-1 ${
          idea.direction === "long" ? "text-up border-[#3fb95044]"
          : idea.direction === "short" ? "text-down border-[#f8514944]"
          : "text-fg3 border-edge"}`}>
          {idea.direction === "long" ? "多" : idea.direction === "short" ? "空" : "观察"}
        </span>
        {idea.is_demo && <DemoBadge />}
      </div>
      <div className="text-[12.5px] text-fg leading-snug">{idea.title}</div>
      <div className="flex items-center gap-2 text-[11px] text-fg3 mt-auto pt-1">
        {idea.ev && (
          <span className="num" style={{ color: idea.ev.ev_return >= 0 ? "#3fb950" : "#f85149" }}>
            EV {fmtPct(idea.ev.ev_return * 100, 0)}
          </span>
        )}
        {idea.driver_count > 0 && <span>{idea.driver_count} drivers</span>}
        {idea.has_sniff && <span>sniff ✓</span>}
        <span className="ml-auto"><Chg value={idea.ticker.change_pct} /></span>
      </div>
    </Link>
  );
}

export default function Pipeline() {
  const [ideas, setIdeas] = useState<Idea[] | null>(null);
  const [tickers, setTickers] = useState<Ticker[]>([]);
  const [showSniff, setShowSniff] = useState(false);
  const [symbol, setSymbol] = useState("");
  const [direction, setDirection] = useState("watch");
  const [sniffing, setSniffing] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(() => { api.get<Idea[]>("/api/ideas").then(setIdeas); }, []);
  useEffect(() => {
    load();
    api.get<Ticker[]>("/api/tickers").then(setTickers);
  }, [load]);

  const sniff = async () => {
    if (!symbol.trim()) return;
    setSniffing(true);
    setError("");
    try {
      const idea = await api.post<Idea>("/api/ideas/sniff", {
        symbol: symbol.trim().toUpperCase(), direction,
      });
      setShowSniff(false);
      setSymbol("");
      load();
      window.location.href = `/ideas/${idea.id}`;
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSniffing(false);
    }
  };

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-[17px] font-semibold">想法管线</h1>
          <p className="text-[12.5px] text-fg3 mt-0.5">
            Hunch → Hypothesis → Thesis:看 60 个,砍 50 个,深挖 10 个,做 3 个
          </p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowSniff(true)}>✦ AI Sniff Test</button>
      </div>

      {ideas === null ? <Spinner /> : (
        <div className="grid grid-cols-4 gap-3 items-start">
          {COLUMNS.map((col) => {
            const list = ideas.filter((i) => i.stage === col.stage);
            return (
              <div key={col.stage} className="flex flex-col gap-2">
                <div className="px-1">
                  <div className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full" style={{ background: col.color }} />
                    <span className="text-[13px] font-semibold">{col.label}</span>
                    <span className="num text-[12px] text-fg3">{list.length}</span>
                  </div>
                  <div className="text-[10.5px] text-fg3 mt-0.5 ml-4">{col.hint}</div>
                </div>
                {list.length === 0 ? (
                  <div className="border border-dashed border-edge rounded-lg py-6 text-center text-[11.5px] text-fg3">
                    空
                  </div>
                ) : (
                  list.map((idea) => <IdeaCard key={idea.id} idea={idea} />)
                )}
              </div>
            );
          })}
        </div>
      )}

      <Modal open={showSniff} onClose={() => setShowSniff(false)} title="AI Sniff Test · filter-or-kill">
        <p className="text-[12.5px] text-fg2 mb-4 leading-relaxed">
          对任意标的做一次结构化嗅探:业务一段话、Focus-5 评分、当前价格在问什么问题、
          三大关键辩论、初步三情景、advance-or-kill 建议。产出是 <b>hypothesis 层素材</b>,不是结论。
        </p>
        <Field label="标的代码(美股如 NVDA,港股如 0700.HK;不在覆盖池会自动添加)">
          <input className="input num" value={symbol} placeholder="NVDA / 0700.HK"
                 onChange={(e) => setSymbol(e.target.value)}
                 onKeyDown={(e) => e.key === "Enter" && sniff()} autoFocus />
        </Field>
        <Field label="初始方向">
          <div className="flex gap-2">
            {[["watch", "观察"], ["long", "偏多"], ["short", "偏空"]].map(([v, label]) => (
              <button key={v} type="button" className={`btn btn-sm ${direction === v ? "btn-primary" : ""}`}
                      onClick={() => setDirection(v)}>{label}</button>
            ))}
          </div>
        </Field>
        <div className="flex gap-1.5 flex-wrap mb-2">
          {tickers.slice(0, 10).map((t) => (
            <button key={t.id} className="btn btn-sm num" onClick={() => setSymbol(t.symbol)}>{t.symbol}</button>
          ))}
        </div>
        {error && <div className="text-[12px] text-down mb-2">{error}</div>}
        <div className="flex justify-end gap-2 mt-2">
          <button className="btn" onClick={() => setShowSniff(false)}>取消</button>
          <button className="btn btn-primary" onClick={sniff} disabled={sniffing || !symbol.trim()}>
            {sniffing ? <><span className="spinner" /> 生成中(约 20-60 秒)</> : "开始嗅探"}
          </button>
        </div>
      </Modal>
    </div>
  );
}
