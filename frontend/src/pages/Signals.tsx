/** Signals — the full filterable feed. */
import { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api, EVENT_LABEL, LANE_LABEL, Signal, Ticker } from "../api";
import SignalRow from "../SignalRow";
import { Empty, Field, Modal, Spinner } from "../ui";

export default function Signals() {
  const [searchParams] = useSearchParams();
  const [items, setItems] = useState<Signal[] | null>(null);
  const [total, setTotal] = useState(0);
  const [tickers, setTickers] = useState<Ticker[]>([]);
  const [tickerId, setTickerId] = useState("");
  const [eventType, setEventType] = useState("");
  const [lane, setLane] = useState(searchParams.get("lane") || "");
  const [minMat, setMinMat] = useState("1");
  const [variantOnly, setVariantOnly] = useState(false);
  const [q, setQ] = useState(searchParams.get("q") || "");
  const [days, setDays] = useState("14");
  const [offset, setOffset] = useState(0);
  const [showAdd, setShowAdd] = useState(false);
  const [manual, setManual] = useState({ title: "", url: "", ticker_id: "" });
  const LIMIT = 60;

  useEffect(() => { api.get<Ticker[]>("/api/tickers").then(setTickers); }, []);

  const load = useCallback(() => {
    const params = new URLSearchParams({
      min_materiality: minMat, days, limit: String(LIMIT), offset: String(offset),
    });
    if (tickerId) params.set("ticker_id", tickerId);
    if (eventType) params.set("event_type", eventType);
    if (lane) params.set("lane", lane);
    if (variantOnly) params.set("variant_only", "true");
    if (q.trim()) params.set("q", q.trim());
    api.get<{ total: number; items: Signal[] }>(`/api/signals?${params}`)
      .then((r) => { setItems(r.items); setTotal(r.total); });
  }, [tickerId, eventType, lane, minMat, variantOnly, q, days, offset]);

  useEffect(() => { load(); }, [load]);
  useEffect(() => { setOffset(0); }, [tickerId, eventType, lane, minMat, variantOnly, q, days]);

  const addManual = async () => {
    if (!manual.title.trim()) return;
    await api.post("/api/signals", {
      title: manual.title, url: manual.url,
      ticker_id: manual.ticker_id ? Number(manual.ticker_id) : null,
    });
    setShowAdd(false);
    setManual({ title: "", url: "", ticker_id: "" });
    load();
  };

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h1 className="text-[17px] font-semibold">信号流 <span className="num text-[13px] text-fg3 font-normal">{total} 条</span></h1>
        <button className="btn btn-sm" onClick={() => setShowAdd(true)}>+ 手动录入</button>
      </div>

      <div className="card p-3 flex flex-wrap items-center gap-2.5">
        <input className="input !w-[220px]" placeholder="搜索标题 / so-what…" value={q}
               onChange={(e) => setQ(e.target.value)} />
        <select className="select !w-[130px]" value={tickerId} onChange={(e) => setTickerId(e.target.value)}>
          <option value="">全部标的</option>
          {tickers.map((t) => <option key={t.id} value={t.id}>{t.symbol}</option>)}
        </select>
        <select className="select !w-[100px]" value={lane} onChange={(e) => setLane(e.target.value)}>
          <option value="">全部通道</option>
          {Object.entries(LANE_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
        <select className="select !w-[110px]" value={eventType} onChange={(e) => setEventType(e.target.value)}>
          <option value="">全部事件</option>
          {Object.entries(EVENT_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
        <select className="select !w-[130px]" value={minMat} onChange={(e) => setMinMat(e.target.value)}>
          {[1, 2, 3, 4, 5].map((m) => <option key={m} value={m}>重要性 ≥ M{m}</option>)}
        </select>
        <select className="select !w-[100px]" value={days} onChange={(e) => setDays(e.target.value)}>
          <option value="3">3 天</option><option value="7">7 天</option>
          <option value="14">14 天</option><option value="30">30 天</option>
        </select>
        <label className="flex items-center gap-1.5 text-[12.5px] text-fg2 cursor-pointer select-none">
          <input type="checkbox" checked={variantOnly} onChange={(e) => setVariantOnly(e.target.checked)} />
          只看非共识
        </label>
      </div>

      <div className="card px-4 py-1">
        {items === null ? <Spinner /> : items.length === 0 ? (
          <div className="py-4"><Empty>没有匹配的信号</Empty></div>
        ) : (
          items.map((s) => <SignalRow key={s.id} signal={s} />)
        )}
      </div>

      {total > LIMIT && (
        <div className="flex justify-center gap-2">
          <button className="btn btn-sm" disabled={offset === 0}
                  onClick={() => setOffset(Math.max(0, offset - LIMIT))}>← 上一页</button>
          <span className="text-[12px] text-fg3 self-center num">
            {offset + 1}–{Math.min(offset + LIMIT, total)} / {total}
          </span>
          <button className="btn btn-sm" disabled={offset + LIMIT >= total}
                  onClick={() => setOffset(offset + LIMIT)}>下一页 →</button>
        </div>
      )}

      <Modal open={showAdd} onClose={() => setShowAdd(false)} title="手动录入信号">
        <Field label="标题 / 内容摘要 *">
          <input className="input" value={manual.title} placeholder="例:专家访谈——渠道反馈 Q3 提货放缓"
                 onChange={(e) => setManual({ ...manual, title: e.target.value })} />
        </Field>
        <Field label="链接(可选)">
          <input className="input" value={manual.url} placeholder="https://…"
                 onChange={(e) => setManual({ ...manual, url: e.target.value })} />
        </Field>
        <Field label="关联标的(可选)">
          <select className="select" value={manual.ticker_id}
                  onChange={(e) => setManual({ ...manual, ticker_id: e.target.value })}>
            <option value="">无 / 宏观</option>
            {tickers.map((t) => <option key={t.id} value={t.id}>{t.symbol} {t.name}</option>)}
          </select>
        </Field>
        <div className="flex justify-end gap-2 mt-4">
          <button className="btn" onClick={() => setShowAdd(false)}>取消</button>
          <button className="btn btn-primary" onClick={addManual}>录入并分诊</button>
        </div>
      </Modal>
    </div>
  );
}
