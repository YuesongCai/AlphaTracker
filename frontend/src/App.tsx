import { useEffect, useState } from "react";
import { NavLink, Route, Routes, useLocation } from "react-router-dom";
import { api } from "./api";
import Radar from "./pages/Radar";
import Today from "./pages/Today";
import Signals from "./pages/Signals";
import Narratives from "./pages/Narratives";
import NarrativeDetail from "./pages/NarrativeDetail";
import Pipeline from "./pages/Pipeline";
import IdeaDetail from "./pages/IdeaDetail";
import Coverage from "./pages/Coverage";
import TickerDetail from "./pages/TickerDetail";
import Briefs from "./pages/Briefs";
import Settings from "./pages/Settings";

const NAV = [
  { to: "/", label: "雷达", icon: "◈" },
  { to: "/today", label: "今日", icon: "◉" },
  { to: "/signals", label: "信号流", icon: "≋" },
  { to: "/narratives", label: "叙事", icon: "◫" },
  { to: "/pipeline", label: "管线", icon: "⇶" },
  { to: "/coverage", label: "覆盖池", icon: "▦" },
  { to: "/briefs", label: "简报", icon: "✉" },
  { to: "/settings", label: "设置", icon: "⚙" },
];

function LlmStatus() {
  const [status, setStatus] = useState<{ backend: string; detail: string } | null>(null);
  const location = useLocation();
  useEffect(() => {
    api.get<{ backend: string; detail: string }>("/api/llm/status").then(setStatus).catch(() => {});
  }, [location.pathname]);
  if (!status) return null;
  const on = status.backend !== "off";
  return (
    <NavLink to="/settings" className="flex items-center gap-2 text-[12px] text-fg3 hover:text-fg2 no-underline"
       title={status.detail}>
      <span className={`w-2 h-2 rounded-full ${on ? "bg-[#3fb950] live-dot" : "bg-[#5c6b7f]"}`} />
      AI {on ? (status.backend === "api" ? "API" : "CLI") : "未接入"}
    </NavLink>
  );
}

function Clock() {
  const [now, setNow] = useState(new Date());
  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 30_000);
    return () => clearInterval(t);
  }, []);
  return (
    <span className="num text-[12px] text-fg3">
      {now.toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" })}
    </span>
  );
}

export default function App() {
  return (
    <div className="flex min-h-screen">
      <aside className="w-[196px] shrink-0 border-r border-edge bg-panel/40 flex flex-col sticky top-0 h-screen">
        <div className="px-4 pt-5 pb-4">
          <div className="flex items-center gap-2.5">
            <svg width="26" height="26" viewBox="0 0 100 100">
              <rect x="8" y="8" width="38" height="38" rx="7" fill="#f0b429" />
              <rect x="54" y="8" width="38" height="38" rx="7" fill="#2d3a4d" />
              <rect x="8" y="54" width="38" height="38" rx="7" fill="#2d3a4d" />
              <rect x="54" y="54" width="38" height="38" rx="7" fill="#f0b429" opacity=".5" />
            </svg>
            <div>
              <div className="font-bold text-[15px] tracking-wide leading-none">MOSAIC</div>
              <div className="text-[10px] text-fg3 mt-1 leading-none">Variant Perception Engine</div>
            </div>
          </div>
        </div>
        <nav className="px-2.5 flex flex-col gap-0.5">
          {NAV.map((item) => (
            <NavLink key={item.to} to={item.to} end={item.to === "/"}
              className={({ isActive }) => `navlink ${isActive ? "active" : ""}`}>
              <span className="w-4 text-center opacity-80">{item.icon}</span>
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="mt-auto px-4 py-4 border-t border-edge flex items-center justify-between">
          <LlmStatus />
          <Clock />
        </div>
      </aside>

      <main className="flex-1 min-w-0 px-6 py-5 max-w-[1240px]">
        <Routes>
          <Route path="/" element={<Radar />} />
          <Route path="/today" element={<Today />} />
          <Route path="/signals" element={<Signals />} />
          <Route path="/narratives" element={<Narratives />} />
          <Route path="/narratives/:id" element={<NarrativeDetail />} />
          <Route path="/pipeline" element={<Pipeline />} />
          <Route path="/ideas/:id" element={<IdeaDetail />} />
          <Route path="/coverage" element={<Coverage />} />
          <Route path="/tickers/:id" element={<TickerDetail />} />
          <Route path="/briefs" element={<Briefs />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </main>
    </div>
  );
}
