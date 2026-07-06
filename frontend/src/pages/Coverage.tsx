/** Coverage — the universe table. */
import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, fmtPrice, Ticker } from "../api";
import { Chg, Empty, Field, Modal, Spinner } from "../ui";

export default function Coverage() {
  const [tickers, setTickers] = useState<Ticker[] | null>(null);
  const [showAdd, setShowAdd] = useState(false);
  const [showBulk, setShowBulk] = useState(false);
  const [symbol, setSymbol] = useState("");
  const [name, setName] = useState("");
  const [bulkText, setBulkText] = useState("");
  const [adding, setAdding] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(() => { api.get<Ticker[]>("/api/tickers").then(setTickers); }, []);
  useEffect(() => { load(); }, [load]);

  const add = async () => {
    if (!symbol.trim()) return;
    setAdding(true);
    setError("");
    try {
      await api.post("/api/tickers", { symbol: symbol.trim().toUpperCase(), name: name.trim() });
      setShowAdd(false);
      setSymbol(""); setName("");
      load();
    } catch (e: any) { setError(e.message); } finally { setAdding(false); }
  };

  const addBulk = async () => {
    const symbols = bulkText.split(/[\s,;、，]+/).map((s) => s.trim()).filter(Boolean);
    if (!symbols.length) return;
    setAdding(true);
    setError("");
    try {
      const r = await api.post<{ added: string[]; skipped: string[] }>(
        "/api/tickers/bulk", { symbols });
      setShowBulk(false);
      setBulkText("");
      if (r.skipped.length) setError(`已存在跳过:${r.skipped.join(" ")}`);
      load();
    } catch (e: any) { setError(e.message); } finally { setAdding(false); }
  };

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-[17px] font-semibold">覆盖池</h1>
          <p className="text-[12.5px] text-fg3 mt-0.5">know the companies you cover better than any non-insider</p>
        </div>
        <div className="flex gap-2">
          <button className="btn btn-sm" onClick={() => setShowBulk(true)}>⇪ 批量导入</button>
          <button className="btn btn-primary btn-sm" onClick={() => setShowAdd(true)}>+ 添加标的</button>
        </div>
      </div>

      {tickers === null ? <Spinner /> : tickers.length === 0 ? <Empty>覆盖池为空</Empty> : (
        <div className="card overflow-hidden">
          <table className="w-full text-[13px]">
            <thead>
              <tr className="text-[11px] text-fg3 uppercase border-b border-edge">
                {["标的", "名称", "价格", "涨跌", "财报日", "7d信号", "想法", "散户多头%", "状态"].map((h) => (
                  <th key={h} className="text-left font-medium px-3 py-2.5">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {tickers.map((t) => (
                <tr key={t.id} className="border-b border-edge2 last:border-0 hover:bg-panel2/50">
                  <td className="px-3 py-2.5">
                    <Link to={`/tickers/${t.id}`} className="num font-bold text-amber no-underline hover:underline">
                      {t.symbol}
                    </Link>
                  </td>
                  <td className="px-3 py-2.5 text-fg2">{t.name || "—"}
                    {!t.active && <span className="ml-2 text-[10.5px] text-fg3 border border-edge rounded px-1">停用</span>}
                  </td>
                  <td className="px-3 py-2.5 num">{fmtPrice(t.last_price)} <span className="text-[10.5px] text-fg3">{t.currency}</span></td>
                  <td className="px-3 py-2.5"><Chg value={t.change_pct} /></td>
                  <td className="px-3 py-2.5 num text-fg2">{t.next_earnings || "—"}</td>
                  <td className="px-3 py-2.5 num text-fg2">{t.signals_7d ?? 0}</td>
                  <td className="px-3 py-2.5 num text-fg2">{t.idea_count ?? 0}</td>
                  <td className="px-3 py-2.5 num text-fg2">
                    {t.st_bull_ratio != null ? `${(t.st_bull_ratio * 100).toFixed(0)}%` : "—"}
                  </td>
                  <td className="px-3 py-2.5">
                    <button className="btn btn-sm"
                      onClick={async () => { await api.patch(`/api/tickers/${t.id}`, { active: !t.active }); load(); }}>
                      {t.active ? "停用" : "启用"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <Modal open={showBulk} onClose={() => setShowBulk(false)} title="批量导入组合">
        <Field label="粘贴代码列表(空格/逗号/换行分隔;美股 NVDA / 港股 0700.HK)">
          <textarea className="input !h-[110px] num" value={bulkText} autoFocus
                    placeholder={"GOOGL MSTR TSM UNH HOOD\nCRWV NBIS MU LITE COHR"}
                    onChange={(e) => setBulkText(e.target.value)} />
        </Field>
        {error && <div className="text-[12px] text-down mb-2">{error}</div>}
        <div className="flex justify-end gap-2 mt-3">
          <button className="btn" onClick={() => setShowBulk(false)}>取消</button>
          <button className="btn btn-primary" onClick={addBulk} disabled={adding}>
            {adding ? <><span className="spinner" /> 逐个抓取初始数据…</> : "导入"}
          </button>
        </div>
      </Modal>

      <Modal open={showAdd} onClose={() => setShowAdd(false)} title="添加标的">
        <Field label="代码 *(美股 NVDA / 港股 0700.HK)">
          <input className="input num" value={symbol} autoFocus placeholder="NVDA"
                 onChange={(e) => setSymbol(e.target.value)}
                 onKeyDown={(e) => e.key === "Enter" && add()} />
        </Field>
        <Field label="名称(可选,自动补全)">
          <input className="input" value={name} onChange={(e) => setName(e.target.value)} />
        </Field>
        {error && <div className="text-[12px] text-down mb-2">{error}</div>}
        <div className="flex justify-end gap-2 mt-3">
          <button className="btn" onClick={() => setShowAdd(false)}>取消</button>
          <button className="btn btn-primary" onClick={add} disabled={adding}>
            {adding ? <><span className="spinner" /> 抓取初始数据…</> : "添加"}
          </button>
        </div>
      </Modal>
    </div>
  );
}
