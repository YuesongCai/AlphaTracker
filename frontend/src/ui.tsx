/** Small shared building blocks for the terminal-dark aesthetic. */
import { ReactNode, useEffect } from "react";

export function Spinner({ label }: { label?: string }) {
  return (
    <div className="flex items-center gap-2 text-fg3 text-[13px] py-6 justify-center">
      <div className="spinner" />
      {label || "加载中"}
    </div>
  );
}

export function Empty({ children }: { children: ReactNode }) {
  return (
    <div className="text-center text-fg3 text-[13px] py-10 border border-dashed border-edge rounded-lg">
      {children}
    </div>
  );
}

/** Materiality badge M1..M5 — the product's core visual grammar. */
export function Mat({ level }: { level: number }) {
  const palette: Record<number, string> = {
    5: "bg-[#f8514922] text-[#ff7b72] border-[#f8514966]",
    4: "bg-[#f0b42922] text-[#f0b429] border-[#f0b42966]",
    3: "bg-[#58a6ff1a] text-[#58a6ff] border-[#58a6ff55]",
    2: "bg-[#8b98a915] text-fg2 border-edge",
    1: "bg-transparent text-fg3 border-edge",
  };
  return (
    <span className={`num inline-flex items-center border rounded px-1.5 py-px text-[11px] font-semibold ${palette[level] || palette[1]}`}>
      M{level || "?"}
    </span>
  );
}

export function SentimentDot({ value }: { value: number }) {
  const color = value > 0 ? "#3fb950" : value < 0 ? "#f85149" : "#5c6b7f";
  const arrows = value >= 2 ? "▲▲" : value === 1 ? "▲" : value === 0 ? "—" : value === -1 ? "▼" : "▼▼";
  return <span className="num text-[11px]" style={{ color }}>{arrows}</span>;
}

export function Chg({ value }: { value: number | null | undefined }) {
  if (value === null || value === undefined) return <span className="text-fg3 num">—</span>;
  const color = value >= 0 ? "#3fb950" : "#f85149";
  return (
    <span className="num" style={{ color }}>
      {value >= 0 ? "+" : ""}{value.toFixed(2)}%
    </span>
  );
}

export function StageChip({ stage }: { stage: string }) {
  const styles: Record<string, string> = {
    hunch: "text-[#bc8cff] border-[#bc8cff55] bg-[#bc8cff12]",
    hypothesis: "text-[#58a6ff] border-[#58a6ff55] bg-[#58a6ff12]",
    thesis: "text-[#f0b429] border-[#f0b42955] bg-[#f0b42912]",
    killed: "text-fg3 border-edge bg-transparent line-through",
  };
  const label: Record<string, string> = {
    hunch: "Hunch", hypothesis: "Hypothesis", thesis: "Thesis", killed: "Killed",
  };
  return (
    <span className={`inline-flex border rounded-full px-2 py-px text-[11px] font-medium ${styles[stage] || styles.hunch}`}>
      {label[stage] || stage}
    </span>
  );
}

export function StatusChip({ status }: { status: string }) {
  const map: Record<string, [string, string]> = {
    accelerating: ["升温 ↑", "text-[#3fb950] border-[#3fb95055] bg-[#3fb95010]"],
    forming: ["酝酿中", "text-[#58a6ff] border-[#58a6ff44] bg-[#58a6ff0d]"],
    cooling: ["降温 ↓", "text-fg3 border-edge bg-transparent"],
    resolved: ["已了结", "text-fg3 border-edge bg-transparent"],
  };
  const [label, cls] = map[status] || map.forming;
  return <span className={`inline-flex border rounded-full px-2 py-px text-[11px] ${cls}`}>{label}</span>;
}

export function Spark({ points, width = 120, height = 28 }: { points: number[]; width?: number; height?: number }) {
  if (!points.length) return null;
  const max = Math.max(...points, 0.1);
  const step = width / Math.max(points.length - 1, 1);
  const path = points
    .map((v, i) => `${i === 0 ? "M" : "L"}${(i * step).toFixed(1)},${(height - 2 - (v / max) * (height - 6)).toFixed(1)}`)
    .join(" ");
  const last = points[points.length - 1];
  return (
    <svg width={width} height={height} className="overflow-visible">
      <path d={path} fill="none" stroke="#f0b429" strokeWidth="1.5" strokeLinejoin="round" opacity={0.9} />
      <circle
        cx={(points.length - 1) * step}
        cy={height - 2 - (last / max) * (height - 6)}
        r="2" fill="#f0b429"
      />
    </svg>
  );
}

export function Section({ title, extra, children, className = "" }: {
  title: ReactNode; extra?: ReactNode; children: ReactNode; className?: string;
}) {
  return (
    <div className={`card p-4 fade-in ${className}`}>
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-[13px] font-semibold text-fg2 tracking-wide uppercase">{title}</h2>
        {extra}
      </div>
      {children}
    </div>
  );
}

export function Modal({ open, onClose, title, children, wide }: {
  open: boolean; onClose: () => void; title: ReactNode; children: ReactNode; wide?: boolean;
}) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    if (open) window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-[8vh] bg-black/60 backdrop-blur-sm"
         onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className={`card p-5 ${wide ? "w-[760px]" : "w-[520px]"} max-w-[94vw] max-h-[80vh] overflow-y-auto fade-in`}>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-[15px] font-semibold">{title}</h3>
          <button className="btn btn-sm" onClick={onClose}>✕</button>
        </div>
        {children}
      </div>
    </div>
  );
}

export function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="block mb-3">
      <div className="text-[12px] text-fg3 mb-1">{label}</div>
      {children}
    </label>
  );
}

export function DemoBadge() {
  return (
    <span className="inline-flex items-center border border-[#bc8cff44] bg-[#bc8cff0d] text-[#bc8cff] rounded px-1.5 py-px text-[10.5px]"
          title="构建期 AI 预生成的演示内容,展示产品满血状态">
      DEMO
    </span>
  );
}

export function VariantBadge() {
  return (
    <span className="inline-flex items-center border border-[#bc8cff55] bg-[#bc8cff12] text-[#bc8cff] rounded px-1.5 py-px text-[10.5px] font-medium"
          title="AI 判断:包含与主流叙事相左、市场可能尚未消化的信息">
      非共识
    </span>
  );
}
