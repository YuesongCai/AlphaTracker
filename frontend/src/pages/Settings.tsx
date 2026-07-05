/** Settings — LLM provider, Feishu channel, schedules, ops status. */
import { useCallback, useEffect, useState } from "react";
import { api, fmtDate } from "../api";
import { Field, Section, Spinner } from "../ui";

interface SettingsResp {
  settings: Record<string, any>;
  llm: { backend: string; detail: string };
}
interface OpsResp {
  log: { job: string; status: string; detail: string; ran_at: string }[];
  signal_count: number; untriaged: number;
  jobs: { id: string; next_run: string | null }[];
  version: string;
}

export default function Settings() {
  const [data, setData] = useState<SettingsResp | null>(null);
  const [ops, setOps] = useState<OpsResp | null>(null);
  const [form, setForm] = useState<Record<string, any>>({});
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [ingesting, setIngesting] = useState(false);

  const load = useCallback(() => {
    api.get<SettingsResp>("/api/settings").then((r) => { setData(r); setForm(r.settings); });
    api.get<OpsResp>("/api/ops/status").then(setOps);
  }, []);
  useEffect(() => { load(); }, [load]);

  if (!data) return <Spinner />;

  const save = async () => {
    setSaving(true);
    try {
      const r = await api.put<SettingsResp>("/api/settings", { settings: form });
      setData(r); setForm(r.settings);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } finally { setSaving(false); }
  };

  const fullIngest = async () => {
    setIngesting(true);
    try { await api.post("/api/ops/ingest?what=all"); load(); }
    finally { setIngesting(false); }
  };

  const set = (key: string, value: any) => setForm({ ...form, [key]: value });
  const backendLabel: Record<string, string> = {
    api: "Anthropic API", cli: "claude CLI(本机订阅)", off: "未接入(规则引擎兜底)",
  };

  return (
    <div className="flex flex-col gap-4 max-w-[860px]">
      <div className="flex items-center justify-between">
        <h1 className="text-[17px] font-semibold">设置</h1>
        <div className="flex items-center gap-2">
          {saved && <span className="text-[12px] text-up">已保存 ✓</span>}
          <button className="btn btn-primary btn-sm" onClick={save} disabled={saving}>
            {saving ? <span className="spinner" /> : "保存全部"}
          </button>
        </div>
      </div>

      <Section title="AI 引擎"
        extra={
          <span className={`text-[12px] ${data.llm.backend !== "off" ? "text-up" : "text-fg3"}`}>
            当前:{backendLabel[data.llm.backend]} · {data.llm.detail}
          </span>
        }>
        <div className="grid grid-cols-2 gap-4">
          <Field label="模式">
            <select className="select" value={form["llm.mode"] || "auto"}
                    onChange={(e) => set("llm.mode", e.target.value)}>
              <option value="auto">自动(API key 优先,其次 claude CLI)</option>
              <option value="api">仅 Anthropic API</option>
              <option value="cli">仅 claude CLI</option>
              <option value="off">关闭 AI(规则引擎兜底)</option>
            </select>
          </Field>
          <Field label="API 模型">
            <input className="input num" value={form["llm.model"] || ""}
                   onChange={(e) => set("llm.model", e.target.value)} />
          </Field>
          <Field label="Anthropic API Key(本地存储,不外传)">
            <input className="input num" type="password" value={form["llm.api_key"] || ""}
                   placeholder="sk-ant-…"
                   onChange={(e) => set("llm.api_key", e.target.value)} />
          </Field>
          <Field label="API Base URL(代理可填,留空官方)">
            <input className="input num" value={form["llm.base_url"] || ""}
                   placeholder="https://api.anthropic.com"
                   onChange={(e) => set("llm.base_url", e.target.value)} />
          </Field>
        </div>
        <p className="text-[12px] text-fg3 leading-relaxed">
          三级降级:API key → 本机 <code className="num">claude</code> CLI(用你的订阅,零额外成本)→ 规则引擎。
          没有 AI 时监控/推送照常,Sniff Test 等生成功能需要前两者之一。
          CLI 需要在终端跑过 <code className="num">claude</code> 并登录。
        </p>
      </Section>

      <Section title="飞书推送">
        <div className="grid grid-cols-2 gap-4">
          <Field label="启用">
            <select className="select" value={String(form["feishu.enabled"] ?? true)}
                    onChange={(e) => set("feishu.enabled", e.target.value === "true")}>
              <option value="true">开启</option>
              <option value="false">关闭</option>
            </select>
          </Field>
          <Field label="接收人 open_id">
            <input className="input num" value={form["feishu.open_id"] || ""}
                   onChange={(e) => set("feishu.open_id", e.target.value)} />
          </Field>
          <Field label="晨报时间(北京时间)">
            <input className="input num" value={form["brief.morning"] || "08:00"}
                   onChange={(e) => set("brief.morning", e.target.value)} />
          </Field>
          <Field label="晚报时间">
            <input className="input num" value={form["brief.evening"] || "19:30"}
                   onChange={(e) => set("brief.evening", e.target.value)} />
          </Field>
          <Field label="即时警报">
            <select className="select" value={String(form["alerts.enabled"] ?? true)}
                    onChange={(e) => set("alerts.enabled", e.target.value === "true")}>
              <option value="true">开启(thesis 标的 M≥4 / 全池 M5)</option>
              <option value="false">关闭</option>
            </select>
          </Field>
          <Field label="警报重要性阈值">
            <select className="select" value={String(form["alerts.min_materiality"] ?? 4)}
                    onChange={(e) => set("alerts.min_materiality", Number(e.target.value))}>
              <option value="3">M3(较多)</option>
              <option value="4">M4(推荐)</option>
              <option value="5">M5(仅重大)</option>
            </select>
          </Field>
        </div>
      </Section>

      <Section title="抓取频率(分钟)">
        <div className="grid grid-cols-3 gap-4">
          {[["ingest.news_minutes", "新闻"], ["ingest.quotes_minutes", "报价"], ["ingest.slow_minutes", "EDGAR/情绪"]].map(([key, label]) => (
            <Field key={key} label={label}>
              <input className="input num" type="number" value={form[key] ?? ""}
                     onChange={(e) => set(key, Number(e.target.value))} />
            </Field>
          ))}
        </div>
      </Section>

      {ops && (
        <Section title={`运行状态 · v${ops.version}`}
          extra={
            <button className="btn btn-sm" onClick={fullIngest} disabled={ingesting}>
              {ingesting ? <><span className="spinner" /> 全量抓取中…</> : "⟳ 全量抓取"}
            </button>
          }>
          <div className="flex gap-6 text-[13px] mb-3">
            <span>信号总数 <b className="num">{ops.signal_count}</b></span>
            <span>待分诊 <b className="num">{ops.untriaged}</b></span>
            {ops.jobs.map((j) => (
              <span key={j.id} className="text-fg3">{j.id} → <span className="num">{j.next_run || "—"}</span></span>
            ))}
          </div>
          <div className="max-h-[240px] overflow-y-auto border-t border-edge2 pt-2">
            {ops.log.map((l, i) => (
              <div key={i} className="flex gap-3 text-[12px] py-1 border-b border-edge2 last:border-0">
                <span className="num text-fg3 shrink-0">{fmtDate(l.ran_at)}</span>
                <span className={l.status === "ok" ? "text-up" : "text-down"}>{l.status}</span>
                <span className="text-fg2">{l.job}</span>
                <span className="text-fg3 truncate">{l.detail}</span>
              </div>
            ))}
          </div>
        </Section>
      )}
    </div>
  );
}
