/** Narrative detail — debate framing, heat timeline, evidence feed. */
import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, NarrativeDetail as ND } from "../api";
import SignalRow from "../SignalRow";
import { Empty, Section, Spark, Spinner, StatusChip } from "../ui";

export default function NarrativeDetail() {
  const { id } = useParams();
  const nav = useNavigate();
  const [data, setData] = useState<ND | null>(null);

  const load = useCallback(() => {
    api.get<ND>(`/api/narratives/${id}`).then(setData).catch(() => nav("/narratives"));
  }, [id, nav]);
  useEffect(() => { load(); }, [load]);

  if (!data) return <Spinner />;

  const resolve = async () => {
    await api.patch(`/api/narratives/${data.id}`, {
      status: data.status === "resolved" ? "forming" : "resolved",
    });
    load();
  };

  const heatSeries = data.timeline.map((p) => p.heat);

  return (
    <div className="flex flex-col gap-4">
      <div>
        <Link to="/narratives" className="text-[12px] text-fg3 no-underline hover:text-fg2">← 叙事</Link>
        <div className="flex items-start justify-between mt-1 gap-4">
          <div>
            <h1 className="text-[18px] font-semibold leading-snug">{data.title}</h1>
            {data.question && <p className="text-[13px] text-fg2 mt-1">{data.question}</p>}
            <div className="flex items-center gap-2 mt-2">
              <StatusChip status={data.status} />
              {data.tickers.map((t) => (
                <Link key={t.id} to={`/tickers/${t.id}`}
                  className="num text-[11.5px] text-amber border border-[#f0b42933] rounded px-1.5 no-underline">
                  {t.symbol}
                </Link>
              ))}
              {data.keywords.map((k) => (
                <span key={k} className="text-[11px] text-fg3 border border-edge rounded px-1.5">{k}</span>
              ))}
            </div>
          </div>
          <div className="card p-3 text-center shrink-0">
            <div className="num text-[26px] font-bold leading-none"
                 style={{ color: data.momentum_score >= 50 ? "#f0b429" : "#58a6ff" }}>
              {data.momentum_score}
            </div>
            <div className="text-[10.5px] text-fg3 mt-1">动量分</div>
            <div className="mt-2"><Spark points={heatSeries} width={140} /></div>
            <div className="num text-[10.5px] text-fg3 mt-1">60 天热度</div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="card p-4 border-l-2 border-l-[#3fb950]">
          <div className="text-[12px] font-semibold text-up mb-1.5">BULL 多方立场</div>
          <div className="text-[13px] text-fg2 leading-relaxed">{data.stance_bull || "—"}</div>
        </div>
        <div className="card p-4 border-l-2 border-l-[#f85149]">
          <div className="text-[12px] font-semibold text-down mb-1.5">BEAR 空方立场</div>
          <div className="text-[13px] text-fg2 leading-relaxed">{data.stance_bear || "—"}</div>
        </div>
      </div>

      <Section title={`证据时间线 · ${data.signals.length} 条`}
        extra={
          <button className="btn btn-sm" onClick={resolve}>
            {data.status === "resolved" ? "重新激活" : "标记已了结"}
          </button>
        }>
        {data.signals.length === 0 ? (
          <Empty>暂无关联信号 —— 信号在 triage 时会自动映射到叙事(关键词命中或 AI 判断)</Empty>
        ) : (
          data.signals.map((s) => <SignalRow key={s.id} signal={s} />)
        )}
      </Section>
    </div>
  );
}
