/** Signal list row — the shared visual unit across Today / Signals / detail pages. */
import { Link } from "react-router-dom";
import { EVENT_LABEL, Signal, timeAgo } from "./api";
import { Mat, SentimentDot, VariantBadge } from "./ui";

const SOURCE_LABEL: Record<string, string> = {
  google_news: "新闻", edgar: "EDGAR", stocktwits: "社区", manual: "手动",
};

export default function SignalRow({ signal, showTicker = true, dense = false }: {
  signal: Signal; showTicker?: boolean; dense?: boolean;
}) {
  return (
    <div className={`flex gap-3 ${dense ? "py-2" : "py-2.5"} border-b border-edge2 last:border-0 group`}>
      <div className="flex flex-col items-center gap-1 pt-0.5 w-8 shrink-0">
        <Mat level={signal.materiality} />
        <SentimentDot value={signal.sentiment} />
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-baseline gap-2 flex-wrap">
          {showTicker && signal.ticker && (
            <Link to={`/tickers/${signal.ticker.id}`}
              className="num text-[12.5px] font-semibold text-amber no-underline hover:underline">
              {signal.ticker.symbol}
            </Link>
          )}
          {signal.url ? (
            <a href={signal.url} target="_blank" rel="noreferrer"
               className="text-[13.5px] text-fg leading-snug no-underline hover:text-blue hover:underline">
              {signal.title}
            </a>
          ) : (
            <span className="text-[13.5px] text-fg leading-snug">{signal.title}</span>
          )}
          {signal.variant && <VariantBadge />}
        </div>
        {signal.so_what && (
          <div className="text-[12.5px] text-fg2 mt-1 leading-snug">
            <span className="text-fg3">So what · </span>{signal.so_what}
          </div>
        )}
        <div className="flex items-center gap-2 mt-1 text-[11px] text-fg3">
          <span>{timeAgo(signal.published_at)}</span>
          <span>·</span>
          <span>{SOURCE_LABEL[signal.source] || signal.source}{signal.publisher ? ` / ${signal.publisher}` : ""}</span>
          <span>·</span>
          <span className="border border-edge rounded px-1 py-px">{EVENT_LABEL[signal.event_type] || signal.event_type}</span>
          {signal.narratives.map((n) => (
            <Link key={n.id} to={`/narratives/${n.id}`}
              className="border border-[#58a6ff33] text-[#58a6ff] rounded px-1 py-px no-underline hover:bg-[#58a6ff11]">
              {n.title.length > 18 ? n.title.slice(0, 18) + "…" : n.title}
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
