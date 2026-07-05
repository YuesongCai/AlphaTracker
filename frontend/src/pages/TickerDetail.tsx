/** Ticker detail — everything about one name in one place. */
import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, fmtPrice, Idea, Narrative, Signal, Ticker } from "../api";
import SignalRow from "../SignalRow";
import { Chg, DemoBadge, Empty, Section, Spinner, StageChip, StatusChip } from "../ui";

interface TickerFull extends Ticker {
  signals: Signal[]; ideas: Idea[]; narratives: Narrative[];
}

export default function TickerDetail() {
  const { id } = useParams();
  const nav = useNavigate();
  const [data, setData] = useState<TickerFull | null>(null);
  const [sniffing, setSniffing] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(() => {
    api.get<TickerFull>(`/api/tickers/${id}`).then(setData).catch(() => nav("/coverage"));
  }, [id, nav]);
  useEffect(() => { load(); }, [load]);

  if (!data) return <Spinner />;

  const sniff = async () => {
    setSniffing(true);
    setError("");
    try {
      const idea = await api.post<Idea>("/api/ideas/sniff", { ticker_id: data.id });
      nav(`/ideas/${idea.id}`);
    } catch (e: any) { setError(e.message); } finally { setSniffing(false); }
  };

  return (
    <div className="flex flex-col gap-4">
      <div>
        <Link to="/coverage" className="text-[12px] text-fg3 no-underline hover:text-fg2">← 覆盖池</Link>
        <div className="flex items-start justify-between mt-1">
          <div>
            <div className="flex items-baseline gap-3">
              <h1 className="num text-[22px] font-bold text-amber">{data.symbol}</h1>
              <span className="text-[15px] text-fg">{data.name}</span>
              <span className="text-[12px] text-fg3">{data.sector} · {data.market}</span>
            </div>
            <div className="flex items-center gap-3 mt-1.5">
              <span className="num text-[18px] font-semibold">{fmtPrice(data.last_price)} <span className="text-[12px] text-fg3">{data.currency}</span></span>
              <span className="text-[14px]"><Chg value={data.change_pct} /></span>
              {data.next_earnings && (
                <span className="text-[12px] text-fg2 border border-edge rounded px-2 py-0.5">
                  📅 财报 {data.next_earnings}
                </span>
              )}
              {data.st_bull_ratio != null && (
                <span className="text-[12px] text-fg3" title="StockTwits 近期带情绪标签消息中的多头占比">
                  散户 {(data.st_bull_ratio * 100).toFixed(0)}% 偏多
                </span>
              )}
            </div>
          </div>
          <button className="btn btn-primary" onClick={sniff} disabled={sniffing}>
            {sniffing ? <><span className="spinner" /> 嗅探中…</> : "✦ Sniff Test"}
          </button>
        </div>
        {error && <div className="text-[12px] text-down mt-1">{error}</div>}
      </div>

      <div className="grid grid-cols-3 gap-4 items-start">
        <div className="col-span-2">
          <Section title={`信号 · 最近 ${data.signals.length} 条`}>
            {data.signals.length === 0 ? <Empty>暂无信号</Empty> :
              data.signals.map((s) => <SignalRow key={s.id} signal={s} showTicker={false} />)}
          </Section>
        </div>
        <div className="flex flex-col gap-4">
          <Section title="想法">
            {data.ideas.length === 0 ? <Empty>暂无 —— 点上方 Sniff Test 开始</Empty> : (
              <div className="flex flex-col gap-2">
                {data.ideas.map((i) => (
                  <Link key={i.id} to={`/ideas/${i.id}`} className="card card-hover p-2.5 no-underline">
                    <div className="flex items-center gap-2">
                      <StageChip stage={i.stage} />
                      {i.is_demo && <DemoBadge />}
                    </div>
                    <div className="text-[12.5px] text-fg mt-1 leading-snug">{i.title}</div>
                  </Link>
                ))}
              </div>
            )}
          </Section>
          <Section title="关联叙事">
            {data.narratives.length === 0 ? <Empty>暂无</Empty> : (
              <div className="flex flex-col gap-2">
                {data.narratives.map((n) => (
                  <Link key={n.id} to={`/narratives/${n.id}`} className="no-underline">
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-[12.5px] text-fg leading-snug hover:text-amber">{n.title}</span>
                      <span className="num text-[13px] font-bold shrink-0"
                            style={{ color: n.momentum_score >= 50 ? "#f0b429" : "#58a6ff" }}>
                        {n.momentum_score}
                      </span>
                    </div>
                    <div className="mt-0.5"><StatusChip status={n.status} /></div>
                  </Link>
                ))}
              </div>
            )}
          </Section>
        </div>
      </div>
    </div>
  );
}
