import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

/* ── Animated ticker tape ───────────────────────────────────────── */
const TICKER_ITEMS = [
  { pair: "EUR/USD", val: "1.08423", chg: "+0.12%", up: true },
  { pair: "GBP/USD", val: "1.27618", chg: "-0.08%", up: false },
  { pair: "USD/JPY", val: "149.872", chg: "+0.34%", up: true },
  { pair: "AUD/USD", val: "0.65231", chg: "-0.21%", up: false },
  { pair: "USD/CAD", val: "1.36054", chg: "+0.05%", up: true },
  { pair: "EUR/GBP", val: "0.84991", chg: "+0.19%", up: true },
  { pair: "USD/CHF", val: "0.90134", chg: "-0.11%", up: false },
  { pair: "NZD/USD", val: "0.60872", chg: "+0.07%", up: true },
];

function Ticker() {
  const items = [...TICKER_ITEMS, ...TICKER_ITEMS];
  return (
    <div className="relative overflow-hidden border-y border-white/5 bg-black/30 backdrop-blur-sm py-2.5">
      <div className="ticker-track flex gap-10 whitespace-nowrap">
        {items.map((item, i) => (
          <span
            key={i}
            className="inline-flex items-center gap-2.5 text-xs font-mono"
          >
            <span className="text-slate-400 tracking-wider">{item.pair}</span>
            <span className="text-slate-200 font-semibold">{item.val}</span>
            <span className={item.up ? "text-emerald-400" : "text-red-400"}>
              {item.chg}
            </span>
            <span className="text-slate-700">•</span>
          </span>
        ))}
      </div>
    </div>
  );
}

/* ── Floating card component ────────────────────────────────────── */
function FloatCard({
  title,
  value,
  sub,
  accent,
  delay,
}: {
  title: string;
  value: string;
  sub: string;
  accent: string;
  delay: string;
}) {
  return (
    <div
      className="glass-card p-4 rounded-xl min-w-[160px] float-anim"
      style={{ animationDelay: delay }}
    >
      <p className="text-[10px] text-slate-500 uppercase tracking-widest mb-1">
        {title}
      </p>
      <p className={`text-xl font-mono font-bold ${accent}`}>{value}</p>
      <p className="text-[11px] text-slate-500 mt-0.5">{sub}</p>
    </div>
  );
}

/* ── Feature card ───────────────────────────────────────────────── */
function FeatureCard({
  icon,
  title,
  desc,
}: {
  icon: string;
  title: string;
  desc: string;
}) {
  return (
    <div className="group relative rounded-2xl border border-white/5 bg-white/2 p-6 hover:border-brand-500/30 hover:bg-white/4 transition-all duration-300">
      <div className="w-10 h-10 rounded-xl bg-brand-500/10 border border-brand-500/20 flex items-center justify-center text-xl mb-4 group-hover:bg-brand-500/20 transition-colors">
        {icon}
      </div>
      <h3 className="font-semibold text-slate-200 mb-2 text-sm tracking-wide">
        {title}
      </h3>
      <p className="text-xs text-slate-500 leading-relaxed">{desc}</p>
    </div>
  );
}

/* ── Stat item ──────────────────────────────────────────────────── */
function Stat({ value, label }: { value: string; label: string }) {
  return (
    <div className="text-center">
      <div className="text-3xl font-bold text-slate-100 font-mono tabular-nums">
        {value}
      </div>
      <div className="text-xs text-slate-500 mt-1 uppercase tracking-widest">
        {label}
      </div>
    </div>
  );
}

/* ── Main component ─────────────────────────────────────────────── */
export default function Home() {
  const { isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [scrolled, setScrolled] = useState(false);

  // Redirect if already logged in
  useEffect(() => {
    if (isAuthenticated) navigate("/dashboard", { replace: true });
  }, [isAuthenticated, navigate]);

  // Subtle scroll-aware navbar
  useEffect(() => {
    const handler = () => setScrolled(window.scrollY > 20);
    window.addEventListener("scroll", handler);
    return () => window.removeEventListener("scroll", handler);
  }, []);

  // Canvas grid background
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d")!;
    let raf = 0;

    const draw = () => {
      canvas.width = canvas.offsetWidth;
      canvas.height = canvas.offsetHeight;
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      const size = 40;
      ctx.strokeStyle = "rgba(255,255,255,0.025)";
      ctx.lineWidth = 1;
      for (let x = 0; x < canvas.width; x += size) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, canvas.height);
        ctx.stroke();
      }
      for (let y = 0; y < canvas.height; y += size) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(canvas.width, y);
        ctx.stroke();
      }

      // Accent diagonal gradient line
      const grd = ctx.createLinearGradient(
        0,
        canvas.height * 0.3,
        canvas.width * 0.6,
        canvas.height * 0.7,
      );
      grd.addColorStop(0, "rgba(34,197,94,0)");
      grd.addColorStop(0.4, "rgba(34,197,94,0.06)");
      grd.addColorStop(1, "rgba(34,197,94,0)");
      ctx.fillStyle = grd;
      ctx.fillRect(0, 0, canvas.width, canvas.height);
    };

    draw();
    const ro = new ResizeObserver(draw);
    ro.observe(canvas);
    return () => {
      cancelAnimationFrame(raf);
      ro.disconnect();
    };
  }, []);

  return (
    <div className="home-root min-h-screen bg-[#050810] text-slate-100 overflow-x-hidden">
      <style>{`
        @keyframes ticker { from { transform: translateX(0); } to { transform: translateX(-50%); } }
        .ticker-track { animation: ticker 28s linear infinite; }
        @keyframes float {
          0%, 100% { transform: translateY(0px); }
          50%       { transform: translateY(-8px); }
        }
        .float-anim { animation: float 4s ease-in-out infinite; }
        .glass-card {
          background: rgba(255,255,255,0.04);
          border: 1px solid rgba(255,255,255,0.08);
          backdrop-filter: blur(12px);
        }
        @keyframes fadeUp {
          from { opacity: 0; transform: translateY(24px); }
          to   { opacity: 1; transform: translateY(0); }
        }
        .fade-up { animation: fadeUp 0.7s ease both; }
        .fade-up-1 { animation-delay: 0.1s; }
        .fade-up-2 { animation-delay: 0.25s; }
        .fade-up-3 { animation-delay: 0.4s; }
        .fade-up-4 { animation-delay: 0.55s; }
        .glow-brand { text-shadow: 0 0 40px rgba(34,197,94,0.4); }
        .btn-glow:hover { box-shadow: 0 0 24px rgba(34,197,94,0.35); }
      `}</style>

      {/* ── Canvas grid ── */}
      <canvas
        ref={canvasRef}
        className="fixed inset-0 w-full h-full pointer-events-none"
        style={{ zIndex: 0 }}
      />

      {/* ── Radial glow orbs ── */}
      <div className="fixed inset-0 pointer-events-none" style={{ zIndex: 0 }}>
        <div
          style={{
            position: "absolute",
            top: "-10%",
            left: "30%",
            width: 600,
            height: 600,
            background:
              "radial-gradient(circle, rgba(34,197,94,0.07) 0%, transparent 70%)",
            borderRadius: "50%",
          }}
        />
        <div
          style={{
            position: "absolute",
            bottom: "-5%",
            right: "20%",
            width: 400,
            height: 400,
            background:
              "radial-gradient(circle, rgba(16,185,129,0.05) 0%, transparent 70%)",
            borderRadius: "50%",
          }}
        />
      </div>

      <div className="relative" style={{ zIndex: 1 }}>
        {/* ── Navbar ── */}
        <nav
          className="sticky top-0 z-50 transition-all duration-300"
          style={{
            background: scrolled ? "rgba(5,8,16,0.9)" : "transparent",
            backdropFilter: scrolled ? "blur(16px)" : "none",
            borderBottom: scrolled
              ? "1px solid rgba(255,255,255,0.06)"
              : "none",
          }}
        >
          <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="w-7 h-7 rounded-lg bg-brand-500 flex items-center justify-center text-white font-black text-xs">
                α
              </div>
              <span className="font-bold text-slate-100 tracking-tight text-lg">
                AlphaFX
              </span>
            </div>
            <div className="hidden md:flex items-center gap-8 text-sm text-slate-400">
              <a
                href="#features"
                className="hover:text-slate-200 transition-colors"
              >
                Features
              </a>
              <a
                href="#stats"
                className="hover:text-slate-200 transition-colors"
              >
                Platform
              </a>
              <a
                href="#pricing"
                className="hover:text-slate-200 transition-colors"
              >
                Pricing
              </a>
            </div>
            <div className="flex items-center gap-3">
              <Link
                to="/login"
                className="text-sm text-slate-400 hover:text-slate-200 transition-colors px-3 py-1.5"
              >
                Sign in
              </Link>
              <Link
                to="/register"
                className="btn-glow text-sm bg-brand-600 hover:bg-brand-500 text-white font-medium px-4 py-1.5 rounded-lg transition-all duration-200"
              >
                Get started
              </Link>
            </div>
          </div>
        </nav>

        {/* ── Ticker ── */}
        <Ticker />

        {/* ── Hero ── */}
        <section className="max-w-7xl mx-auto px-6 pt-24 pb-20">
          <div className="grid lg:grid-cols-2 gap-16 items-center">
            {/* Left copy */}
            <div>
              <div className="fade-up fade-up-1 inline-flex items-center gap-2 text-xs text-brand-400 bg-brand-500/10 border border-brand-500/20 rounded-full px-3.5 py-1.5 mb-6 font-mono tracking-wider uppercase">
                <span className="w-1.5 h-1.5 rounded-full bg-brand-400 animate-pulse inline-block" />
                Institutional-grade FX Intelligence
              </div>

              <h1 className="fade-up fade-up-2 text-5xl lg:text-6xl font-black leading-[1.05] tracking-tight text-slate-100 mb-6">
                Trade FX with
                <br />
                <span className="glow-brand text-brand-400">institutional</span>
                <br />
                precision
              </h1>

              <p className="fade-up fade-up-3 text-slate-400 text-lg leading-relaxed mb-10 max-w-lg">
                Real-time rates, options pricing, portfolio analytics, and
                AI-powered signals — everything a professional FX trader needs,
                unified in one platform.
              </p>

              <div className="fade-up fade-up-4 flex flex-wrap gap-3">
                <Link
                  to="/register"
                  className="btn-glow inline-flex items-center gap-2 bg-brand-600 hover:bg-brand-500 text-white font-semibold px-6 py-3 rounded-xl transition-all duration-200 text-sm"
                >
                  Start free trial
                  <svg
                    className="w-4 h-4"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M17 8l4 4m0 0l-4 4m4-4H3"
                    />
                  </svg>
                </Link>
                <Link
                  to="/login"
                  className="inline-flex items-center gap-2 text-slate-300 border border-white/10 hover:border-white/20 hover:bg-white/4 font-medium px-6 py-3 rounded-xl transition-all duration-200 text-sm"
                >
                  Sign in
                </Link>
              </div>

              <div className="fade-up fade-up-4 flex items-center gap-5 mt-8 text-xs text-slate-600">
                {[
                  "No credit card required",
                  "Cancel anytime",
                  "SOC 2 Type II",
                ].map((t) => (
                  <span key={t} className="flex items-center gap-1.5">
                    <svg
                      className="w-3.5 h-3.5 text-brand-500"
                      fill="currentColor"
                      viewBox="0 0 20 20"
                    >
                      <path
                        fillRule="evenodd"
                        d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                        clipRule="evenodd"
                      />
                    </svg>
                    {t}
                  </span>
                ))}
              </div>
            </div>

            {/* Right: floating cards */}
            <div className="relative hidden lg:block h-[420px]">
              <div className="absolute top-6 left-4">
                <FloatCard
                  title="EUR / USD"
                  value="1.08423"
                  sub="↑ +0.12% today"
                  accent="text-emerald-400"
                  delay="0s"
                />
              </div>
              <div className="absolute top-2 right-8">
                <FloatCard
                  title="Portfolio P&L"
                  value="+$4,281"
                  sub="↑ +2.34% MTD"
                  accent="text-emerald-400"
                  delay="0.8s"
                />
              </div>
              <div className="absolute top-44 left-16">
                <FloatCard
                  title="USD / JPY"
                  value="149.872"
                  sub="↓ -0.08% today"
                  accent="text-red-400"
                  delay="1.2s"
                />
              </div>
              <div className="absolute top-52 right-4">
                <FloatCard
                  title="Open Positions"
                  value="7"
                  sub="3 long · 4 short"
                  accent="text-slate-200"
                  delay="0.4s"
                />
              </div>
              <div className="absolute bottom-8 left-8">
                <FloatCard
                  title="Signals Today"
                  value="12"
                  sub="8 bullish · 4 bearish"
                  accent="text-brand-400"
                  delay="1.6s"
                />
              </div>
              <div className="absolute bottom-4 right-16">
                <FloatCard
                  title="GBP / JPY"
                  value="191.543"
                  sub="↑ +0.29% today"
                  accent="text-emerald-400"
                  delay="2.0s"
                />
              </div>

              {/* Center connecting lines decoration */}
              <svg
                className="absolute inset-0 w-full h-full pointer-events-none opacity-10"
                viewBox="0 0 400 420"
              >
                <line
                  x1="80"
                  y1="80"
                  x2="320"
                  y2="60"
                  stroke="#22c55e"
                  strokeWidth="0.5"
                  strokeDasharray="4 4"
                />
                <line
                  x1="80"
                  y1="80"
                  x2="120"
                  y2="220"
                  stroke="#22c55e"
                  strokeWidth="0.5"
                  strokeDasharray="4 4"
                />
                <line
                  x1="320"
                  y1="60"
                  x2="340"
                  y2="280"
                  stroke="#22c55e"
                  strokeWidth="0.5"
                  strokeDasharray="4 4"
                />
                <line
                  x1="120"
                  y1="220"
                  x2="340"
                  y2="280"
                  stroke="#22c55e"
                  strokeWidth="0.5"
                  strokeDasharray="4 4"
                />
                <line
                  x1="120"
                  y1="220"
                  x2="80"
                  y2="360"
                  stroke="#22c55e"
                  strokeWidth="0.5"
                  strokeDasharray="4 4"
                />
                <line
                  x1="340"
                  y1="280"
                  x2="260"
                  y2="380"
                  stroke="#22c55e"
                  strokeWidth="0.5"
                  strokeDasharray="4 4"
                />
              </svg>
            </div>
          </div>
        </section>

        {/* ── Stats ── */}
        <section
          id="stats"
          className="border-y border-white/5 bg-white/2 py-14"
        >
          <div className="max-w-7xl mx-auto px-6">
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-8">
              <Stat value="$2.4B+" label="Daily volume tracked" />
              <Stat value="40+" label="Currency pairs" />
              <Stat value="99.9%" label="Uptime SLA" />
              <Stat value="< 15ms" label="Quote latency" />
            </div>
          </div>
        </section>

        {/* ── Features ── */}
        <section id="features" className="max-w-7xl mx-auto px-6 py-24">
          <div className="text-center mb-14">
            <p className="text-xs text-brand-400 font-mono tracking-widest uppercase mb-3">
              Platform capabilities
            </p>
            <h2 className="text-3xl font-black text-slate-100">
              Everything you need to trade FX
            </h2>
            <p className="text-slate-500 mt-3 text-sm max-w-lg mx-auto">
              Built for quants, traders, and risk managers who demand
              institutional-quality tools.
            </p>
          </div>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {[
              {
                icon: "💹",
                title: "Live Rates & Quotes",
                desc: "Real-time spot, forward, and cross-rate quotes across 40+ pairs with millisecond latency.",
              },
              {
                icon: "📊",
                title: "Technical Analysis",
                desc: "RSI, MACD, Bollinger Bands, Fibonacci, support/resistance levels and more — all calculated server-side.",
              },
              {
                icon: "💼",
                title: "Portfolio Management",
                desc: "Track positions, P&L, VaR, and run scenario analysis across multiple portfolios simultaneously.",
              },
              {
                icon: "⚙️",
                title: "FX Options Pricing",
                desc: "Black-Scholes and SABR model option pricing with full Greeks: delta, gamma, vega, theta, rho.",
              },
              {
                icon: "💰",
                title: "Carry Trade Analytics",
                desc: "Identify and evaluate carry trade opportunities with risk-adjusted return metrics and forward curves.",
              },
              {
                icon: "🔔",
                title: "Smart Price Alerts",
                desc: "Set conditional alerts with live WebSocket delivery. Never miss a breakout or target level again.",
              },
              {
                icon: "🧮",
                title: "Risk Calculators",
                desc: "Position sizing, risk-reward analysis, pip value, and margin requirements at your fingertips.",
              },
              {
                icon: "📈",
                title: "Charts & Correlation",
                desc: "Interactive price charts with overlay indicators and cross-pair correlation heatmaps.",
              },
              {
                icon: "📋",
                title: "Trade History & Reporting",
                desc: "Full audit trail with P&L attribution, win-rate statistics, and exportable reports.",
              },
            ].map((f) => (
              <FeatureCard key={f.title} {...f} />
            ))}
          </div>
        </section>

        {/* ── CTA ── */}
        <section id="pricing" className="max-w-7xl mx-auto px-6 py-20">
          <div className="relative rounded-3xl border border-brand-500/20 bg-gradient-to-br from-brand-500/5 via-transparent to-transparent p-12 text-center overflow-hidden">
            <div
              style={{
                position: "absolute",
                inset: 0,
                background:
                  "radial-gradient(ellipse at 50% 0%, rgba(34,197,94,0.08) 0%, transparent 60%)",
                pointerEvents: "none",
              }}
            />
            <p className="text-xs text-brand-400 font-mono tracking-widest uppercase mb-4">
              Get started today
            </p>
            <h2 className="text-4xl font-black text-slate-100 mb-4">
              Trade smarter, not harder
            </h2>
            <p className="text-slate-400 mb-8 max-w-md mx-auto text-sm">
              Join professional FX traders already using AlphaFX. Free tier
              available — no credit card required.
            </p>
            <div className="flex justify-center gap-3 flex-wrap">
              <Link
                to="/register"
                className="btn-glow inline-flex items-center gap-2 bg-brand-600 hover:bg-brand-500 text-white font-semibold px-8 py-3.5 rounded-xl transition-all duration-200"
              >
                Create free account
                <svg
                  className="w-4 h-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M17 8l4 4m0 0l-4 4m4-4H3"
                  />
                </svg>
              </Link>
              <Link
                to="/login"
                className="inline-flex items-center gap-2 text-slate-300 border border-white/10 hover:border-white/20 hover:bg-white/4 font-medium px-8 py-3.5 rounded-xl transition-all duration-200"
              >
                Sign in
              </Link>
            </div>
          </div>
        </section>

        {/* ── Footer ── */}
        <footer className="border-t border-white/5 py-8">
          <div className="max-w-7xl mx-auto px-6 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-slate-600">
            <div className="flex items-center gap-2">
              <div className="w-5 h-5 rounded bg-brand-500 flex items-center justify-center text-white font-black text-[10px]">
                α
              </div>
              <span className="font-semibold text-slate-500">AlphaFX</span>
              <span>© {new Date().getFullYear()}</span>
            </div>
            <div className="flex gap-6">
              {["Privacy", "Terms", "Docs", "Support"].map((l) => (
                <a
                  key={l}
                  href="#"
                  className="hover:text-slate-400 transition-colors"
                >
                  {l}
                </a>
              ))}
            </div>
          </div>
        </footer>
      </div>
    </div>
  );
}
