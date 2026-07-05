/** Idea detail — sniff report, hypothesis, research plan, thesis EV,
 *  drivers with signposts & evidence, Bayesian journal. */
import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, Driver, fmtPct, fmtPrice, Idea, fmtDate } from "../api";
import { Chg, DemoBadge, Empty, Field, Modal, Section, Spinner, StageChip } from "../ui";

function Focus5({ focus5 }: { focus5: Record<string, { assessment: string; score: number }> }) {
  const LABELS: Record<string, string> = {
    organic_growth: "有机增长", margin_trajectory: "利润率轨迹", capital_intensity: "资本密集度",
    capital_deployment: "资本配置", terminal_value: "终局可见度",
  };
  return (
    <div className="grid grid-cols-5 gap-2">
      {Object.entries(LABELS).map(([key, label]) => {
        const item = focus5[key];
        if (!item) return null;
        return (
          <div key={key} className="card p-2.5">
            <div className="flex items-center justify-between">
              <span className="text-[11px] text-fg3">{label}</span>
              <span className="num text-[13px] font-bold"
                    style={{ color: item.score >= 4 ? "#3fb950" : item.score >= 3 ? "#f0b429" : "#f85149" }}>
                {item.score}
              </span>
            </div>
            <div className="flex gap-0.5 my-1.5">
              {[1, 2, 3, 4, 5].map((i) => (
                <div key={i} className="h-1 flex-1 rounded-full"
                     style={{ background: i <= item.score ? (item.score >= 4 ? "#3fb950" : item.score >= 3 ? "#f0b429" : "#f85149") : "#1d2634" }} />
              ))}
            </div>
            <div className="text-[11.5px] text-fg2 leading-snug">{item.assessment}</div>
          </div>
        );
      })}
    </div>
  );
}

function EvBar({ ev, price, currency }: { ev: NonNullable<Idea["ev"]>; price?: number | null; currency?: string }) {
  return (
    <div className="card p-4">
      <div className="flex items-baseline gap-6 flex-wrap">
        <div>
          <div className="text-[11px] text-fg3">期望收益 EV</div>
          <div className="num text-[24px] font-bold" style={{ color: ev.ev_return >= 0 ? "#3fb950" : "#f85149" }}>
            {fmtPct(ev.ev_return * 100, 1)}
          </div>
        </div>
        <div>
          <div className="text-[11px] text-fg3">赔率(上行/下行)</div>
          <div className="num text-[24px] font-bold text-fg">{ev.skew ?? "—"}{ev.skew ? "x" : ""}</div>
        </div>
        <div>
          <div className="text-[11px] text-fg3">现价</div>
          <div className="num text-[24px] font-bold text-fg">{fmtPrice(price)} <span className="text-[12px] text-fg3">{currency}</span></div>
        </div>
      </div>
      <div className="mt-3 flex flex-col gap-1.5">
        {ev.legs.map((leg) => {
          const color = leg.name === "bull" ? "#3fb950" : leg.name === "bear" ? "#f85149" : "#58a6ff";
          return (
            <div key={leg.name} className="flex items-center gap-3">
              <span className="text-[11px] w-8 uppercase" style={{ color }}>{leg.name}</span>
              <div className="flex-1 h-4 bg-ink rounded overflow-hidden">
                <div className="h-full rounded" style={{ width: `${leg.prob * 100}%`, background: `${color}55`, borderRight: `2px solid ${color}` }} />
              </div>
              <span className="num text-[12px] text-fg2 w-14 text-right">{(leg.prob * 100).toFixed(0)}%</span>
              <span className="num text-[12px] text-fg w-16 text-right">{fmtPrice(leg.target)}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function DriverCard({ driver, ideaId, reload }: { driver: Driver; ideaId: number; reload: () => void }) {
  const [expanded, setExpanded] = useState(false);
  const toggleSignpost = async (idx: number) => {
    const signposts = driver.signposts.map((s, i) => i === idx ? { ...s, hit: !s.hit } : s);
    await api.patch(`/api/drivers/${driver.id}`, { signposts });
    reload();
  };
  return (
    <div className="card p-3.5">
      <div className="flex items-start justify-between gap-3 cursor-pointer" onClick={() => setExpanded(!expanded)}>
        <div>
          <div className="text-[13.5px] font-semibold text-fg">{driver.name}</div>
          {driver.description && <div className="text-[12px] text-fg2 mt-0.5">{driver.description}</div>}
        </div>
        <div className="flex items-center gap-2 shrink-0 text-[11.5px]">
          {driver.confirm_count > 0 && <span className="text-up num">✓{driver.confirm_count}</span>}
          {driver.refute_count > 0 && <span className="text-down num">✗{driver.refute_count}</span>}
          <span className="text-fg3">{expanded ? "▾" : "▸"}</span>
        </div>
      </div>

      <div className="mt-2.5 flex flex-col gap-1.5">
        {driver.signposts.map((sp, idx) => (
          <button key={idx} onClick={() => toggleSignpost(idx)}
            className={`text-left flex items-start gap-2 text-[12.5px] rounded-md px-2 py-1.5 border transition-colors ${
              sp.hit ? "border-[#f0b42966] bg-[#f0b42910]" : "border-edge2 hover:border-edge"}`}
            title="点击标记该路标已触发/未触发">
            <span className={sp.direction === "confirm" ? "text-up" : "text-down"}>
              {sp.direction === "confirm" ? "▲" : "▼"}
            </span>
            <span className={sp.hit ? "text-fg" : "text-fg2"}>{sp.text}</span>
            {sp.hit && <span className="ml-auto text-[10.5px] text-amber shrink-0">已触发</span>}
          </button>
        ))}
      </div>

      {expanded && (
        <div className="mt-3 border-t border-edge2 pt-2.5">
          <div className="text-[11px] text-fg3 mb-1.5">证据({driver.evidence.length})</div>
          {driver.evidence.length === 0 ? (
            <div className="text-[12px] text-fg3">暂无 —— triage 会把触及该 driver 的信号自动挂进来</div>
          ) : (
            driver.evidence.map((e) => (
              <div key={e.id} className="flex items-start gap-2 text-[12.5px] py-1">
                <span className={e.stance === "confirm" ? "text-up" : e.stance === "refute" ? "text-down" : "text-fg3"}>
                  {e.stance === "confirm" ? "✅" : e.stance === "refute" ? "❌" : "◽"}
                </span>
                <div className="min-w-0">
                  {e.signal.url
                    ? <a className="text-fg2 hover:text-blue no-underline" href={e.signal.url} target="_blank" rel="noreferrer">{e.signal.title}</a>
                    : <span className="text-fg2">{e.signal.title}</span>}
                  {e.note && <div className="text-[11.5px] text-fg3">{e.note}</div>}
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}

export default function IdeaDetail() {
  const { id } = useParams();
  const nav = useNavigate();
  const [idea, setIdea] = useState<Idea | null>(null);
  const [journalText, setJournalText] = useState("");
  const [journalType, setJournalType] = useState("note");
  const [showKill, setShowKill] = useState(false);
  const [killReason, setKillReason] = useState("");
  const [showDriver, setShowDriver] = useState(false);
  const [driverForm, setDriverForm] = useState({ name: "", description: "" });
  const [planLoading, setPlanLoading] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(() => {
    api.get<Idea>(`/api/ideas/${id}`).then(setIdea).catch(() => nav("/pipeline"));
  }, [id, nav]);
  useEffect(() => { load(); }, [load]);

  if (!idea) return <Spinner />;

  const sniff = idea.sniff || {};
  const thesis = idea.thesis || {};
  const hypo = idea.hypothesis || {};
  const plan = idea.research_plan || {};

  const advance = async () => {
    await api.post(`/api/ideas/${idea.id}/advance`, { note: "" });
    load();
  };
  const kill = async () => {
    await api.post(`/api/ideas/${idea.id}/kill`, { note: killReason });
    setShowKill(false);
    load();
  };
  const addJournal = async () => {
    if (!journalText.trim()) return;
    await api.post(`/api/ideas/${idea.id}/journal`, { content: journalText, entry_type: journalType });
    setJournalText("");
    load();
  };
  const genPlan = async () => {
    setPlanLoading(true);
    setError("");
    try {
      await api.post(`/api/ideas/${idea.id}/research-plan`);
      load();
    } catch (e: any) { setError(e.message); } finally { setPlanLoading(false); }
  };
  const addDriver = async () => {
    if (!driverForm.name.trim()) return;
    await api.post(`/api/ideas/${idea.id}/drivers`, { ...driverForm, signposts: [] });
    setShowDriver(false);
    setDriverForm({ name: "", description: "" });
    load();
  };
  const togglePlanItem = async (section: "analyses" | "people", idx: number) => {
    const next = JSON.parse(JSON.stringify(plan));
    next[section][idx].done = !next[section][idx].done;
    await api.patch(`/api/ideas/${idea.id}`, { research_plan: next });
    load();
  };

  const JOURNAL_ICON: Record<string, string> = {
    stage_change: "⇶", belief_update: "◑", note: "✎", ai_flag: "✦",
  };

  return (
    <div className="flex flex-col gap-4">
      {/* header */}
      <div>
        <Link to="/pipeline" className="text-[12px] text-fg3 no-underline hover:text-fg2">← 管线</Link>
        <div className="flex items-start justify-between mt-1 gap-4">
          <div>
            <div className="flex items-center gap-2.5 flex-wrap">
              <Link to={`/tickers/${idea.ticker.id}`} className="num text-[18px] font-bold text-amber no-underline">
                {idea.ticker.symbol}
              </Link>
              <h1 className="text-[17px] font-semibold">{idea.title}</h1>
              <StageChip stage={idea.stage} />
              {idea.is_demo && <DemoBadge />}
            </div>
            <div className="flex items-center gap-3 mt-1.5 text-[12.5px] text-fg2">
              <span className="num">{fmtPrice(idea.ticker.last_price)} {idea.ticker.currency}</span>
              <Chg value={idea.ticker.change_pct} />
              <span className="text-fg3">更新于 {fmtDate(idea.updated_at)}</span>
            </div>
          </div>
          <div className="flex gap-2 shrink-0">
            {idea.stage !== "thesis" && idea.stage !== "killed" && (
              <button className="btn btn-primary btn-sm" onClick={advance}>
                升级为 {idea.stage === "hunch" ? "Hypothesis" : "Thesis"} →
              </button>
            )}
            {idea.stage !== "killed" ? (
              <button className="btn btn-danger btn-sm" onClick={() => setShowKill(true)}>否决</button>
            ) : (
              <button className="btn btn-sm" onClick={advance}>复活 → Hunch</button>
            )}
          </div>
        </div>
      </div>
      {error && <div className="text-[12px] text-down">{error}</div>}

      {/* thesis EV */}
      {idea.ev && <EvBar ev={idea.ev} price={idea.ticker.last_price} currency={idea.ticker.currency} />}

      <div className="grid grid-cols-3 gap-4 items-start">
        {/* left 2/3 */}
        <div className="col-span-2 flex flex-col gap-4">
          {thesis.variant_view && (
            <Section title="差异化观点 · Variant Perception">
              <p className="text-[13.5px] text-fg leading-relaxed">{thesis.variant_view}</p>
              {(thesis.kill_criteria || []).length > 0 && (
                <div className="mt-3 border-t border-edge2 pt-2.5">
                  <div className="text-[11.5px] text-down font-semibold mb-1.5">KILL CRITERIA · 触发即离场重估</div>
                  {(thesis.kill_criteria as string[]).map((c, i) => (
                    <div key={i} className="text-[12.5px] text-fg2 py-0.5 flex gap-2">
                      <span className="text-down">✂</span>{c}
                    </div>
                  ))}
                </div>
              )}
              {thesis.sizing_note && (
                <div className="mt-2 text-[12px] text-fg3">仓位备注:{thesis.sizing_note}</div>
              )}
            </Section>
          )}

          {sniff.business && (
            <Section title={<span>Sniff Test {sniff._meta?.engine === "seed" && <DemoBadge />}</span>}>
              <p className="text-[13px] text-fg2 leading-relaxed mb-3">{sniff.business}</p>
              {sniff.focus5 && <Focus5 focus5={sniff.focus5} />}
              {sniff.price_question && (
                <div className="mt-3 card p-3 border-l-2 border-l-[#f0b429]">
                  <div className="text-[11px] text-amber font-semibold mb-1">当前价格在问什么问题?</div>
                  <div className="text-[13px] text-fg2 leading-relaxed">{sniff.price_question}</div>
                </div>
              )}
              {(sniff.debates || []).length > 0 && (
                <div className="mt-3 flex flex-col gap-2">
                  <div className="text-[11px] text-fg3 font-semibold uppercase">关键辩论</div>
                  {(sniff.debates as any[]).map((d, i) => (
                    <div key={i} className="card p-3">
                      <div className="text-[13px] font-medium text-fg mb-1.5">{i + 1}. {d.question}</div>
                      <div className="grid grid-cols-2 gap-3 text-[12.5px]">
                        <div><span className="text-up font-semibold">牛:</span> <span className="text-fg2">{d.bull}</span></div>
                        <div><span className="text-down font-semibold">熊:</span> <span className="text-fg2">{d.bear}</span></div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
              {sniff.verdict && (
                <div className="mt-3 flex items-start gap-2.5 text-[13px]">
                  <span className={`border rounded px-2 py-0.5 text-[12px] font-semibold ${
                    sniff.verdict.action === "advance"
                      ? "text-up border-[#3fb95055] bg-[#3fb95010]"
                      : "text-down border-[#f8514955] bg-[#f8514910]"}`}>
                    {sniff.verdict.action === "advance" ? "ADVANCE" : "KILL"}
                  </span>
                  <span className="text-fg2 leading-relaxed">{sniff.verdict.rationale}</span>
                </div>
              )}
              {sniff._meta?.disclaimer && (
                <div className="mt-2.5 text-[11px] text-fg3">⚠ {sniff._meta.disclaimer}</div>
              )}
            </Section>
          )}

          {(hypo.propositions || []).length > 0 && (
            <Section title="Hypothesis · 可检验命题">
              {(hypo.propositions as any[]).map((p, i) => (
                <div key={i} className="flex gap-2.5 text-[13px] py-1.5 border-b border-edge2 last:border-0">
                  <span className="num text-fg3">{i + 1}.</span>
                  <span className="text-fg">{typeof p === "string" ? p : p.text}</span>
                </div>
              ))}
              <div className="grid grid-cols-2 gap-3 mt-3 text-[12.5px]">
                {hypo.confirm && (
                  <div className="card p-2.5 border-l-2 border-l-[#3fb950]">
                    <div className="text-[11px] text-up font-semibold mb-1">什么会证实</div>
                    <div className="text-fg2">{hypo.confirm}</div>
                  </div>
                )}
                {hypo.refute && (
                  <div className="card p-2.5 border-l-2 border-l-[#f85149]">
                    <div className="text-[11px] text-down font-semibold mb-1">什么会证伪</div>
                    <div className="text-fg2">{hypo.refute}</div>
                  </div>
                )}
              </div>
            </Section>
          )}

          <Section title="研究计划 · AI 编排,人来执行"
            extra={
              <button className="btn btn-sm" onClick={genPlan} disabled={planLoading}>
                {planLoading ? <span className="spinner" /> : "✦"} {plan.analyses ? "重新生成" : "AI 生成"}
              </button>
            }>
            {!plan.analyses ? (
              <Empty>还没有研究计划 —— 点「AI 生成」得到分析清单、该聊的人、该问的问题</Empty>
            ) : (
              <div className="flex flex-col gap-3">
                <div>
                  <div className="text-[11px] text-fg3 font-semibold uppercase mb-1.5">分析任务</div>
                  {(plan.analyses as any[]).map((a, i) => (
                    <button key={i} onClick={() => togglePlanItem("analyses", i)}
                      className={`w-full text-left flex gap-2.5 py-1.5 px-2 rounded-md border text-[12.5px] mb-1 transition-colors ${
                        a.done ? "border-[#3fb95044] bg-[#3fb9500a]" : "border-edge2 hover:border-edge"}`}>
                      <span className={a.done ? "text-up" : "text-fg3"}>{a.done ? "☑" : "☐"}</span>
                      <span>
                        <span className={a.done ? "text-fg3 line-through" : "text-fg"}>{a.title}</span>
                        <span className="block text-[11.5px] text-fg3 mt-0.5">{a.why} {a.how && `· ${a.how}`}</span>
                      </span>
                    </button>
                  ))}
                </div>
                {(plan.people || []).length > 0 && (
                  <div>
                    <div className="text-[11px] text-fg3 font-semibold uppercase mb-1.5">该聊的人(AI 无法替你打电话)</div>
                    {(plan.people as any[]).map((p, i) => (
                      <div key={i} className={`card p-2.5 mb-1.5 ${p.done ? "opacity-60" : ""}`}>
                        <button className="flex items-center gap-2 text-[12.5px] font-medium text-fg w-full text-left"
                                onClick={() => togglePlanItem("people", i)}>
                          <span className={p.done ? "text-up" : "text-fg3"}>{p.done ? "☑" : "☐"}</span>
                          {p.who} <span className="text-fg3 font-normal">— {p.why}</span>
                        </button>
                        <ul className="mt-1 ml-6 text-[12px] text-fg2 list-disc pl-3">
                          {(p.questions || []).map((question: string, qi: number) => <li key={qi}>{question}</li>)}
                        </ul>
                      </div>
                    ))}
                  </div>
                )}
                {(plan.data_to_track || []).length > 0 && (
                  <div>
                    <div className="text-[11px] text-fg3 font-semibold uppercase mb-1.5">持续跟踪的数据</div>
                    <div className="flex flex-wrap gap-1.5">
                      {(plan.data_to_track as string[]).map((d, i) => (
                        <span key={i} className="text-[12px] text-fg2 border border-edge rounded-full px-2.5 py-0.5">{d}</span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </Section>

          {idea.notes && (
            <Section title="笔记">
              <p className="text-[13px] text-fg2 leading-relaxed whitespace-pre-wrap">{idea.notes}</p>
            </Section>
          )}
        </div>

        {/* right 1/3: drivers + journal */}
        <div className="flex flex-col gap-4">
          <Section title="Key Drivers · 路标监控"
            extra={<button className="btn btn-sm" onClick={() => setShowDriver(true)}>+ 添加</button>}>
            {(idea.drivers || []).length === 0 ? (
              <Empty>该股成败取决于的 2-3 个变量。{sniff.suggested_drivers ? "Sniff 建议见下方,点添加录入。" : ""}</Empty>
            ) : (
              <div className="flex flex-col gap-2.5">
                {idea.drivers!.map((d) => <DriverCard key={d.id} driver={d} ideaId={idea.id} reload={load} />)}
              </div>
            )}
            {(sniff.suggested_drivers || []).length > 0 && (idea.drivers || []).length === 0 && (
              <div className="mt-3 border-t border-edge2 pt-2.5">
                <div className="text-[11px] text-fg3 mb-1.5">AI 建议的 drivers:</div>
                {(sniff.suggested_drivers as any[]).map((d, i) => (
                  <button key={i} className="btn btn-sm w-full !justify-start mb-1 text-left"
                    onClick={async () => {
                      await api.post(`/api/ideas/${idea.id}/drivers`, {
                        name: d.name, description: d.why || "", signposts: [],
                      });
                      load();
                    }}>
                    + {d.name}
                  </button>
                ))}
              </div>
            )}
          </Section>

          <Section title="过程日志 · Bayesian Journal">
            <div className="mb-3">
              <textarea className="input" rows={2} value={journalText}
                placeholder="记录信念更新:看到什么证据,先验如何变化…"
                onChange={(e) => setJournalText(e.target.value)} />
              <div className="flex items-center gap-2 mt-1.5">
                <select className="select !w-[120px] !py-1 text-[12px]" value={journalType}
                        onChange={(e) => setJournalType(e.target.value)}>
                  <option value="note">笔记</option>
                  <option value="belief_update">信念更新</option>
                </select>
                <button className="btn btn-sm ml-auto" onClick={addJournal} disabled={!journalText.trim()}>记录</button>
              </div>
            </div>
            <div className="flex flex-col">
              {(idea.journal || []).map((j) => (
                <div key={j.id} className="flex gap-2.5 py-2 border-b border-edge2 last:border-0">
                  <span className="text-[13px] text-fg3 shrink-0">{JOURNAL_ICON[j.entry_type] || "✎"}</span>
                  <div className="min-w-0">
                    <div className="text-[12.5px] text-fg2 leading-snug">{j.content}</div>
                    <div className="text-[11px] text-fg3 mt-0.5 num">{fmtDate(j.created_at)}</div>
                  </div>
                </div>
              ))}
            </div>
          </Section>
        </div>
      </div>

      {/* modals */}
      <Modal open={showKill} onClose={() => setShowKill(false)} title="否决想法 · filter-or-kill">
        <p className="text-[12.5px] text-fg2 mb-3">否决要留痕 —— 记录为什么砍掉,未来复盘你的漏斗质量。</p>
        <Field label="否决理由">
          <textarea className="input" rows={3} value={killReason} autoFocus
                    onChange={(e) => setKillReason(e.target.value)}
                    placeholder="例:赔率不足 2:1;关键辩论无法用可得数据验证…" />
        </Field>
        <div className="flex justify-end gap-2 mt-3">
          <button className="btn" onClick={() => setShowKill(false)}>取消</button>
          <button className="btn btn-danger" onClick={kill}>确认否决</button>
        </div>
      </Modal>

      <Modal open={showDriver} onClose={() => setShowDriver(false)} title="添加 Key Driver">
        <Field label="Driver 名称 *">
          <input className="input" value={driverForm.name} autoFocus
                 placeholder="例:AV 合作经济学(分发 vs 直营)"
                 onChange={(e) => setDriverForm({ ...driverForm, name: e.target.value })} />
        </Field>
        <Field label="说明">
          <textarea className="input" rows={2} value={driverForm.description}
                    onChange={(e) => setDriverForm({ ...driverForm, description: e.target.value })} />
        </Field>
        <div className="flex justify-end gap-2 mt-3">
          <button className="btn" onClick={() => setShowDriver(false)}>取消</button>
          <button className="btn btn-primary" onClick={addDriver}>添加</button>
        </div>
      </Modal>
    </div>
  );
}
