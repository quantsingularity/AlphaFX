import { useState, FormEvent, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

type Plan = "free" | "pro" | "institutional";

const PLANS: { id: Plan; label: string; price: string; features: string[] }[] =
  [
    {
      id: "free",
      label: "Free",
      price: "$0/mo",
      features: ["5 pairs", "Basic charts", "1 portfolio"],
    },
    {
      id: "pro",
      label: "Pro",
      price: "$49/mo",
      features: ["40+ pairs", "Full analytics", "10 portfolios", "Alerts"],
    },
    {
      id: "institutional",
      label: "Institutional",
      price: "$199/mo",
      features: [
        "Unlimited",
        "API access",
        "Options pricing",
        "Priority support",
      ],
    },
  ];

export default function Register() {
  const { register, isAuthenticated } = useAuth();
  const navigate = useNavigate();

  const [step, setStep] = useState<1 | 2>(1);
  const [plan, setPlan] = useState<Plan>("free");
  const [form, setForm] = useState({
    first_name: "",
    last_name: "",
    username: "",
    email: "",
    password: "",
    confirm: "",
  });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [showPw, setShowPw] = useState(false);

  useEffect(() => {
    if (isAuthenticated) navigate("/dashboard", { replace: true });
  }, [isAuthenticated, navigate]);

  const set =
    (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
      setForm((f) => ({ ...f, [k]: e.target.value }));

  const validateStep1 = () => {
    if (!form.first_name.trim()) return "First name is required.";
    if (!form.username.trim()) return "Username is required.";
    if (!form.email.trim()) return "Email is required.";
    if (!/^[^@]+@[^@]+\.[^@]+$/.test(form.email))
      return "Enter a valid email address.";
    return "";
  };

  const nextStep = () => {
    const err = validateStep1();
    if (err) {
      setError(err);
      return;
    }
    setError("");
    setStep(2);
  };

  const handle = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    if (form.password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }
    if (form.password !== form.confirm) {
      setError("Passwords do not match.");
      return;
    }
    setLoading(true);
    try {
      await register({
        username: form.username.trim(),
        email: form.email.trim(),
        password: form.password,
        first_name: form.first_name.trim(),
        last_name: form.last_name.trim(),
      });
      navigate("/dashboard", { replace: true });
    } catch (err: any) {
      const data = err?.response?.data;
      const msg =
        typeof data === "object"
          ? Object.values(data).flat().join(" ")
          : data?.detail || "Registration failed. Please try again.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#050810] flex">
      <style>{`
        @keyframes fadeUp {
          from { opacity:0; transform:translateY(20px); }
          to   { opacity:1; transform:translateY(0); }
        }
        .auth-card { animation: fadeUp 0.5s ease both; }
        .input-auth {
          width: 100%;
          background: rgba(255,255,255,0.04);
          border: 1px solid rgba(255,255,255,0.1);
          color: #e2e8f0;
          border-radius: 10px;
          padding: 11px 14px;
          font-size: 14px;
          outline: none;
          transition: border-color 0.2s, box-shadow 0.2s;
        }
        .input-auth:focus {
          border-color: rgba(34,197,94,0.5);
          box-shadow: 0 0 0 3px rgba(34,197,94,0.08);
        }
        .input-auth::placeholder { color: #475569; }
        .btn-submit {
          width: 100%;
          background: #16a34a;
          color: white;
          font-weight: 600;
          font-size: 14px;
          padding: 11px;
          border-radius: 10px;
          border: none;
          cursor: pointer;
          transition: background 0.2s, box-shadow 0.2s;
        }
        .btn-submit:hover:not(:disabled) { background:#15803d; box-shadow:0 0 20px rgba(34,197,94,0.3); }
        .btn-submit:disabled { opacity:0.55; cursor:not-allowed; }
        .plan-card {
          border: 1px solid rgba(255,255,255,0.08);
          border-radius: 12px;
          padding: 14px;
          cursor: pointer;
          transition: border-color 0.2s, background 0.2s;
          background: rgba(255,255,255,0.02);
        }
        .plan-card:hover { border-color: rgba(34,197,94,0.3); background: rgba(255,255,255,0.04); }
        .plan-card.active { border-color: rgba(34,197,94,0.6); background: rgba(34,197,94,0.06); }
      `}</style>

      {/* Left branding panel */}
      <div className="hidden lg:flex flex-col justify-between w-[420px] border-r border-white/5 p-12 relative overflow-hidden">
        <div
          style={{
            position: "absolute",
            inset: 0,
            background:
              "radial-gradient(ellipse at 20% 50%, rgba(34,197,94,0.07) 0%, transparent 60%)",
            pointerEvents: "none",
          }}
        />
        <div
          style={{
            position: "absolute",
            inset: 0,
            backgroundImage:
              "linear-gradient(rgba(255,255,255,0.02) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.02) 1px, transparent 1px)",
            backgroundSize: "40px 40px",
            pointerEvents: "none",
          }}
        />

        <div className="relative">
          <Link to="/" className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-brand-500 flex items-center justify-center text-white font-black">
              α
            </div>
            <span className="font-bold text-slate-100 text-xl tracking-tight">
              AlphaFX
            </span>
          </Link>
        </div>

        <div className="relative space-y-5">
          <h2 className="text-2xl font-black text-slate-100">
            Start trading smarter today
          </h2>
          <p className="text-slate-500 text-sm leading-relaxed">
            Free to start. Upgrade when you're ready. Cancel anytime.
          </p>
          <div className="space-y-3 pt-2">
            {[
              "Real-time rates with < 15ms latency",
              "Full technical analysis suite",
              "Portfolio risk management & VaR",
              "Black-Scholes options pricing engine",
            ].map((f) => (
              <div
                key={f}
                className="flex items-center gap-3 text-sm text-slate-400"
              >
                <svg
                  className="w-4 h-4 text-brand-400 shrink-0"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                >
                  <path
                    fillRule="evenodd"
                    d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                    clipRule="evenodd"
                  />
                </svg>
                {f}
              </div>
            ))}
          </div>
        </div>

        <div className="relative text-xs text-slate-700">
          © {new Date().getFullYear()} AlphaFX.
        </div>
      </div>

      {/* Right panel */}
      <div className="flex-1 flex items-center justify-center p-6 overflow-y-auto">
        <div className="auth-card w-full max-w-[440px] space-y-6 py-8">
          {/* Mobile logo */}
          <div className="lg:hidden flex items-center gap-2 mb-2">
            <div className="w-7 h-7 rounded-lg bg-brand-500 flex items-center justify-center text-white font-black text-xs">
              α
            </div>
            <span className="font-bold text-slate-100 tracking-tight">
              AlphaFX
            </span>
          </div>

          {/* Progress */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <h1 className="text-2xl font-bold text-slate-100">
                {step === 1 ? "Create account" : "Set password"}
              </h1>
              <span className="text-xs text-slate-600 font-mono">
                Step {step}/2
              </span>
            </div>
            <div className="h-1 bg-white/5 rounded-full overflow-hidden">
              <div
                className="h-full bg-brand-500 rounded-full transition-all duration-500"
                style={{ width: step === 1 ? "50%" : "100%" }}
              />
            </div>
          </div>

          {step === 1 ? (
            <div className="space-y-4">
              {/* Plan selector */}
              <div>
                <p className="text-xs font-medium text-slate-400 mb-2">
                  Choose plan
                </p>
                <div className="grid grid-cols-3 gap-2">
                  {PLANS.map((p) => (
                    <button
                      key={p.id}
                      type="button"
                      onClick={() => setPlan(p.id)}
                      className={`plan-card text-left ${plan === p.id ? "active" : ""}`}
                    >
                      <p className="text-xs font-semibold text-slate-200">
                        {p.label}
                      </p>
                      <p className="text-[11px] text-brand-400 font-mono mt-0.5">
                        {p.price}
                      </p>
                      <ul className="mt-1.5 space-y-0.5">
                        {p.features.map((f) => (
                          <li key={f} className="text-[10px] text-slate-500">
                            {f}
                          </li>
                        ))}
                      </ul>
                    </button>
                  ))}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1.5">
                    First name
                  </label>
                  <input
                    className="input-auth"
                    placeholder="Jane"
                    value={form.first_name}
                    onChange={set("first_name")}
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1.5">
                    Last name
                  </label>
                  <input
                    className="input-auth"
                    placeholder="Smith"
                    value={form.last_name}
                    onChange={set("last_name")}
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1.5">
                  Username
                </label>
                <input
                  className="input-auth"
                  placeholder="janesmith"
                  value={form.username}
                  onChange={set("username")}
                  autoComplete="username"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1.5">
                  Email address
                </label>
                <input
                  className="input-auth"
                  type="email"
                  placeholder="jane@example.com"
                  value={form.email}
                  onChange={set("email")}
                  autoComplete="email"
                />
              </div>

              {error && (
                <div className="text-xs text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg px-3.5 py-2.5">
                  {error}
                </div>
              )}

              <button type="button" onClick={nextStep} className="btn-submit">
                Continue →
              </button>
            </div>
          ) : (
            <form onSubmit={handle} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1.5">
                  Password
                </label>
                <div className="relative">
                  <input
                    className="input-auth pr-10"
                    type={showPw ? "text" : "password"}
                    placeholder="Min. 8 characters"
                    value={form.password}
                    onChange={set("password")}
                    autoComplete="new-password"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPw(!showPw)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 transition-colors"
                    tabIndex={-1}
                  >
                    <svg
                      className="w-4 h-4"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      {showPw ? (
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21"
                        />
                      ) : (
                        <>
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                          />
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
                          />
                        </>
                      )}
                    </svg>
                  </button>
                </div>

                {/* Strength meter */}
                {form.password && (
                  <div className="mt-2 space-y-1">
                    <div className="flex gap-1">
                      {[1, 2, 3, 4].map((n) => {
                        const score = [
                          /[a-z]/,
                          /[A-Z]/,
                          /[0-9]/,
                          /[^a-zA-Z0-9]/,
                        ].filter((r) => r.test(form.password)).length;
                        return (
                          <div
                            key={n}
                            className={`h-1 flex-1 rounded-full transition-colors ${n <= score ? (score <= 2 ? "bg-red-500" : score === 3 ? "bg-yellow-500" : "bg-brand-500") : "bg-white/8"}`}
                          />
                        );
                      })}
                    </div>
                    <p className="text-[10px] text-slate-600">
                      {(() => {
                        const score = [
                          /[a-z]/,
                          /[A-Z]/,
                          /[0-9]/,
                          /[^a-zA-Z0-9]/,
                        ].filter((r) => r.test(form.password)).length;
                        return ["", "Weak", "Weak", "Good", "Strong"][score];
                      })()}
                    </p>
                  </div>
                )}
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1.5">
                  Confirm password
                </label>
                <input
                  className="input-auth"
                  type={showPw ? "text" : "password"}
                  placeholder="Repeat password"
                  value={form.confirm}
                  onChange={set("confirm")}
                  autoComplete="new-password"
                />
                {form.confirm && form.password !== form.confirm && (
                  <p className="text-[11px] text-red-400 mt-1">
                    Passwords don't match
                  </p>
                )}
              </div>

              {error && (
                <div className="text-xs text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg px-3.5 py-2.5">
                  {error}
                </div>
              )}

              <p className="text-[11px] text-slate-600 leading-relaxed">
                By creating an account you agree to our{" "}
                <a href="#" className="text-slate-400 hover:text-slate-300">
                  Terms of Service
                </a>{" "}
                and{" "}
                <a href="#" className="text-slate-400 hover:text-slate-300">
                  Privacy Policy
                </a>
                .
              </p>

              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => {
                    setStep(1);
                    setError("");
                  }}
                  className="flex-none px-4 py-[11px] rounded-[10px] text-sm font-medium text-slate-400 border border-white/10 hover:border-white/20 hover:bg-white/4 transition-all"
                >
                  ← Back
                </button>
                <button
                  type="submit"
                  disabled={loading}
                  className="btn-submit flex-1"
                >
                  {loading ? (
                    <span className="flex items-center justify-center gap-2">
                      <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin inline-block" />{" "}
                      Creating account…
                    </span>
                  ) : (
                    "Create account"
                  )}
                </button>
              </div>
            </form>
          )}

          <p className="text-center text-sm text-slate-500 pt-1">
            Already have an account?{" "}
            <Link
              to="/login"
              className="text-brand-400 hover:text-brand-300 font-medium transition-colors"
            >
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
