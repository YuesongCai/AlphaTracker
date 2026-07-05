/** Today — the analyst's morning screen: overnight signals, narrative movers,
 *  driver alerts, earnings calendar, latest brief. */
import { useCallback, useEffect, useState } from "react";
import Markdown from "react-markdown";
import { Link } from "react-router-dom";
import { api, Dashboard, fmtPrice } from "../api";
import SignalRow from "../SignalRow";
import { Chg, Empty, Section, Spinner, StatusChip } from "../ui";

export default function Today() {
  const [data, setData] = useState<Dashboard | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [briefing, setBriefing] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(() => {
    api.get<Dashboard>("/api/dashboard").then(setData).catch((e) => setError(String(e.message || e)));
  }, []);
  useEffect(() => {
    load();
    const t = setInterval(load, 120_000);
    return () => clearInterval(t);
  }, [load]);

  const refresh = async () => {
    setRefreshing(true);
    try {
      await api.post("/api/ops/ingest?what=news");
      load();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setRefreshing(false);
    }
  };

  const makeBrief = async () => {
    setBriefing(true);
    try {
      await api.post("/api/briefs/generate", { kind: "manual", send: true });
      load();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBriefing(false);
    }
  };

  if (!data) return error ? <Empty>加载失败:{error}</Empty> : <Spinner label="加载今日视图" />;

  const pipeline = data.pipeline_counts;

  return (
    <div className="flex flex-col gap-4">
      {/* price strip */}
      <div className="flex gap-2 overflow-x-auto pb-1 -mx-1 px-1">
        {data.tickers.map((t) => (
          <Link key={t.id} to={`/tickers/${t.id}`}
            className="card card-hover px-3 py-2 min-w-[108px] no-underline shrink-0">
            <div className="num text-[12px] font-semibold text-fg">{t.symbol}</div>
            <div className="num text-[13.5px] mt-0.5 text-fg">{fmtPrice(t.last_price)}</div>
            <div className="text-[11.5px]"><Chg value={t.change_pct} /></div>
          </Link>
        ))}
      </div>

      <div className="flex items-center justify-between">
        <h1 className="text-[17px] font-semibold">今日</h1>
        <div className="flex gap-2">
          <button className="btn btn-sm" onClick={refresh} disabled={refreshing}>
            {refreshing ? <span className="spinner" /> : "⟳"} 立即抓取
          </button>
          <button className="btn btn-sm btn-primary" onClick={makeBrief} disabled={briefing}>
            {briefing ? <span className="spinner" /> : "✉"} 生成简报并推送飞书
          </button>
        </div>
      </div>
      {error && <div className="text-[12px] text-down">{error}</div>}

      <div className="grid grid-cols-5 gap-4">
        {/* left: signals */}
        <div className="col-span-3 flex flex-col gap-4">
          <Section title="隔夜要闻 · 24h 重要性排序"
            extra={<Link to="/signals" className="text-[12px] text-fg3 hover:text-fg2 no-underline">全部 →</Link>}>
            {data.top_signals.length === 0 ? (
              <Empty>暂无重要性≥3的信号 —— 点右上「立即抓取」或等待调度任务</Empty>
            ) : (
              data.top_signals.map((s) => <SignalRow key={s.id} signal={s} />)
            )}
          </Section>

          <Section title="最新简报"
            extra={<Link to="/briefs" className="text-[12px] text-fg3 hover:text-fg2 no-underline">历史 →</Link>}>
            {data.latest_brief ? (
              <div>
                <div className="flex items-center gap-2 text-[12px] text-fg3 mb-2">
                  <span>{data.latest_brief.title}</span>
                  {data.latest_brief.sent
                    ? <span className="text-up">已推送飞书 ✓</span>
                    : data.latest_brief.send_error
                      ? <span className="text-down" title={data.latest_brief.send_error}>推送失败</span>
                      : null}
                </div>
                <div className="md"><Markdown>{data.latest_brief.content_md}</Markdown></div>
              </div>
            ) : (
              <Empty>还没有简报 —— 点上方「生成简报」,或等 08:00 / 19:30 定时推送</Empty>
            )}
          </Section>
        </div>

        {/* right: narrative movers, alerts, earnings, pipeline */}
        <div className="col-span-2 flex flex-col gap-4">
          <Section title="叙事动量"
            extra={<Link to="/narratives" className="text-[12px] text-fg3 hover:text-fg2 no-underline">全部 →</Link>}>
            {data.movers.length === 0 ? <Empty>暂无叙事</Empty> : (
              <div className="flex flex-col gap-2.5">
                {data.movers.map((n) => (
                  <Link key={n.id} to={`/narratives/${n.id}`}
                    className="no-underline group flex items-center gap-3">
                    <div className="num text-[15px] font-bold w-8 text-right shrink-0"
                         style={{ color: n.momentum_score >= 50 ? "#f0b429" : n.momentum_score >= 25 ? "#58a6ff" : "#5c6b7f" }}>
                      {n.momentum_score}
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="text-[13px] text-fg leading-tight truncate group-hover:text-amber">
                        {n.title}
                      </div>
                      <div className="flex items-center gap-2 mt-0.5">
                        <StatusChip status={n.status} />
                        <span className="num text-[11px] text-fg3">7d热度 {n.heat_7d}</span>
                      </div>
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </Section>

          <Section title="Driver 警报 · 证据触及 thesis">
            {data.driver_alerts.length === 0 ? (
              <Empty>暂无 —— 当新信号触及活跃想法的关键驱动时出现在这里</Empty>
            ) : (
              <div className="flex flex-col gap-2">
                {data.driver_alerts.map((a) => (
                  <Link key={a.id} to={`/ideas/${a.idea_id}`} className="no-underline">
                    <div className="text-[12.5px] leading-snug">
                      <span className={a.stance === "confirm" ? "text-up" : a.stance === "refute" ? "text-down" : "text-fg3"}>
                        {a.stance === "confirm" ? "✅" : a.stance === "refute" ? "❌" : "◽"}
                      </span>{" "}
                      <span className="num font-semibold text-amber">{a.symbol}</span>{" "}
                      <span className="text-fg2">{a.driver}</span>
                      <div className="text-fg3 text-[12px] truncate">{a.signal_title}</div>
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </Section>

          <Section title="本周财报">
            {data.earnings_week.length === 0 ? (
              <Empty>未来 8 天覆盖池无财报</Empty>
            ) : (
              <div className="flex flex-col gap-1.5">
                {data.earnings_week.map((t) => (
                  <div key={t.id} className="flex justify-between text-[13px]">
                    <Link to={`/tickers/${t.id}`} className="num font-semibold text-fg no-underline hover:text-amber">
                      {t.symbol}
                    </Link>
                    <span className="num text-fg2">{t.next_earnings}</span>
                  </div>
                ))}
              </div>
            )}
          </Section>

          <Section title="管线概览"
            extra={<Link to="/pipeline" className="text-[12px] text-fg3 hover:text-fg2 no-underline">看板 →</Link>}>
            <div className="grid grid-cols-4 gap-2 text-center">
              {(["hunch", "hypothesis", "thesis", "killed"] as const).map((stage) => (
                <div key={stage} className="card p-2">
                  <div className="num text-[18px] font-bold"
                       style={{ color: { hunch: "#bc8cff", hypothesis: "#58a6ff", thesis: "#f0b429", killed: "#5c6b7f" }[stage] }}>
                    {pipeline[stage] || 0}
                  </div>
                  <div className="text-[10.5px] text-fg3 mt-0.5">
                    {{ hunch: "Hunch", hypothesis: "Hypo", thesis: "Thesis", killed: "Killed" }[stage]}
                  </div>
                </div>
              ))}
            </div>
          </Section>
        </div>
      </div>
    </div>
  );
}
