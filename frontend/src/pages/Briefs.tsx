/** Briefs — history of morning/evening/manual briefs with Feishu send status. */
import { useCallback, useEffect, useState } from "react";
import Markdown from "react-markdown";
import { api, Brief, fmtDate } from "../api";
import { Empty, Section, Spinner } from "../ui";

export default function Briefs() {
  const [briefs, setBriefs] = useState<Brief[] | null>(null);
  const [generating, setGenerating] = useState(false);
  const [selected, setSelected] = useState<Brief | null>(null);

  const load = useCallback(() => {
    api.get<Brief[]>("/api/briefs").then((r) => {
      setBriefs(r);
      setSelected((prev) => prev ?? r[0] ?? null);
    });
  }, []);
  useEffect(() => { load(); }, [load]);

  const generate = async () => {
    setGenerating(true);
    try {
      const brief = await api.post<Brief>("/api/briefs/generate", { kind: "manual", send: true });
      setSelected(brief);
      load();
    } finally { setGenerating(false); }
  };

  const resend = async (id: number) => {
    const updated = await api.post<Brief>(`/api/briefs/${id}/send`);
    setSelected(updated);
    load();
  };

  const KIND_LABEL: Record<string, string> = { morning: "晨报", evening: "晚报", manual: "手动" };

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-[17px] font-semibold">简报</h1>
          <p className="text-[12.5px] text-fg3 mt-0.5">晨报 08:00 · 晚报 19:30(北京时间,设置页可改)自动推送飞书</p>
        </div>
        <button className="btn btn-primary btn-sm" onClick={generate} disabled={generating}>
          {generating ? <><span className="spinner" /> 生成中…</> : "✉ 立即生成并推送"}
        </button>
      </div>

      {briefs === null ? <Spinner /> : briefs.length === 0 ? (
        <Empty>还没有简报</Empty>
      ) : (
        <div className="grid grid-cols-3 gap-4 items-start">
          <div className="card p-2 flex flex-col max-h-[75vh] overflow-y-auto">
            {briefs.map((b) => (
              <button key={b.id} onClick={() => setSelected(b)}
                className={`text-left px-3 py-2.5 rounded-lg transition-colors ${
                  selected?.id === b.id ? "bg-[#f0b42912] border border-[#f0b42933]" : "hover:bg-panel2 border border-transparent"}`}>
                <div className="flex items-center gap-2">
                  <span className="text-[13px] font-medium text-fg">{b.title || KIND_LABEL[b.kind] || b.kind}</span>
                  {b.sent ? <span className="text-[10.5px] text-up">✓ 已推送</span>
                    : b.send_error ? <span className="text-[10.5px] text-down" title={b.send_error}>推送失败</span>
                    : <span className="text-[10.5px] text-fg3">未推送</span>}
                </div>
                <div className="num text-[11px] text-fg3 mt-0.5">{fmtDate(b.created_at)}</div>
              </button>
            ))}
          </div>
          <div className="col-span-2">
            {selected && (
              <Section title={selected.title}
                extra={
                  <button className="btn btn-sm" onClick={() => resend(selected.id)}>
                    {selected.sent ? "再次推送飞书" : "推送飞书"}
                  </button>
                }>
                {selected.send_error && (
                  <div className="text-[12px] text-down mb-2">上次推送失败:{selected.send_error}</div>
                )}
                <div className="md"><Markdown>{selected.content_md}</Markdown></div>
              </Section>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
