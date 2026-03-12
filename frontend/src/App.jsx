import { useState, useEffect, useRef, useCallback } from "react";
import { fetchAnalytics, fetchHotJobs, fetchJobs, fetchStatus, triggerFetch, fetchTrendMovers, fetchTrendBulk, fetchSkillTrend } from "./api.js";

// ─────────────────────────────────────────────────────────────────────
// SKILL COLOR MAP — used because analytics API doesn't carry colors
// ─────────────────────────────────────────────────────────────────────
const SKILL_COLORS = {
  Python: "#3776AB", JavaScript: "#F7DF1E", TypeScript: "#3178C6",
  Java: "#ED8B00", "C++": "#00599C", "C#": "#9B4993",
  Go: "#00ADD8", Rust: "#CE422B", Ruby: "#CC342D",
  PHP: "#8892BE", Swift: "#FA7343", Kotlin: "#7F52FF",
  Scala: "#DC322F", SQL: "#CC2927", Spark: "#E25A1C",
  AWS: "#FF9900", GCP: "#4285F4", Azure: "#0078D4",
  Cloudflare: "#F38020", Vercel: "#000000",
  Docker: "#2496ED", Kubernetes: "#326CE5", Terraform: "#7B42BC",
  "GitHub Actions": "#2088FF", Linux: "#FCC624", Git: "#F05032",
  "CI/CD": "#8B5CF6",
  "OpenAI API": "#10A37F", LLM: "#8B5CF6", PyTorch: "#EE4C2C",
  TensorFlow: "#FF6F00", "Hugging Face": "#FFD21E", LangChain: "#1C3C3C",
  RAG: "#6366F1", MLOps: "#22C55E", CUDA: "#76B900",
  React: "#61DAFB", "Next.js": "#000000", Vue: "#42B883",
  Angular: "#DD0031", Svelte: "#FF3E00", Tailwind: "#06B6D4",
  "Node.js": "#339933", Django: "#092E20", FastAPI: "#009688",
  Flask: "#000000", Spring: "#6DB33F", Rails: "#CC0000",
  PostgreSQL: "#336791", MySQL: "#4479A1", MongoDB: "#47A248",
  Redis: "#DC382D", Elasticsearch: "#005571", Snowflake: "#29B5E8",
  Firebase: "#FFCA28",
};
const COMPANY_COLORS = {
  // Greenhouse
  Airbnb: "#FF5A5F", Stripe: "#635BFF", Coinbase: "#0052FF",
  Discord: "#5865F2", Pinterest: "#E60023", Twitch: "#9146FF",
  Duolingo: "#58CC02", Robinhood: "#00C805", Brex: "#F5A623",
  Gusto: "#E8423F", Instacart: "#43B02A", Lyft: "#FF00BF",
  Chime: "#00D64F", Carta: "#6941C6", Faire: "#1A1A1A",
  Lattice: "#7B61FF", Anthropic: "#D4A574", xAI: "#AAAAAA",
  "DeepMind": "#4285F4", "Scale AI": "#5B21B6", CoreWeave: "#00C2FF",
  Waymo: "#00B0F0", Cloudflare: "#F38020", Databricks: "#FF3621",
  Datadog: "#632CA6", Elastic: "#005571", MongoDB: "#47A248",
  CockroachDB: "#6933FF", PagerDuty: "#06AC38", Twilio: "#F22F46",
  Okta: "#007DC1", GitLab: "#FC6D26", Amplitude: "#1C52FF",
  Figma: "#A259FF", Airtable: "#FCB400", Asana: "#F06A6A",
  Webflow: "#4353FF", Grammarly: "#15C39A", Dropbox: "#0061FE",
  Calendly: "#0069FF", Vercel: "#888888", Verkada: "#1A1A2E",
  Samsara: "#00857C", Flexport: "#0014CC", Intercom: "#1F8DED",
  Navan: "#1C5EFF",
  Netflix: "#E50914", Shopify: "#96BF48", HubSpot: "#FF7A59",
  Zendesk: "#17494D", Box: "#0061D5", DocuSign: "#FFCC00",
  Squarespace: "#000000", Quora: "#B92B27",
  // Ashby
  OpenAI: "#10A37F", ElevenLabs: "#222222", Runway: "#E83A3A",
  Harvey: "#1C1C1C", Cohere: "#39594D", Pika: "#9B5DE5",
  Ramp: "#16A34A", Notion: "#000000", Linear: "#5E6AD2",
  Cursor: "#00BCD4", Supabase: "#3ECF8E", PostHog: "#F54E00",
  Warp: "#01A4FF", Resend: "#222222", Replit: "#F26207",
  Vanta: "#5B21B6",
  Mistral: "#FF7000", Perplexity: "#20808D",
  "Character.ai": "#7C3AED", "Together AI": "#0F172A",
  Glean: "#FFA500", "Hugging Face": "#FFD21E",
  // FAANG (custom scrapers)
  Amazon: "#FF9900", Google: "#4285F4", Meta: "#0866FF", Apple: "#A2AAAD",
  // Misc
  Reddit: "#FF4500",
  "Weights & Biases": "#FFBE00", Miro: "#FFD02F",
};
const skillColor = (s) => SKILL_COLORS[s] || "#6b7280";
const companyColor = (c) => COMPANY_COLORS[c] || "#6b7280";

// ─────────────────────────────────────────────────────────────────────
// MOBILE DETECTION HOOK
// ─────────────────────────────────────────────────────────────────────
function useIsMobile(breakpoint = 768) {
  const [isMobile, setIsMobile] = useState(() => window.innerWidth < breakpoint);
  useEffect(() => {
    const mq = window.matchMedia(`(max-width: ${breakpoint - 1}px)`);
    const handler = (e) => setIsMobile(e.matches);
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, [breakpoint]);
  return isMobile;
}

// ─────────────────────────────────────────────────────────────────────
// RELATIVE TIME
// ─────────────────────────────────────────────────────────────────────
function relTime(ts) {
  if (!ts) return "";
  const d = new Date(isNaN(ts) ? ts : Number(ts) * 1000);
  if (isNaN(d)) return "";
  const diff = (Date.now() - d) / 1000;
  if (diff < 3600) return `${Math.round(diff / 60)}m`;
  if (diff < 86400) return `${Math.round(diff / 3600)}h`;
  return `${Math.round(diff / 86400)}d`;
}

// ─────────────────────────────────────────────────────────────────────
// UI PRIMITIVES
// ─────────────────────────────────────────────────────────────────────
function WebGLBackground() {
  const canvasRef = useRef(null);
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    let w = (canvas.width = window.innerWidth);
    let h = (canvas.height = window.innerHeight);
    const particles = Array.from({ length: 60 }, () => ({
      x: Math.random() * w, y: Math.random() * h,
      vx: (Math.random() - 0.5) * 0.3, vy: (Math.random() - 0.5) * 0.3,
      r: Math.random() * 2 + 0.5,
    }));
    let raf;
    function draw() {
      ctx.fillStyle = "rgba(7,7,13,0.15)";
      ctx.fillRect(0, 0, w, h);
      for (const p of particles) {
        p.x += p.vx; p.y += p.vy;
        if (p.x < 0 || p.x > w) p.vx *= -1;
        if (p.y < 0 || p.y > h) p.vy *= -1;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(0,240,255,${0.15 + p.r * 0.1})`;
        ctx.fill();
      }
      for (let i = 0; i < particles.length; i++) {
        for (let j = i + 1; j < particles.length; j++) {
          const dx = particles[i].x - particles[j].x;
          const dy = particles[i].y - particles[j].y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < 150) {
            ctx.beginPath();
            ctx.moveTo(particles[i].x, particles[i].y);
            ctx.lineTo(particles[j].x, particles[j].y);
            ctx.strokeStyle = `rgba(0,240,255,${0.04 * (1 - dist / 150)})`;
            ctx.stroke();
          }
        }
      }
      raf = requestAnimationFrame(draw);
    }
    draw();
    const resize = () => { w = canvas.width = window.innerWidth; h = canvas.height = window.innerHeight; };
    window.addEventListener("resize", resize);
    return () => { cancelAnimationFrame(raf); window.removeEventListener("resize", resize); };
  }, []);
  return <canvas ref={canvasRef} style={{ position: "fixed", inset: 0, zIndex: 0, pointerEvents: "none" }} />;
}

function Sparkline({ data, color = "#00f0ff", w = 80, h = 24 }) {
  if (!data || data.length < 2) return null;
  const max = Math.max(...data), min = Math.min(...data), range = max - min || 1;
  const pts = data.map((v, i) => `${(i / (data.length - 1)) * w},${h - ((v - min) / range) * (h - 4) - 2}`).join(" ");
  return (
    <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`}>
      <defs>
        <linearGradient id={`sg-${color.replace("#", "")}`} x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stopColor={color} stopOpacity="0.2" />
          <stop offset="100%" stopColor={color} />
        </linearGradient>
      </defs>
      <polyline fill="none" stroke={`url(#sg-${color.replace("#", "")})`} strokeWidth="1.5" points={pts} />
      <circle cx={w} cy={h - ((data[data.length - 1] - min) / range) * (h - 4) - 2} r="2.5" fill={color} />
    </svg>
  );
}

function BarChart({ data, maxVal, height = 240, isMobile = false }) {
  // Mobile: horizontal bars so labels are fully readable
  if (isMobile) {
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 8, width: "100%" }}>
        {data.map((d, i) => {
          const bw = Math.max(8, (d.value / maxVal) * 100);
          return (
            <div key={i} style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <span style={{ fontSize: 12, color: "#e4e4e7", fontFamily: "mono", fontWeight: 500, width: 90, flexShrink: 0, textAlign: "right" }}>
                {d.label}
              </span>
              <div style={{ flex: 1, height: 20, background: "rgba(255,255,255,0.03)", borderRadius: 4, overflow: "hidden" }}>
                <div style={{
                  width: `${bw}%`, height: "100%", borderRadius: 4,
                  background: `linear-gradient(90deg, ${d.color || "#00f0ff"}44, ${d.color || "#00f0ff"})`,
                  transition: "width 0.5s ease",
                }} />
              </div>
              <span style={{ fontSize: 11, color: "#9ca3af", fontFamily: "mono", fontWeight: 500, width: 45, flexShrink: 0, textAlign: "right" }}>
                {d.value.toLocaleString()}
              </span>
            </div>
          );
        })}
      </div>
    );
  }
  // Desktop: vertical bars
  return (
    <div style={{ display: "flex", alignItems: "flex-end", gap: 6, height, padding: "0 4px", width: "100%" }}>
      {data.map((d, i) => {
        const bh = Math.max(6, (d.value / maxVal) * (height - 48));
        return (
          <div key={i} style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 5, flex: 1, minWidth: 0 }}>
            <span style={{ fontSize: 12, color: "#9ca3af", fontFamily: "mono", fontWeight: 500 }}>{d.value.toLocaleString()}</span>
            <div style={{
              width: "100%", height: bh, borderRadius: "5px 5px 0 0",
              background: `linear-gradient(to top, ${d.color || "#00f0ff"}44, ${d.color || "#00f0ff"})`,
              transition: "height 0.5s ease",
            }} />
            <span style={{
              fontSize: 11, color: "#9ca3af", fontFamily: "mono", textAlign: "center",
              width: "100%", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
            }}>
              {d.label}
            </span>
          </div>
        );
      })}
    </div>
  );
}

function PulsingDot({ color = "#00ff88", size = 8 }) {
  return (
    <span style={{ display: "inline-block", position: "relative", width: size, height: size, marginRight: 6, verticalAlign: "middle" }}>
      <span style={{ position: "absolute", width: size, height: size, borderRadius: "50%", background: color, opacity: 0.4, animation: "pulse 2s ease-in-out infinite" }} />
      <span style={{ position: "absolute", width: size, height: size, borderRadius: "50%", background: color }} />
    </span>
  );
}

function StatCard({ label, value, sub, accent = "#00f0ff" }) {
  return (
    <div className="stat-card">
      <div style={{ fontSize: 10, color: "#6b7280", textTransform: "uppercase", letterSpacing: "0.1em", fontFamily: "mono", marginBottom: 4 }}>{label}</div>
      <div style={{ fontSize: 22, fontWeight: 700, color: accent, fontFamily: "mono" }}>{value}</div>
      {sub && <div style={{ fontSize: 10, color: "#4b5563", fontFamily: "mono", marginTop: 2 }}>{sub}</div>}
    </div>
  );
}

function DeltaBadge({ delta, size = "normal" }) {
  if (delta === null || delta === undefined) {
    return (
      <span style={{
        fontSize: size === "small" ? 9 : 10, padding: size === "small" ? "1px 5px" : "2px 7px",
        borderRadius: 4, fontFamily: "'JetBrains Mono',monospace", fontWeight: 500,
        background: "rgba(107,114,128,0.1)", color: "#6b7280",
      }}>— collecting</span>
    );
  }
  const isUp = delta > 0;
  const isFlat = delta === 0;
  const color = isFlat ? "#6b7280" : isUp ? "#00ff88" : "#ff6b6b";
  const bg = isFlat ? "rgba(107,114,128,0.1)" : isUp ? "rgba(0,255,136,0.1)" : "rgba(255,107,107,0.1)";
  const arrow = isFlat ? "~" : isUp ? "+" : "";
  return (
    <span style={{
      fontSize: size === "small" ? 9 : 10, padding: size === "small" ? "1px 5px" : "2px 7px",
      borderRadius: 4, fontFamily: "'JetBrains Mono',monospace", fontWeight: 500,
      background: bg, color,
    }}>{arrow}{delta}%{isFlat ? "" : isUp ? " ↑" : " ↓"}</span>
  );
}

function TrendChart({ data, color = "#00f0ff", w = 300, h = 80 }) {
  if (!data || data.length < 2) {
    return (
      <div style={{ width: w, height: h, display: "flex", alignItems: "center", justifyContent: "center", color: "#4b5563", fontSize: 11, fontFamily: "'JetBrains Mono',monospace" }}>
        Collecting data...
      </div>
    );
  }
  const max = Math.max(...data.map(d => d.mentions));
  const min = Math.min(...data.map(d => d.mentions));
  const range = max - min || 1;
  const pad = 4;
  const pts = data.map((d, i) =>
    `${pad + (i / (data.length - 1)) * (w - 2 * pad)},${pad + (1 - (d.mentions - min) / range) * (h - 2 * pad)}`
  ).join(" ");
  // Area fill path
  const areaPath = `M ${pad},${h - pad} ` +
    data.map((d, i) =>
      `L ${pad + (i / (data.length - 1)) * (w - 2 * pad)},${pad + (1 - (d.mentions - min) / range) * (h - 2 * pad)}`
    ).join(" ") +
    ` L ${w - pad},${h - pad} Z`;
  return (
    <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`} style={{ display: "block" }}>
      <defs>
        <linearGradient id="tcg" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.2" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={areaPath} fill="url(#tcg)" />
      <polyline fill="none" stroke={color} strokeWidth="2" points={pts} />
      <circle
        cx={pad + ((data.length - 1) / (data.length - 1)) * (w - 2 * pad)}
        cy={pad + (1 - (data[data.length - 1].mentions - min) / range) * (h - 2 * pad)}
        r="3" fill={color}
      />
    </svg>
  );
}

function LoadingSkeleton() {
  const shimmer = { background: "linear-gradient(90deg,rgba(255,255,255,0.03) 25%,rgba(255,255,255,0.07) 50%,rgba(255,255,255,0.03) 75%)", backgroundSize: "200% 100%", animation: "shimmer 1.5s infinite", borderRadius: 6 };
  return (
    <div style={{ padding: 24 }}>
      <div style={{ ...shimmer, height: 200, marginBottom: 16 }} />
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        <div style={{ ...shimmer, height: 160 }} />
        <div style={{ ...shimmer, height: 160 }} />
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────
// AI INSIGHTS fallback (used when analytics snapshot has none yet)
// ─────────────────────────────────────────────────────────────────────
const AI_INSIGHTS = [
  { icon: "🔥", title: "Hottest Skill", text: "OpenAI API adoption is accelerating fastest among all tech skills. It now appears in AI/ML job listings more than any other framework or library.", type: "hot" },
  { icon: "📈", title: "Rising Fast", text: "Rust is crossing mainstream adoption in infrastructure. Cloudflare, Discord, and CoreWeave are leading the charge — look for Rust to crack top-10 languages soon.", type: "trend" },
  { icon: "⚠️", title: "Trend Watch", text: "TypeScript continues to cannibalize plain JavaScript listings. If you're a JS developer without TypeScript, add it to your stack.", type: "warn" },
  { icon: "💰", title: "Salary Insight", text: "Python + Kubernetes + LLM is consistently the highest-paying combination. Adding cloud certifications (AWS/GCP) further boosts compensation.", type: "money" },
  { icon: "🔮", title: "Prediction", text: "Based on current trajectory, Go is on pace to overtake Java in backend listings. Rust and TypeScript are both rising while dynamically-typed languages stabilise.", type: "predict" },
  { icon: "🏢", title: "Company Intel", text: "AI-focused companies (OpenAI, Anthropic, Cohere, xAI) are hiring aggressively. Infrastructure and cloud companies show strong demand for Go/Rust engineers.", type: "company" },
];

// Normalise a job from /api/jobs/ to the same shape as /api/hotjobs/
// The serializer exposes `apply_link` (= apply_url || source_url) and `salary_display`
function normaliseJob(j) {
  return {
    ...j,
    skills: j.extracted_skills || [],
    url: j.apply_link || "#",           // apply_link is the serializer's computed field
    salary: j.salary_display || "Competitive",
    time: relTime(j.posted_at || j.first_seen),
    hot: (j.salary_min || 0) > 150_000 || (j.extracted_skills || []).length > 5,
    source_label: j.company || j.source,
  };
}

// ─────────────────────────────────────────────────────────────────────
// RESPONSIVE CSS
// ─────────────────────────────────────────────────────────────────────
const RESPONSIVE_CSS = `
  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&family=Inter:wght@400;500;600;700&display=swap');
  @keyframes pulse { 0%,100%{transform:scale(1);opacity:.4} 50%{transform:scale(2.5);opacity:0} }
  @keyframes fadeUp { from{opacity:0;transform:translateY(12px)} to{opacity:1;transform:translateY(0)} }
  @keyframes glow { 0%,100%{box-shadow:0 0 20px rgba(0,240,255,.08)} 50%{box-shadow:0 0 40px rgba(0,240,255,.15)} }
  @keyframes shimmer { 0%{background-position:-200% 0} 100%{background-position:200% 0} }
  @keyframes spin { to{transform:rotate(360deg)} }
  *{box-sizing:border-box;scrollbar-width:thin;scrollbar-color:#1a1a2e #07070d}
  *::-webkit-scrollbar{width:5px}*::-webkit-scrollbar-track{background:#07070d}*::-webkit-scrollbar-thumb{background:#1a1a2e;border-radius:3px}
  a{color:#00f0ff;text-decoration:none}a:hover{text-decoration:underline}
  button:hover{opacity:.85}
  .search-input::placeholder{color:#4b5563}
  .search-input:focus{outline:none;border-color:rgba(0,240,255,0.4);box-shadow:0 0 0 3px rgba(0,240,255,0.06)}

  /* ── Header ── */
  .app-header {
    position:relative; z-index:10; border-bottom:1px solid rgba(0,240,255,0.08);
    padding:14px 24px; display:flex; align-items:center; justify-content:space-between;
    background:rgba(7,7,13,0.85); backdrop-filter:blur(20px); gap:12px;
  }
  .header-left { display:flex; align-items:center; gap:14px; }
  .header-right { display:flex; align-items:center; gap:16px; flex-shrink:0; }

  /* ── Stats grid ── */
  .stats-grid {
    display:grid; grid-template-columns:repeat(5,1fr);
    border-bottom:1px solid rgba(0,240,255,0.06); position:relative; z-index:10;
    background:rgba(7,7,13,0.6);
  }
  .stat-card { padding:16px 20px; border-right:1px solid rgba(0,240,255,0.06); }

  /* ── Nav tabs ── */
  .nav-tabs {
    position:relative; z-index:10; padding:12px 24px;
    display:flex; gap:6px; flex-wrap:wrap;
    border-bottom:1px solid rgba(0,240,255,0.08);
    background:rgba(7,7,13,0.7); backdrop-filter:blur(12px);
    overflow-x:auto; -webkit-overflow-scrolling:touch;
  }
  .nav-tabs::-webkit-scrollbar { height:0; display:none; }
  .nav-tabs { scrollbar-width:none; }
  .tab-btn {
    white-space:nowrap; flex-shrink:0; border-radius:8px;
    transition:all 0.2s ease;
  }
  .tab-btn:hover { background:rgba(0,240,255,0.08) !important; color:#e4e4e7 !important; }

  /* ── Content area ── */
  .content-area { position:relative; z-index:10; padding:24px; }

  /* ── Overview grid ── */
  .overview-grid { display:grid; grid-template-columns:1fr 1fr; gap:16px; animation:fadeUp .3s ease; }
  .overview-full-row { grid-column:1 / -1; }

  /* ── Hot jobs preview (overview page) ── */
  .hot-jobs-preview { display:grid; grid-template-columns:repeat(4,1fr); gap:10px; }

  /* ── Companies grid ── */
  .companies-grid { display:grid; grid-template-columns:repeat(3,1fr); gap:10px; }

  /* ── Jobs grid ── */
  .jobs-grid { display:grid; grid-template-columns:repeat(2,1fr); gap:12px; }

  /* ── AI insights grid ── */
  .insights-grid { display:grid; grid-template-columns:1fr 1fr; gap:12px; }

  /* ── Table scroll wrapper ── */
  .table-scroll { overflow-x:auto; -webkit-overflow-scrolling:touch; }
  .table-scroll::-webkit-scrollbar { height:4px; }

  /* ── Combo row ── */
  .combo-row {
    display:flex; align-items:center; gap:16px; padding:12px 16px;
    border-bottom:1px solid rgba(255,255,255,0.03);
  }
  .combo-label { width:200px; font-size:13px; flex-shrink:0; }
  .combo-bar { flex:1; height:16px; background:rgba(255,255,255,0.03); border-radius:4px; overflow:hidden; min-width:60px; }

  /* ── Footer ── */
  .app-footer {
    position:relative; z-index:10; padding:20px 24px;
    border-top:1px solid rgba(0,240,255,0.04);
    display:flex; justify-content:space-between; font-size:10px;
    color:#4b5563; font-family:'JetBrains Mono','IBM Plex Mono','SF Mono','Fira Code',monospace;
  }

  /* ── Search bar ── */
  .search-bar { display:flex; gap:8px; align-items:center; margin-bottom:16px; }

  /* ══════════════════════════════════════════════════════════════════
     MOBILE BREAKPOINT — 768px
     ══════════════════════════════════════════════════════════════════ */
  @media (max-width: 768px) {
    .app-header {
      flex-wrap:wrap; padding:12px 16px; gap:10px;
    }
    .header-right { width:100%; justify-content:space-between; }

    .stats-grid { grid-template-columns:repeat(2,1fr); }
    .stat-card { padding:12px 14px; }
    .stat-card:last-child { border-right:none; }
    /* On 2-col, remove right border on even items */
    .stat-card:nth-child(2n) { border-right:none; }

    .nav-tabs { padding:10px 12px; gap:4px; }

    .content-area { padding:16px 12px; }

    .overview-grid { grid-template-columns:1fr; gap:12px; }
    .hot-jobs-preview { grid-template-columns:1fr; gap:8px; }
    .companies-grid { grid-template-columns:1fr 1fr; gap:8px; }
    .jobs-grid { grid-template-columns:1fr; gap:10px; }
    .insights-grid { grid-template-columns:1fr; gap:10px; }

    .combo-row { flex-wrap:wrap; gap:8px; padding:10px 12px; }
    .combo-label { width:100%; }
    .combo-bar { width:100%; }

    .app-footer { flex-direction:column; gap:6px; text-align:center; padding:16px 12px; }

    .search-bar { flex-direction:column; align-items:stretch; }

    /* Table min-width so it scrolls horizontally */
    .skill-table { min-width:520px; }
  }

  /* ══════════════════════════════════════════════════════════════════
     SMALL MOBILE — 480px
     ══════════════════════════════════════════════════════════════════ */
  @media (max-width: 480px) {
    .app-header { padding:10px 12px; }
    .stats-grid { grid-template-columns:1fr 1fr; }
    .stat-card { padding:10px 12px; }
    .content-area { padding:12px 8px; }
    .companies-grid { grid-template-columns:1fr; }
  }
`;

// ─────────────────────────────────────────────────────────────────────
// MAIN DASHBOARD
// ─────────────────────────────────────────────────────────────────────
export default function SkillTreeDashboard() {
  const [tab, setTab] = useState("overview");
  const [tickerX, setTickerX] = useState(0);
  const isMobile = useIsMobile();

  // API state
  const [analytics, setAnalytics] = useState(null);
  const [jobs, setJobs] = useState([]);
  const [hotJobs, setHotJobs] = useState([]);
  const [hotJobsSources, setHotJobsSources] = useState([]);
  const [fetchStatusData, setFetchStatusData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [fetchingNow, setFetchingNow] = useState(false);
  const [error, setError] = useState(null);

  // Search
  const [jobSearch, setJobSearch] = useState("");
  const [searchResults, setSearchResults] = useState(null); // null = not searching
  const [searchLoading, setSearchLoading] = useState(false);

  // Trends
  const [trendMovers, setTrendMovers] = useState({ risers: [], fallers: [] });
  const [trendBulk, setTrendBulk] = useState({ sparklines: {}, deltas: {} });
  const [selectedSkill, setSelectedSkill] = useState(null);
  const [skillTrendData, setSkillTrendData] = useState(null);

  // True while the server has jobs in DB but analytics snapshot not yet saved
  const analyticsPending = analytics?._pending === true;

  // Derived data from analytics
  const skillRankings = (analytics?.skill_rankings || []).map((s) => ({
    ...s,
    color: skillColor(s.skill),
    trend: Array(10).fill(s.pct),
  }));
  const combos = analytics?.skill_combos || [];
  const topCompanies = (analytics?.top_companies || []).slice(0, 15).map((c) => ({
    ...c,
    color: companyColor(c.company),
  }));
  const meta = analytics?.meta || {};
  const remoteInfo = analytics?.remote || {};
  const salaryInfo = analytics?.salary || {};

  // What to show in the Hot Jobs grid
  const displayedJobs = searchResults !== null ? searchResults : hotJobs;

  // Live ticker text
  const topSkill = skillRankings[0]?.skill || "Python";
  const topSkillPct = skillRankings[0]?.pct || 0;
  const totalJobs = meta.total_jobs || 0;
  const ticker = totalJobs
    ? `🔥 ${topSkill} #1 at ${topSkillPct}% demand  •  ${totalJobs.toLocaleString()} jobs tracked  •  Remote: ${remoteInfo.pct || 0}%  •  Avg salary: $${salaryInfo.avg_min ? Math.round(salaryInfo.avg_min / 1000) + "K" : "–"}–$${salaryInfo.avg_max ? Math.round(salaryInfo.avg_max / 1000) + "K" : "–"}  •  Unique skills tracked: ${meta.unique_skills || 0}  •  `
    : "Loading job market data...  •  ";

  // Load analytics + status on mount
  useEffect(() => {
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const [ana, jobData, st] = await Promise.allSettled([
          fetchAnalytics(),
          fetchJobs({ size: 50 }),
          fetchStatus(),
        ]);
        if (ana.status === "fulfilled") setAnalytics(ana.value);
        else setAnalytics(null);
        if (jobData.status === "fulfilled") setJobs(jobData.value.jobs || []);
        if (st.status === "fulfilled") setFetchStatusData(st.value);
      } catch (e) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    }
    load();

    let intervalMs = 10_000;
    let intervalId;
    function schedulePoll() {
      intervalId = setTimeout(async () => {
        try {
          const s = await fetchStatus();
          setFetchStatusData(s);
          const needsRefresh = s.status === "success" || s.status === "running";
          if (needsRefresh) {
            const [ana, jobData] = await Promise.all([fetchAnalytics(), fetchJobs({ size: 50 })]);
            setAnalytics(ana);
            setJobs(jobData.jobs || []);
          }
          intervalMs = (s.status === "running") ? 10_000 : 60_000;
        } catch {}
        schedulePoll();
      }, intervalMs);
    }
    schedulePoll();
    return () => clearTimeout(intervalId);
  }, []);

  // Hot jobs: load immediately, then re-load when the 20-min rotation window turns
  useEffect(() => {
    let timerId;
    async function loadHotJobs() {
      try {
        const data = await fetchHotJobs();
        setHotJobs(
          (data.jobs || []).map((j) => ({
            ...j,
            salary: j.salary || "Competitive",
            time: relTime(j.posted_at || j.first_seen),
          }))
        );
        setHotJobsSources(data.sources || []);
        const delay = Math.max(10_000, (data.next_rotation_in || 1200) * 1000);
        timerId = setTimeout(loadHotJobs, delay);
      } catch {}
    }
    loadHotJobs();
    return () => clearTimeout(timerId);
  }, []);

  // Trend data: load movers + bulk sparklines/deltas alongside analytics
  useEffect(() => {
    async function loadTrends() {
      try {
        const [movers, bulk] = await Promise.allSettled([
          fetchTrendMovers(7, 5),
          fetchTrendBulk(30, 7),
        ]);
        if (movers.status === "fulfilled") setTrendMovers(movers.value);
        if (bulk.status === "fulfilled") setTrendBulk(bulk.value);
      } catch {}
    }
    loadTrends();
    const id = setInterval(loadTrends, 300_000); // refresh every 5 min
    return () => clearInterval(id);
  }, []);

  // Load individual skill trend when selected
  useEffect(() => {
    if (!selectedSkill) { setSkillTrendData(null); return; }
    let cancelled = false;
    async function load() {
      try {
        const data = await fetchSkillTrend(selectedSkill, 90);
        if (!cancelled) setSkillTrendData(data);
      } catch { if (!cancelled) setSkillTrendData(null); }
    }
    load();
    return () => { cancelled = true; };
  }, [selectedSkill]);

  // Debounced search — calls /api/jobs/?search=... on title, company, description (includes tech)
  useEffect(() => {
    const q = jobSearch.trim();
    if (q.length < 2) {
      setSearchResults(null);
      return;
    }
    setSearchLoading(true);
    const t = setTimeout(async () => {
      try {
        const data = await fetchJobs({ search: q, size: 50 });
        setSearchResults((data.jobs || []).map(normaliseJob));
      } catch {}
      finally { setSearchLoading(false); }
    }, 350);
    return () => clearTimeout(t);
  }, [jobSearch]);

  // Ticker animation
  useEffect(() => {
    const t = setInterval(() => setTickerX((p) => p - 1), 25);
    return () => clearInterval(t);
  }, []);

  const handleManualFetch = useCallback(async () => {
    if (fetchingNow) return;
    setFetchingNow(true);
    try {
      await triggerFetch();
      setFetchStatusData((prev) => ({ ...prev, status: "running" }));
    } catch (e) {
      alert(e.message);
    } finally {
      setFetchingNow(false);
    }
  }, [fetchingNow]);

  const mono = "'JetBrains Mono','IBM Plex Mono','SF Mono','Fira Code',monospace";
  const sans = "'Inter','SF Pro Display',-apple-system,sans-serif";

  const tabs = [
    { id: "overview", label: "Overview" },
    { id: "trends", label: "Trends" },
    { id: "languages", label: "Languages" },
    { id: "skills", label: "All Skills" },
    { id: "companies", label: "Companies" },
    { id: "combos", label: "Skill Combos" },
    { id: "jobs", label: "Hot Jobs" },
    { id: "ai", label: "AI Insights" },
  ];

  const maxJobVal = Math.max(...(topCompanies.map((c) => c.jobs)), 1);
  const maxSkillVal = Math.max(...(skillRankings.map((s) => s.jobs)), 1);

  // On mobile, horizontal bars handle any count; on desktop limit vertical bars
  const chartSlice = isMobile ? 8 : 8;
  const chartHeight = isMobile ? 180 : 240;

  const statusColor =
    fetchStatusData?.status === "running" ? "#ffaa00"
    : fetchStatusData?.status === "success" ? "#00ff88"
    : fetchStatusData?.status === "error" ? "#ff6b6b"
    : "#6b7280";

  return (
    <div style={{ background: "#07070d", minHeight: "100vh", color: "#e4e4e7", fontFamily: sans, position: "relative" }}>
      <style>{RESPONSIVE_CSS}</style>

      <WebGLBackground />

      {/* ── HEADER ───────────────────────────────────── */}
      <header className="app-header">
        <div className="header-left">
          <div style={{ fontSize: isMobile ? 18 : 22, fontWeight: 700, fontFamily: mono }}>
            <span style={{ background: "linear-gradient(135deg,#00f0ff,#00ff88)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>SkillTree</span>
            <span style={{ color: "#4b5563", fontSize: 13 }}>.dev</span>
          </div>
          <div style={{ fontSize: 9, padding: "3px 10px", borderRadius: 4, background: `rgba(0,255,136,0.08)`, color: statusColor, fontFamily: mono, letterSpacing: "0.08em", display: "flex", alignItems: "center" }}>
            <PulsingDot color={statusColor} size={6} />
            {fetchStatusData?.status === "running" ? "FETCHING" : fetchStatusData?.status === "success" ? "LIVE" : "IDLE"}
          </div>
        </div>
        <div className="header-right">
          {fetchStatusData?.jobs_in_db !== undefined && (
            <span style={{ fontSize: 11, color: "#4b5563", fontFamily: mono }}>
              {fetchStatusData.jobs_in_db.toLocaleString()} jobs in DB
            </span>
          )}
          <button
            onClick={handleManualFetch}
            disabled={fetchingNow || fetchStatusData?.status === "running"}
            style={{ fontSize: 11, padding: "5px 14px", borderRadius: 6, border: "1px solid rgba(0,240,255,0.2)", background: "rgba(0,240,255,0.06)", color: "#00f0ff", cursor: "pointer", fontFamily: mono }}
          >
            {fetchingNow ? "⟳ Starting..." : "↻ Refresh Data"}
          </button>
        </div>
      </header>

      {/* ── TICKER ───────────────────────────────────── */}
      <div style={{ borderBottom: "1px solid rgba(0,240,255,0.04)", padding: "6px 0", overflow: "hidden", background: "rgba(0,240,255,0.015)", position: "relative", zIndex: 10 }}>
        <div style={{ whiteSpace: "nowrap", fontSize: 11, color: "#00f0ff", fontFamily: mono, transform: `translateX(${tickerX % 2000}px)`, opacity: 0.6 }}>
          {ticker.repeat(4)}
        </div>
      </div>

      {/* ── STATS BAR ─────────────────────────────────── */}
      <div className="stats-grid">
        <StatCard label="Total Jobs" value={totalJobs ? totalJobs.toLocaleString() : "—"} sub={Object.keys(meta.sources || {}).length ? `${Object.keys(meta.sources).length} sources` : "loading..."} />
        <StatCard label="Skills Tracked" value={meta.unique_skills || "—"} sub="across 11 categories" />
        <StatCard label="Remote Jobs" value={remoteInfo.pct !== undefined ? `${remoteInfo.pct}%` : "—"} sub={remoteInfo.remote ? `${remoteInfo.remote.toLocaleString()} listings` : ""} accent="#00ff88" />
        <StatCard label="Avg Salary" value={salaryInfo.avg_min ? `$${Math.round(salaryInfo.avg_min / 1000)}K` : "—"} sub={salaryInfo.with_data ? `${salaryInfo.with_data} jobs with data` : ""} accent="#ffaa00" />
        <StatCard label="Top Skill" value={skillRankings[0]?.skill || "—"} sub={skillRankings[0] ? `${skillRankings[0].pct}% of all jobs` : ""} accent={skillRankings[0] ? skillColor(skillRankings[0].skill) : "#6b7280"} />
      </div>

      {/* ── NAV TABS ──────────────────────────────────── */}
      <div className="nav-tabs">
        {tabs.map((t) => (
          <button key={t.id} className="tab-btn" onClick={() => setTab(t.id)} style={{
            padding: isMobile ? "8px 14px" : "9px 20px",
            fontSize: isMobile ? 12 : 13,
            fontFamily: mono,
            cursor: "pointer",
            border: tab === t.id ? "1px solid rgba(0,240,255,0.3)" : "1px solid rgba(255,255,255,0.06)",
            borderRadius: 8,
            background: tab === t.id ? "rgba(0,240,255,0.1)" : "rgba(255,255,255,0.03)",
            color: tab === t.id ? "#00f0ff" : "#9ca3af",
            transition: "all 0.2s",
            fontWeight: tab === t.id ? 600 : 500,
            letterSpacing: "0.02em",
          }}>{t.label}</button>
        ))}
      </div>

      {/* ── CONTENT ───────────────────────────────────── */}
      <div className="content-area">

        {error && (
          <div style={{ padding: 16, marginBottom: 16, borderRadius: 8, background: "rgba(255,100,100,0.08)", border: "1px solid rgba(255,100,100,0.2)", color: "#ff6b6b", fontFamily: mono, fontSize: 13 }}>
            ⚠️ {error} — Is the Django server running? <a href="#" onClick={(e) => { e.preventDefault(); window.location.reload(); }} style={{ color: "#00f0ff" }}>Retry</a>
          </div>
        )}

        {/* First-run banner */}
        {!loading && analyticsPending && (
          <div style={{ padding: "12px 16px", marginBottom: 16, borderRadius: 8, background: "rgba(255,170,0,0.06)", border: "1px solid rgba(255,170,0,0.2)", color: "#ffaa00", fontFamily: mono, fontSize: 12, display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
            <span style={{ display: "inline-block", width: 10, height: 10, borderRadius: "50%", background: "#ffaa00", animation: "pulse 1.5s ease-in-out infinite" }} />
            First scrape in progress — {meta.total_jobs ? `${meta.total_jobs.toLocaleString()} jobs collected so far.` : "collecting jobs from all sources…"}
            {" "}Skill analytics will appear automatically when the fetch completes. This takes 2–5 minutes.
          </div>
        )}

        {loading ? (
          <LoadingSkeleton />
        ) : (
          <>
            {/* ════ OVERVIEW ════ */}
            {tab === "overview" && (
              <div className="overview-grid">

                {/* ── MARKET MOVERS ── */}
                {(trendMovers.risers.length > 0 || trendMovers.fallers.length > 0) && (
                  <div className="overview-full-row" style={{ border: "1px solid rgba(0,240,255,0.1)", borderRadius: 12, padding: isMobile ? 14 : 20, background: "rgba(0,240,255,0.02)", animation: "glow 4s ease infinite" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
                      <h3 style={{ fontSize: 13, fontFamily: mono, color: "#00f0ff", fontWeight: 600 }}>📈 MARKET MOVERS</h3>
                      <button onClick={() => setTab("trends")} style={{ fontSize: 11, color: "#00f0ff", background: "rgba(0,240,255,0.06)", border: "1px solid rgba(0,240,255,0.2)", borderRadius: 6, padding: "4px 12px", cursor: "pointer", fontFamily: mono }}>Details →</button>
                    </div>
                    <div style={{ display: "grid", gridTemplateColumns: isMobile ? "1fr" : "1fr 1fr", gap: 16 }}>
                      {/* Risers */}
                      <div>
                        <div style={{ fontSize: 10, color: "#00ff88", fontFamily: mono, marginBottom: 8, textTransform: "uppercase", letterSpacing: "0.1em" }}>Rising</div>
                        {trendMovers.risers.map((r, i) => (
                          <div key={r.skill} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "6px 0", borderBottom: "1px solid rgba(255,255,255,0.03)" }}>
                            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                              <span style={{ color: "#00ff88", fontSize: 12 }}>▲</span>
                              <button onClick={() => { setSelectedSkill(r.skill); setTab("trends"); }} style={{ background: "none", border: "none", color: "#e4e4e7", cursor: "pointer", fontWeight: 500, fontSize: 13, padding: 0 }}>{r.skill}</button>
                            </div>
                            <DeltaBadge delta={r.delta_pct} size="small" />
                          </div>
                        ))}
                        {trendMovers.risers.length === 0 && <div style={{ fontSize: 11, color: "#4b5563", fontFamily: mono }}>Collecting data...</div>}
                      </div>
                      {/* Fallers */}
                      <div>
                        <div style={{ fontSize: 10, color: "#ff6b6b", fontFamily: mono, marginBottom: 8, textTransform: "uppercase", letterSpacing: "0.1em" }}>Falling</div>
                        {trendMovers.fallers.map((f, i) => (
                          <div key={f.skill} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "6px 0", borderBottom: "1px solid rgba(255,255,255,0.03)" }}>
                            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                              <span style={{ color: "#ff6b6b", fontSize: 12 }}>▼</span>
                              <button onClick={() => { setSelectedSkill(f.skill); setTab("trends"); }} style={{ background: "none", border: "none", color: "#e4e4e7", cursor: "pointer", fontWeight: 500, fontSize: 13, padding: 0 }}>{f.skill}</button>
                            </div>
                            <DeltaBadge delta={f.delta_pct} size="small" />
                          </div>
                        ))}
                        {trendMovers.fallers.length === 0 && <div style={{ fontSize: 11, color: "#4b5563", fontFamily: mono }}>Collecting data...</div>}
                      </div>
                    </div>
                  </div>
                )}

                <div style={{ border: "1px solid rgba(0,240,255,0.08)", borderRadius: 12, padding: isMobile ? 14 : 20, background: "rgba(255,255,255,0.01)" }}>
                  <h3 style={{ fontSize: 13, fontFamily: mono, color: "#00f0ff", marginBottom: 16, fontWeight: 600 }}>📊 TOP LANGUAGES BY DEMAND</h3>
                  <BarChart
                    isMobile={isMobile}
                    data={skillRankings.filter((s) => s.category === "languages").slice(0, chartSlice).map((s) => ({ label: s.skill, value: s.jobs, color: s.color }))}
                    maxVal={maxSkillVal} height={chartHeight}
                  />
                </div>

                <div style={{ border: "1px solid rgba(0,240,255,0.08)", borderRadius: 12, padding: isMobile ? 14 : 20, background: "rgba(255,255,255,0.01)" }}>
                  <h3 style={{ fontSize: 13, fontFamily: mono, color: "#00f0ff", marginBottom: 16, fontWeight: 600 }}>🤖 AI & CLOUD DEMAND</h3>
                  <BarChart
                    isMobile={isMobile}
                    data={skillRankings.filter((s) => s.category === "ai_ml" || s.category === "cloud").slice(0, chartSlice).map((s) => ({ label: s.skill, value: s.jobs, color: s.color }))}
                    maxVal={maxSkillVal} height={chartHeight}
                  />
                </div>

                <div style={{ border: "1px solid rgba(0,240,255,0.1)", borderRadius: 12, padding: isMobile ? 14 : 20, background: "rgba(0,240,255,0.02)", animation: "glow 4s ease infinite" }}>
                  <h3 style={{ fontSize: 13, fontFamily: mono, color: "#00f0ff", marginBottom: 14, fontWeight: 600 }}>🧠 AI INTELLIGENCE BRIEF</h3>
                  {(analytics?.ai_insights || AI_INSIGHTS).slice(0, 3).map((ins, i) => (
                    <div key={i} style={{ marginBottom: 12, padding: "10px 12px", borderRadius: 8, background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.04)" }}>
                      <div style={{ fontSize: 11, fontWeight: 600, color: ins.type === "hot" ? "#ff6b6b" : ins.type === "warn" ? "#ffaa00" : "#00ff88", marginBottom: 4 }}>{ins.icon} {ins.title}</div>
                      <div style={{ fontSize: 12, color: "#9ca3af", lineHeight: 1.5 }}>{ins.text}</div>
                    </div>
                  ))}
                </div>

                <div style={{ border: "1px solid rgba(0,240,255,0.08)", borderRadius: 12, padding: isMobile ? 14 : 20, background: "rgba(255,255,255,0.01)" }}>
                  <h3 style={{ fontSize: 13, fontFamily: mono, color: "#00f0ff", marginBottom: 14, fontWeight: 600 }}>🔗 HOTTEST SKILL COMBOS</h3>
                  {combos.slice(0, 6).map((c, i) => (
                    <div key={i} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "8px 0", borderBottom: "1px solid rgba(255,255,255,0.03)", gap: 8, flexWrap: "wrap" }}>
                      <span style={{ fontSize: 12 }}>
                        {c.combo.split(" + ").map((s, j) => (
                          <span key={j}>{j > 0 && <span style={{ color: "#4b5563", margin: "0 4px" }}>+</span>}<span style={{ color: "#00f0ff", fontWeight: 500 }}>{s}</span></span>
                        ))}
                      </span>
                      <span style={{ fontSize: 11, fontFamily: mono, color: "#6b7280", whiteSpace: "nowrap" }}>{c.jobs} jobs ({c.pct}%)</span>
                    </div>
                  ))}
                </div>

                <div className="overview-full-row" style={{ border: "1px solid rgba(0,240,255,0.08)", borderRadius: 12, padding: isMobile ? 14 : 20, background: "rgba(255,255,255,0.01)" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
                    <h3 style={{ fontSize: 13, fontFamily: mono, color: "#00f0ff", fontWeight: 600 }}>💼 HOT JOBS — APPLY NOW</h3>
                    <button onClick={() => setTab("jobs")} style={{ fontSize: 11, color: "#00f0ff", background: "rgba(0,240,255,0.06)", border: "1px solid rgba(0,240,255,0.2)", borderRadius: 6, padding: "4px 12px", cursor: "pointer", fontFamily: mono }}>View All →</button>
                  </div>
                  <div className="hot-jobs-preview">
                    {hotJobs.slice(0, isMobile ? 3 : 4).map((job, i) => (
                      <a key={i} href={job.url} target="_blank" rel="noopener noreferrer" style={{ border: "1px solid rgba(0,240,255,0.08)", borderRadius: 10, padding: isMobile ? 12 : 14, background: job.hot ? "rgba(255,100,100,0.03)" : "rgba(255,255,255,0.01)", display: "block", textDecoration: "none", color: "#e4e4e7" }}>
                        {job.hot && <div style={{ fontSize: 9, color: "#ff6b6b", fontFamily: mono, marginBottom: 6 }}>🔥 TRENDING</div>}
                        <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 4, wordBreak: "break-word" }}>{job.title}</div>
                        <div style={{ fontSize: 11, color: "#6b7280", marginBottom: 8 }}>{job.company} • {job.location || "Remote"}</div>
                        <div style={{ display: "flex", gap: 3, flexWrap: "wrap", marginBottom: 8 }}>
                          {(job.skills || []).slice(0, 3).map((s) => (
                            <span key={s} style={{ fontSize: 9, padding: "2px 6px", borderRadius: 3, background: "rgba(0,240,255,0.06)", color: "#00f0ff", fontFamily: mono }}>{s}</span>
                          ))}
                        </div>
                        <div style={{ fontSize: 12, fontWeight: 600, color: "#00ff88", fontFamily: mono }}>{job.salary}</div>
                      </a>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* ════ TRENDS ════ */}
            {tab === "trends" && (
              <div style={{ animation: "fadeUp .3s ease" }}>

                {/* ── Skill Detail View ── */}
                {selectedSkill && skillTrendData ? (
                  <div>
                    <button onClick={() => setSelectedSkill(null)} style={{ fontSize: 11, color: "#00f0ff", background: "rgba(0,240,255,0.06)", border: "1px solid rgba(0,240,255,0.2)", borderRadius: 6, padding: "5px 14px", cursor: "pointer", fontFamily: mono, marginBottom: 16 }}>← Back to Overview</button>
                    <div style={{ border: "1px solid rgba(0,240,255,0.1)", borderRadius: 12, padding: isMobile ? 14 : 24, background: "rgba(0,240,255,0.02)", marginBottom: 16 }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20, flexWrap: "wrap", gap: 12 }}>
                        <div>
                          <h2 style={{ fontSize: isMobile ? 18 : 24, fontWeight: 700, fontFamily: mono, color: skillColor(selectedSkill), margin: 0 }}>{selectedSkill}</h2>
                          <div style={{ fontSize: 11, color: "#6b7280", fontFamily: mono, marginTop: 4 }}>90-day demand trend</div>
                        </div>
                        <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
                          <div style={{ textAlign: "center", padding: "8px 14px", borderRadius: 8, background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.04)" }}>
                            <div style={{ fontSize: 9, color: "#6b7280", fontFamily: mono }}>RANK</div>
                            <div style={{ fontSize: 18, fontWeight: 700, color: "#00f0ff", fontFamily: mono }}>#{skillTrendData.rank || "—"}</div>
                          </div>
                          <div style={{ textAlign: "center", padding: "8px 14px", borderRadius: 8, background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.04)" }}>
                            <div style={{ fontSize: 9, color: "#6b7280", fontFamily: mono }}>MENTIONS</div>
                            <div style={{ fontSize: 18, fontWeight: 700, color: "#e4e4e7", fontFamily: mono }}>{skillTrendData.current_mentions?.toLocaleString() || "—"}</div>
                          </div>
                          <div style={{ textAlign: "center", padding: "8px 14px", borderRadius: 8, background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.04)" }}>
                            <div style={{ fontSize: 9, color: "#6b7280", fontFamily: mono }}>7D DELTA</div>
                            <div style={{ fontSize: 14, fontWeight: 600, marginTop: 2 }}><DeltaBadge delta={skillTrendData.delta_7d} /></div>
                          </div>
                          <div style={{ textAlign: "center", padding: "8px 14px", borderRadius: 8, background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.04)" }}>
                            <div style={{ fontSize: 9, color: "#6b7280", fontFamily: mono }}>30D DELTA</div>
                            <div style={{ fontSize: 14, fontWeight: 600, marginTop: 2 }}><DeltaBadge delta={skillTrendData.delta_30d} /></div>
                          </div>
                          <div style={{ textAlign: "center", padding: "8px 14px", borderRadius: 8, background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.04)" }}>
                            <div style={{ fontSize: 9, color: "#6b7280", fontFamily: mono }}>VELOCITY</div>
                            <div style={{ fontSize: 14, fontWeight: 600, color: skillTrendData.velocity === "accelerating" ? "#00ff88" : skillTrendData.velocity === "decelerating" ? "#ff6b6b" : "#6b7280", fontFamily: mono, marginTop: 2 }}>
                              {skillTrendData.velocity === "accelerating" ? "⇡ Accel" : skillTrendData.velocity === "decelerating" ? "⇣ Decel" : skillTrendData.velocity === "stable" ? "~ Stable" : "—"}
                            </div>
                          </div>
                        </div>
                      </div>
                      {skillTrendData.timeseries && skillTrendData.timeseries.length >= 2 ? (
                        <TrendChart data={skillTrendData.timeseries} color={skillColor(selectedSkill)} w={isMobile ? 280 : 700} h={isMobile ? 120 : 200} />
                      ) : (
                        <div style={{ padding: "40px 0", textAlign: "center", color: "#4b5563", fontFamily: mono, fontSize: 12 }}>
                          Collecting trend data... Chart will appear after 2+ data points.
                        </div>
                      )}
                    </div>
                  </div>
                ) : (
                  /* ── Trends Overview ── */
                  <div>
                    {/* Market Movers */}
                    <div style={{ display: "grid", gridTemplateColumns: isMobile ? "1fr" : "1fr 1fr", gap: 16, marginBottom: 16 }}>
                      {/* Risers */}
                      <div style={{ border: "1px solid rgba(0,255,136,0.15)", borderRadius: 12, padding: isMobile ? 14 : 20, background: "rgba(0,255,136,0.02)" }}>
                        <h3 style={{ fontSize: 13, fontFamily: mono, color: "#00ff88", marginBottom: 14, fontWeight: 600 }}>▲ RISING SKILLS</h3>
                        {trendMovers.risers.length > 0 ? trendMovers.risers.map((r, i) => (
                          <div key={r.skill} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "8px 0", borderBottom: "1px solid rgba(255,255,255,0.03)", animation: `fadeUp .3s ease ${i * 0.05}s both` }}>
                            <button onClick={() => setSelectedSkill(r.skill)} style={{ background: "none", border: "none", color: "#e4e4e7", cursor: "pointer", fontWeight: 600, fontSize: 14, padding: 0, display: "flex", alignItems: "center", gap: 8 }}>
                              <div style={{ width: 8, height: 8, borderRadius: 2, background: skillColor(r.skill), flexShrink: 0 }} />
                              {r.skill}
                            </button>
                            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                              <span style={{ fontSize: 11, color: "#6b7280", fontFamily: mono }}>{r.current_mentions} jobs</span>
                              <DeltaBadge delta={r.delta_pct} />
                            </div>
                          </div>
                        )) : (
                          <div style={{ padding: "20px 0", textAlign: "center", color: "#4b5563", fontFamily: mono, fontSize: 12 }}>
                            Collecting data... Trends will appear after 2+ scrape cycles.
                          </div>
                        )}
                      </div>
                      {/* Fallers */}
                      <div style={{ border: "1px solid rgba(255,107,107,0.15)", borderRadius: 12, padding: isMobile ? 14 : 20, background: "rgba(255,107,107,0.02)" }}>
                        <h3 style={{ fontSize: 13, fontFamily: mono, color: "#ff6b6b", marginBottom: 14, fontWeight: 600 }}>▼ DECLINING SKILLS</h3>
                        {trendMovers.fallers.length > 0 ? trendMovers.fallers.map((f, i) => (
                          <div key={f.skill} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "8px 0", borderBottom: "1px solid rgba(255,255,255,0.03)", animation: `fadeUp .3s ease ${i * 0.05}s both` }}>
                            <button onClick={() => setSelectedSkill(f.skill)} style={{ background: "none", border: "none", color: "#e4e4e7", cursor: "pointer", fontWeight: 600, fontSize: 14, padding: 0, display: "flex", alignItems: "center", gap: 8 }}>
                              <div style={{ width: 8, height: 8, borderRadius: 2, background: skillColor(f.skill), flexShrink: 0 }} />
                              {f.skill}
                            </button>
                            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                              <span style={{ fontSize: 11, color: "#6b7280", fontFamily: mono }}>{f.current_mentions} jobs</span>
                              <DeltaBadge delta={f.delta_pct} />
                            </div>
                          </div>
                        )) : (
                          <div style={{ padding: "20px 0", textAlign: "center", color: "#4b5563", fontFamily: mono, fontSize: 12 }}>
                            Collecting data... Trends will appear after 2+ scrape cycles.
                          </div>
                        )}
                      </div>
                    </div>

                    {/* All skills with sparklines + deltas */}
                    <div style={{ border: "1px solid rgba(0,240,255,0.08)", borderRadius: 12, padding: isMobile ? 14 : 20, background: "rgba(255,255,255,0.01)" }}>
                      <h3 style={{ fontSize: 13, fontFamily: mono, color: "#00f0ff", marginBottom: 14, fontWeight: 600 }}>📊 ALL SKILLS — TREND OVERVIEW</h3>
                      <p style={{ fontSize: 11, color: "#4b5563", fontFamily: mono, marginBottom: 12 }}>Click any skill to see its full trend chart</p>
                      {isMobile ? (
                        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                          {skillRankings.map((s, i) => {
                            const delta = trendBulk.deltas?.[s.skill];
                            return (
                              <div key={s.skill} onClick={() => setSelectedSkill(s.skill)} style={{ border: "1px solid rgba(0,240,255,0.08)", borderRadius: 10, padding: "10px 14px", background: "rgba(255,255,255,0.01)", cursor: "pointer", animation: `fadeUp .25s ease ${i * 0.02}s both` }}>
                                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                                    <span style={{ fontFamily: mono, color: "#4b5563", fontSize: 11 }}>{String(s.rank).padStart(2, "0")}</span>
                                    <div style={{ width: 8, height: 8, borderRadius: 2, background: s.color, flexShrink: 0 }} />
                                    <span style={{ fontWeight: 600, fontSize: 13 }}>{s.skill}</span>
                                  </div>
                                  <DeltaBadge delta={delta} size="small" />
                                </div>
                                <div style={{ fontSize: 11, fontFamily: mono, color: "#9ca3af", marginTop: 4 }}>{s.jobs.toLocaleString()} jobs • {s.pct}%</div>
                              </div>
                            );
                          })}
                        </div>
                      ) : (
                        <div style={{ borderRadius: 8, overflow: "hidden", border: "1px solid rgba(0,240,255,0.06)" }}>
                          <div style={{ display: "grid", gridTemplateColumns: "45px 1fr 90px 75px 70px 90px", padding: "10px 16px", fontSize: 10, color: "#4b5563", textTransform: "uppercase", fontFamily: mono, borderBottom: "1px solid rgba(0,240,255,0.06)", background: "rgba(0,240,255,0.02)" }}>
                            <span>#</span><span>Skill</span><span style={{ textAlign: "right" }}>Jobs</span><span style={{ textAlign: "right" }}>Share</span><span style={{ textAlign: "center" }}>7d</span><span style={{ textAlign: "center" }}>Trend</span>
                          </div>
                          {skillRankings.map((s, i) => {
                            const sparkData = trendBulk.sparklines?.[s.skill];
                            const delta = trendBulk.deltas?.[s.skill];
                            return (
                              <div key={s.skill} onClick={() => setSelectedSkill(s.skill)} style={{ display: "grid", gridTemplateColumns: "45px 1fr 90px 75px 70px 90px", padding: "11px 16px", borderBottom: "1px solid rgba(255,255,255,0.02)", alignItems: "center", cursor: "pointer", animation: `fadeUp .25s ease ${i * 0.02}s both` }}>
                                <span style={{ fontFamily: mono, color: "#4b5563", fontSize: 12 }}>{String(s.rank).padStart(2, "0")}</span>
                                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                                  <div style={{ width: 8, height: 8, borderRadius: 2, background: s.color, flexShrink: 0 }} />
                                  <span style={{ fontWeight: 600, fontSize: 13, whiteSpace: "nowrap" }}>{s.skill}</span>
                                </div>
                                <span style={{ textAlign: "right", fontFamily: mono, fontSize: 12 }}>{s.jobs.toLocaleString()}</span>
                                <span style={{ textAlign: "right", fontFamily: mono, fontSize: 12 }}>{s.pct}%</span>
                                <div style={{ display: "flex", justifyContent: "center" }}><DeltaBadge delta={delta} size="small" /></div>
                                <div style={{ display: "flex", justifyContent: "center" }}>
                                  <Sparkline data={sparkData && sparkData.length >= 2 ? sparkData : s.trend} color={delta > 0 ? "#00ff88" : delta < 0 ? "#ff4444" : s.color} />
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* ════ LANGUAGES ════ */}
            {tab === "languages" && (
              <div style={{ animation: "fadeUp .3s ease" }}>
                <div style={{ border: "1px solid rgba(0,240,255,0.08)", borderRadius: 12, padding: isMobile ? 14 : 24, background: "rgba(255,255,255,0.01)", marginBottom: 16 }}>
                  <h3 style={{ fontSize: 13, fontFamily: mono, color: "#00f0ff", marginBottom: 20, fontWeight: 600 }}>PROGRAMMING LANGUAGES — DEMAND RANKING</h3>
                  <BarChart
                    isMobile={isMobile}
                    data={skillRankings.filter((s) => s.category === "languages").map((s) => ({ label: s.skill, value: s.jobs, color: s.color }))}
                    maxVal={maxSkillVal} height={280}
                  />
                </div>
                {isMobile ? (
                  /* Mobile: card list instead of table */
                  <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                    {skillRankings.filter((s) => s.category === "languages").map((s, i) => {
                      const dir = s.trend[s.trend.length - 1] >= s.trend[0];
                      return (
                        <div key={s.skill} style={{ border: "1px solid rgba(0,240,255,0.08)", borderRadius: 10, padding: "12px 14px", background: "rgba(255,255,255,0.01)", animation: `fadeUp .3s ease ${i * 0.04}s both` }}>
                          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                              <span style={{ fontFamily: mono, color: "#4b5563", fontSize: 12 }}>{String(s.rank).padStart(2, "0")}</span>
                              <div style={{ width: 8, height: 8, borderRadius: 2, background: s.color, flexShrink: 0 }} />
                              <span style={{ fontWeight: 600, fontSize: 14 }}>{s.skill}</span>
                            </div>
                            <span style={{ fontFamily: mono, color: dir ? "#00ff88" : "#ff4444", fontSize: 12 }}>{dir ? "▲" : "▼"}</span>
                          </div>
                          <div style={{ display: "flex", gap: 16, fontSize: 12, fontFamily: mono, color: "#9ca3af" }}>
                            <span>{s.jobs.toLocaleString()} jobs</span>
                            <span>{s.pct}% share</span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  /* Desktop: full table */
                  <div style={{ border: "1px solid rgba(0,240,255,0.08)", borderRadius: 12, overflow: "hidden", background: "rgba(255,255,255,0.01)" }}>
                    <div style={{ display: "grid", gridTemplateColumns: "50px 1fr 90px 80px 70px 90px", padding: "10px 16px", fontSize: 10, color: "#4b5563", textTransform: "uppercase", fontFamily: mono, borderBottom: "1px solid rgba(0,240,255,0.06)", background: "rgba(0,240,255,0.02)" }}>
                      <span>#</span><span>Language</span><span style={{ textAlign: "right" }}>Jobs</span><span style={{ textAlign: "right" }}>Share</span><span style={{ textAlign: "center" }}>Trend</span><span style={{ textAlign: "right" }}>Direction</span>
                    </div>
                    {skillRankings.filter((s) => s.category === "languages").map((s, i) => {
                      const dir = s.trend[s.trend.length - 1] >= s.trend[0];
                      return (
                        <div key={s.skill} style={{ display: "grid", gridTemplateColumns: "50px 1fr 90px 80px 70px 90px", padding: "12px 16px", borderBottom: "1px solid rgba(255,255,255,0.02)", alignItems: "center", animation: `fadeUp .3s ease ${i * 0.04}s both` }}>
                          <span style={{ fontFamily: mono, color: "#4b5563" }}>{String(s.rank).padStart(2, "0")}</span>
                          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                            <div style={{ width: 8, height: 8, borderRadius: 2, background: s.color, flexShrink: 0 }} />
                            <span style={{ fontWeight: 600, whiteSpace: "nowrap" }}>{s.skill}</span>
                          </div>
                          <span style={{ textAlign: "right", fontFamily: mono }}>{s.jobs.toLocaleString()}</span>
                          <span style={{ textAlign: "right", fontFamily: mono }}>{s.pct}%</span>
                          <div style={{ display: "flex", justifyContent: "center" }}><Sparkline data={s.trend} color={dir ? "#00ff88" : "#ff4444"} /></div>
                          <span style={{ textAlign: "right", fontFamily: mono, color: dir ? "#00ff88" : "#ff4444" }}>{dir ? "▲ Rising" : "▼ Falling"}</span>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            )}

            {/* ════ ALL SKILLS ════ */}
            {tab === "skills" && (
              <div style={{ animation: "fadeUp .3s ease" }}>
                {isMobile ? (
                  /* Mobile: compact card list */
                  <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                    {skillRankings.map((s, i) => (
                      <div key={s.skill} style={{ border: "1px solid rgba(0,240,255,0.08)", borderRadius: 10, padding: "10px 14px", background: "rgba(255,255,255,0.01)", animation: `fadeUp .25s ease ${i * 0.02}s both` }}>
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
                          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                            <span style={{ fontFamily: mono, color: "#4b5563", fontSize: 11 }}>{String(s.rank).padStart(2, "0")}</span>
                            <div style={{ width: 8, height: 8, borderRadius: 2, background: s.color, flexShrink: 0 }} />
                            <span style={{ fontWeight: 600, fontSize: 14 }}>{s.skill}</span>
                          </div>
                          <span style={{ fontSize: 9, padding: "2px 8px", borderRadius: 4, background: "rgba(255,255,255,0.04)", color: "#6b7280", fontFamily: mono }}>{s.category}</span>
                        </div>
                        <div style={{ display: "flex", gap: 16, fontSize: 12, fontFamily: mono, color: "#9ca3af" }}>
                          <span>{s.jobs.toLocaleString()} jobs</span>
                          <span>{s.pct}%</span>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  /* Desktop: full table with trend data */
                  <div style={{ border: "1px solid rgba(0,240,255,0.08)", borderRadius: 12, overflow: "hidden", background: "rgba(255,255,255,0.01)" }}>
                    <div style={{ display: "grid", gridTemplateColumns: "45px 1fr 90px 75px 80px 70px 90px", padding: "10px 16px", fontSize: 10, color: "#4b5563", textTransform: "uppercase", fontFamily: mono, borderBottom: "1px solid rgba(0,240,255,0.06)", background: "rgba(0,240,255,0.02)" }}>
                      <span>#</span><span>Skill</span><span style={{ textAlign: "right" }}>Jobs</span><span style={{ textAlign: "right" }}>Share</span><span style={{ textAlign: "center" }}>Category</span><span style={{ textAlign: "center" }}>7d</span><span style={{ textAlign: "center" }}>Trend</span>
                    </div>
                    {skillRankings.map((s, i) => {
                      const sparkData = trendBulk.sparklines?.[s.skill];
                      const delta = trendBulk.deltas?.[s.skill];
                      return (
                        <div key={s.skill} style={{ display: "grid", gridTemplateColumns: "45px 1fr 90px 75px 80px 70px 90px", padding: "11px 16px", borderBottom: "1px solid rgba(255,255,255,0.02)", alignItems: "center", animation: `fadeUp .25s ease ${i * 0.03}s both`, cursor: "pointer" }} onClick={() => { setSelectedSkill(s.skill); setTab("trends"); }}>
                          <span style={{ fontFamily: mono, color: "#4b5563", fontSize: 12 }}>{String(s.rank).padStart(2, "0")}</span>
                          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                            <div style={{ width: 8, height: 8, borderRadius: 2, background: s.color, flexShrink: 0 }} />
                            <span style={{ fontWeight: 600, fontSize: 13, whiteSpace: "nowrap" }}>{s.skill}</span>
                          </div>
                          <span style={{ textAlign: "right", fontFamily: mono, fontSize: 12 }}>{s.jobs.toLocaleString()}</span>
                          <span style={{ textAlign: "right", fontFamily: mono, fontSize: 12 }}>{s.pct}%</span>
                          <div style={{ display: "flex", justifyContent: "center" }}>
                            <span style={{ fontSize: 9, padding: "2px 8px", borderRadius: 4, background: "rgba(255,255,255,0.04)", color: "#6b7280", fontFamily: mono, whiteSpace: "nowrap" }}>{s.category}</span>
                          </div>
                          <div style={{ display: "flex", justifyContent: "center" }}>
                            <DeltaBadge delta={delta} size="small" />
                          </div>
                          <div style={{ display: "flex", justifyContent: "center" }}>
                            <Sparkline data={sparkData && sparkData.length >= 2 ? sparkData : s.trend} color={delta > 0 ? "#00ff88" : delta < 0 ? "#ff4444" : s.color} />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            )}

            {/* ════ COMPANIES ════ */}
            {tab === "companies" && (
              <div style={{ animation: "fadeUp .3s ease" }}>
                <div style={{ border: "1px solid rgba(0,240,255,0.08)", borderRadius: 12, padding: isMobile ? 14 : 24, background: "rgba(255,255,255,0.01)", marginBottom: 16 }}>
                  <h3 style={{ fontSize: 13, fontFamily: mono, color: "#00f0ff", marginBottom: 20, fontWeight: 600 }}>🏢 TOP COMPANIES BY OPEN ROLES</h3>
                  <BarChart
                    isMobile={isMobile}
                    data={topCompanies.map((c) => ({ label: c.company, value: c.jobs, color: c.color }))}
                    maxVal={maxJobVal} height={260}
                  />
                </div>
                <div className="companies-grid">
                  {topCompanies.map((c, i) => (
                    <div key={c.company} style={{ border: "1px solid rgba(0,240,255,0.08)", borderRadius: 10, padding: isMobile ? 10 : 16, background: "rgba(255,255,255,0.01)", animation: `fadeUp .3s ease ${i * 0.04}s both` }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                        <div style={{ fontWeight: 600, fontSize: isMobile ? 12 : 14, wordBreak: "break-word", minWidth: 0 }}>{c.company}</div>
                        <div style={{ width: 10, height: 10, borderRadius: 3, background: c.color, flexShrink: 0, marginLeft: 6 }} />
                      </div>
                      <div style={{ display: "flex", justifyContent: "space-between", gap: 6 }}>
                        <div>
                          <div style={{ fontSize: 9, color: "#6b7280", fontFamily: mono }}>ROLES</div>
                          <div style={{ fontSize: isMobile ? 16 : 18, fontWeight: 700, color: "#00f0ff", fontFamily: mono }}>{c.jobs}</div>
                        </div>
                        {c.topSkill && (
                          <div style={{ textAlign: "right", minWidth: 0 }}>
                            <div style={{ fontSize: 9, color: "#6b7280", fontFamily: mono }}>TOP</div>
                            <div style={{ fontSize: isMobile ? 11 : 14, fontWeight: 600, color: "#00ff88", fontFamily: mono, wordBreak: "break-word" }}>{c.topSkill}</div>
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* ════ COMBOS ════ */}
            {tab === "combos" && (
              <div style={{ animation: "fadeUp .3s ease" }}>
                <p style={{ fontSize: 12, color: "#6b7280", fontFamily: mono, marginBottom: 16 }}>
                  Skills that appear together in job listings — the most in-demand combinations
                </p>
                {combos.map((c, i) => {
                  const barW = Math.min(100, (c.pct / Math.max(combos[0]?.pct || 1, 1)) * 100);
                  return (
                    <div key={i} className="combo-row" style={{ animation: `fadeUp .3s ease ${i * 0.05}s both` }}>
                      <span style={{ fontFamily: mono, color: "#4b5563", fontSize: 12, width: 24, flexShrink: 0 }}>{String(i + 1).padStart(2, "0")}</span>
                      <span className="combo-label">
                        {c.combo.split(" + ").map((s, j) => (
                          <span key={j}>{j > 0 && <span style={{ color: "#4b5563", margin: "0 4px" }}>+</span>}<span style={{ color: "#00f0ff", fontWeight: 500 }}>{s}</span></span>
                        ))}
                      </span>
                      <div className="combo-bar">
                        <div style={{ width: `${barW}%`, height: "100%", background: "linear-gradient(90deg,#00f0ff44,#00f0ff)", borderRadius: 4, transition: "width 0.8s ease" }} />
                      </div>
                      <span style={{ fontFamily: mono, color: "#9ca3af", fontSize: 12, width: 80, textAlign: "right", flexShrink: 0, whiteSpace: "nowrap" }}>{c.jobs} jobs</span>
                      <span style={{ fontFamily: mono, color: "#00ff88", fontSize: 12, width: 50, textAlign: "right", flexShrink: 0 }}>{c.pct}%</span>
                    </div>
                  );
                })}
              </div>
            )}

            {/* ════ HOT JOBS ════ */}
            {tab === "jobs" && (
              <div style={{ animation: "fadeUp .3s ease" }}>

                {/* ── Search bar ── */}
                <div className="search-bar">
                  <div style={{ flex: 1, position: "relative" }}>
                    <span style={{ position: "absolute", left: 12, top: "50%", transform: "translateY(-50%)", color: "#4b5563", fontSize: 14, pointerEvents: "none" }}>🔍</span>
                    <input
                      className="search-input"
                      type="text"
                      placeholder={isMobile ? "Search jobs, companies, tech…" : "Search by job title, company, or tech (e.g. React, Stripe, ML Engineer)…"}
                      value={jobSearch}
                      onChange={(e) => setJobSearch(e.target.value)}
                      style={{
                        width: "100%", padding: "10px 14px 10px 38px",
                        fontSize: 13, fontFamily: mono,
                        background: "rgba(255,255,255,0.03)",
                        border: "1px solid rgba(0,240,255,0.15)",
                        borderRadius: 8, color: "#e4e4e7",
                        transition: "border-color 0.2s, box-shadow 0.2s",
                      }}
                    />
                  </div>
                  {jobSearch && (
                    <button
                      onClick={() => setJobSearch("")}
                      style={{ padding: "10px 16px", fontSize: 12, fontFamily: mono, borderRadius: 8, border: "1px solid rgba(255,100,100,0.2)", background: "rgba(255,100,100,0.06)", color: "#ff6b6b", cursor: "pointer", flexShrink: 0 }}
                    >
                      ✕ Clear
                    </button>
                  )}
                </div>

                {/* ── Info line ── */}
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 16, flexWrap: "wrap" }}>
                  <PulsingDot color={searchLoading ? "#ffaa00" : "#00ff88"} />
                  <span style={{ fontSize: 12, color: "#6b7280", fontFamily: mono }}>
                    {searchLoading
                      ? "Searching…"
                      : searchResults !== null
                        ? `${searchResults.length} result${searchResults.length !== 1 ? "s" : ""} for "${jobSearch.trim()}"`
                        : `${hotJobs.length} featured jobs from ${hotJobsSources.length} sources`}
                  </span>
                </div>

                {/* ── No results message ── */}
                {searchResults !== null && searchResults.length === 0 && !searchLoading && (
                  <div style={{ padding: "32px 0", textAlign: "center", color: "#4b5563", fontFamily: mono, fontSize: 13 }}>
                    No jobs found for "{jobSearch.trim()}" — try a different title, company, or tech.
                  </div>
                )}

                {/* ── Job grid ── */}
                <div className="jobs-grid">
                  {displayedJobs.map((job, i) => (
                    <a key={job.id || i} href={job.url} target="_blank" rel="noopener noreferrer" style={{
                      border: `1px solid ${job.hot ? "rgba(255,100,100,0.15)" : "rgba(0,240,255,0.08)"}`,
                      borderRadius: 12, padding: isMobile ? 14 : 18, textDecoration: "none", color: "#e4e4e7",
                      background: job.hot ? "rgba(255,100,100,0.03)" : "rgba(255,255,255,0.01)",
                      display: "block", transition: "all 0.2s", animation: `fadeUp .3s ease ${Math.min(i, 10) * 0.04}s both`,
                    }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 8, gap: 8 }}>
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 4, flexWrap: "wrap" }}>
                            {job.hot && <span style={{ fontSize: 9, color: "#ff6b6b", fontFamily: mono, flexShrink: 0 }}>🔥 HOT</span>}
                            {job.source_label && <span style={{ fontSize: 9, color: "#4b5563", fontFamily: mono, flexShrink: 0 }}>{job.source_label}</span>}
                          </div>
                          <div style={{ fontSize: isMobile ? 14 : 15, fontWeight: 600, marginBottom: 3, wordBreak: "break-word" }}>{job.title}</div>
                          <div style={{ fontSize: 12, color: "#6b7280", wordBreak: "break-word" }}>{job.company} • {job.location || "Remote"}</div>
                        </div>
                        <div style={{ textAlign: "right", flexShrink: 0 }}>
                          <div style={{ fontSize: isMobile ? 13 : 14, fontWeight: 600, color: "#00ff88", fontFamily: mono }}>{job.salary}</div>
                          {job.time && <div style={{ fontSize: 10, color: "#4b5563", fontFamily: mono, marginTop: 2 }}>{job.time} ago</div>}
                        </div>
                      </div>
                      <div style={{ display: "flex", gap: 4, flexWrap: "wrap", marginBottom: 10 }}>
                        {(job.skills || []).slice(0, isMobile ? 4 : 5).map((s) => (
                          <span key={s} style={{ fontSize: 10, padding: "3px 8px", borderRadius: 4, background: "rgba(0,240,255,0.06)", color: "#00f0ff", fontFamily: mono }}>{s}</span>
                        ))}
                      </div>
                      <div style={{ fontSize: 10, color: "#00f0ff", fontFamily: mono, opacity: 0.6 }}>Click to apply →</div>
                    </a>
                  ))}
                </div>
              </div>
            )}

            {/* ════ AI INSIGHTS ════ */}
            {tab === "ai" && (
              <div style={{ animation: "fadeUp .3s ease" }}>
                <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 20 }}>
                  <span style={{ fontSize: 20 }}>🧠</span>
                  <div>
                    <div style={{ fontSize: 14, fontWeight: 600 }}>AI-Generated Market Intelligence</div>
                    <div style={{ fontSize: 11, color: "#6b7280", fontFamily: mono }}>
                      Analyzed {totalJobs.toLocaleString()} jobs across {Object.keys(meta.sources || {}).length} sources
                    </div>
                  </div>
                </div>
                <div className="insights-grid">
                  {(analytics?.ai_insights || AI_INSIGHTS).map((ins, i) => {
                    const colors = { hot: "#ff6b6b", trend: "#00ff88", warn: "#ffaa00", money: "#00f0ff", predict: "#8B5CF6", company: "#61DAFB" };
                    const bg = { hot: "rgba(255,100,100,0.04)", trend: "rgba(0,255,136,0.04)", warn: "rgba(255,170,0,0.04)", money: "rgba(0,240,255,0.04)", predict: "rgba(139,92,246,0.04)", company: "rgba(97,218,251,0.04)" };
                    return (
                      <div key={i} style={{ border: `1px solid ${colors[ins.type]}22`, borderRadius: 12, padding: isMobile ? 14 : 20, background: bg[ins.type], animation: `fadeUp .3s ease ${i * 0.08}s both` }}>
                        <div style={{ fontSize: 13, fontWeight: 600, color: colors[ins.type], marginBottom: 8, fontFamily: mono }}>{ins.icon} {ins.title}</div>
                        <div style={{ fontSize: 13, color: "#c9cdd3", lineHeight: 1.7 }}>{ins.text}</div>
                      </div>
                    );
                  })}
                </div>
                <div style={{ marginTop: 20, padding: isMobile ? 12 : 16, border: "1px solid rgba(0,240,255,0.1)", borderRadius: 12, background: "rgba(0,240,255,0.02)" }}>
                  <div style={{ fontSize: 11, fontFamily: mono, color: "#4b5563", marginBottom: 8 }}>📊 LAST SCRAPE</div>
                  {fetchStatusData && (
                    <div style={{ fontSize: 12, color: "#9ca3af", lineHeight: 1.7, wordBreak: "break-word" }}>
                      Status: <span style={{ color: statusColor }}>{fetchStatusData.status}</span> •
                      {" "}{fetchStatusData.jobs_fetched || 0} jobs fetched •
                      {fetchStatusData.next_run_in && ` Next run in ${Math.round(fetchStatusData.next_run_in / 3600)}h`}
                      {meta.scraped_at && ` • Last scraped: ${new Date(meta.scraped_at).toLocaleString()}`}
                    </div>
                  )}
                </div>
              </div>
            )}
          </>
        )}
      </div>

      {/* ── FOOTER ───────────────────────────────────── */}
      <div className="app-footer">
        <span>SkillTree.dev — Real-time tech job market intelligence • Open Source</span>
        <span>Data auto-refreshes every 8 hours • Built by Rommel Abbas</span>
      </div>
    </div>
  );
}
