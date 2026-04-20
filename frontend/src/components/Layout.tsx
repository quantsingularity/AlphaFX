import { Outlet, NavLink, useNavigate } from "react-router-dom";
import { useState, Component, ErrorInfo, ReactNode } from "react";
import { useAuth } from "../context/AuthContext";

const NAV = [
  { to: "/dashboard", label: "Dashboard", icon: "📊" },
  { to: "/rates", label: "Live Rates", icon: "💹" },
  { to: "/charts", label: "Charts", icon: "📈" },
  { to: "/portfolio", label: "Portfolio", icon: "💼" },
  { to: "/options", label: "FX Options", icon: "⚙️" },
  { to: "/carry", label: "Carry Trade", icon: "💰" },
  { to: "/calculator", label: "Calculator", icon: "🧮" },
  { to: "/alerts", label: "Alerts", icon: "🔔" },
  { to: "/history", label: "History", icon: "📋" },
];

// ── Error boundary ────────────────────────────────────────────────
interface EBState {
  hasError: boolean;
  message: string;
}
class PageErrorBoundary extends Component<{ children: ReactNode }, EBState> {
  state: EBState = { hasError: false, message: "" };
  static getDerivedStateFromError(err: Error): EBState {
    return { hasError: true, message: err.message };
  }
  componentDidCatch(_err: Error, _info: ErrorInfo) {}
  render() {
    if (this.state.hasError) {
      return (
        <div className="flex flex-col items-center justify-center h-full min-h-[60vh] gap-4 text-center px-6">
          <span className="text-4xl">⚠️</span>
          <p className="text-slate-300 font-medium">
            Something went wrong on this page.
          </p>
          <p className="text-xs text-slate-500 font-mono max-w-sm break-words">
            {this.state.message}
          </p>
          <button
            className="btn-secondary text-sm"
            onClick={() => this.setState({ hasError: false, message: "" })}
          >
            Try again
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

// ── Layout ────────────────────────────────────────────────────────
export default function Layout() {
  const [open, setOpen] = useState(true);
  const [showUserMenu, setShowUserMenu] = useState(false);
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const initials =
    [user?.first_name?.[0], user?.last_name?.[0]]
      .filter(Boolean)
      .join("")
      .toUpperCase() ||
    user?.username?.[0]?.toUpperCase() ||
    "?";

  const handleLogout = () => {
    logout();
    navigate("/", { replace: true });
  };

  return (
    <div className="flex h-screen bg-gray-950 text-gray-100">
      {/* ── Sidebar ── */}
      <aside
        className={`${open ? "w-56" : "w-14"} transition-all duration-200 bg-gray-900 border-r border-gray-800 flex flex-col`}
      >
        {/* Logo */}
        <div className="flex items-center justify-between px-4 py-4 border-b border-gray-800">
          {open && (
            <div className="flex items-center gap-2">
              <div className="w-6 h-6 rounded-md bg-brand-500 flex items-center justify-center text-white font-black text-xs">
                α
              </div>
              <span className="font-bold text-slate-100 tracking-tight">
                AlphaFX
              </span>
            </div>
          )}
          <button
            onClick={() => setOpen(!open)}
            className="text-gray-400 hover:text-white transition-colors"
          >
            {open ? "◀" : "▶"}
          </button>
        </div>

        {/* Nav links */}
        <nav className="flex-1 py-4 space-y-0.5 overflow-y-auto">
          {NAV.map(({ to, label, icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `flex items-center gap-3 px-4 py-2.5 text-sm transition-colors rounded-l-none rounded-r-lg mx-2 ` +
                (isActive
                  ? "bg-brand-900/40 text-brand-400 border-l-2 border-brand-400"
                  : "text-gray-400 hover:text-gray-100 hover:bg-gray-800")
              }
            >
              <span className="text-base shrink-0">{icon}</span>
              {open && <span className="truncate">{label}</span>}
            </NavLink>
          ))}
        </nav>

        {/* User section */}
        <div className="border-t border-gray-800 p-3 relative">
          <button
            onClick={() => setShowUserMenu(!showUserMenu)}
            className={`w-full flex items-center gap-3 rounded-lg p-2 hover:bg-gray-800 transition-colors ${showUserMenu ? "bg-gray-800" : ""}`}
          >
            {/* Avatar */}
            <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-brand-600 to-brand-800 flex items-center justify-center text-white text-xs font-bold shrink-0">
              {initials}
            </div>
            {open && (
              <div className="flex-1 text-left min-w-0">
                <p className="text-xs font-medium text-slate-300 truncate">
                  {[user?.first_name, user?.last_name]
                    .filter(Boolean)
                    .join(" ") || user?.username}
                </p>
                <p className="text-[10px] text-slate-600 truncate font-mono">
                  @{user?.username}
                </p>
              </div>
            )}
            {open && (
              <svg
                className={`w-3.5 h-3.5 text-slate-500 shrink-0 transition-transform ${showUserMenu ? "rotate-180" : ""}`}
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M19 9l-7 7-7-7"
                />
              </svg>
            )}
          </button>

          {/* User dropdown */}
          {showUserMenu && (
            <div
              className={`absolute bottom-full ${open ? "left-2 right-2" : "left-14 w-44"} mb-1 bg-gray-800 border border-gray-700 rounded-xl shadow-2xl overflow-hidden z-50`}
            >
              <div className="p-3 border-b border-gray-700">
                <p className="text-xs font-medium text-slate-300 truncate">
                  {[user?.first_name, user?.last_name]
                    .filter(Boolean)
                    .join(" ") || user?.username}
                </p>
                <p className="text-[10px] text-slate-500 truncate mt-0.5">
                  {user?.email}
                </p>
                <span
                  className={`inline-block mt-1.5 text-[10px] font-semibold px-1.5 py-0.5 rounded-full border capitalize ${
                    user?.plan === "pro"
                      ? "text-brand-400 bg-brand-900/30 border-brand-700/40"
                      : user?.plan === "institutional"
                        ? "text-amber-400 bg-amber-900/20 border-amber-700/40"
                        : "text-slate-400 bg-slate-700/40 border-slate-600/40"
                  }`}
                >
                  {user?.plan ?? "free"}
                </span>
              </div>
              <div className="p-1.5 space-y-0.5">
                <button
                  onClick={() => {
                    setShowUserMenu(false);
                    navigate("/profile");
                  }}
                  className="w-full flex items-center gap-2.5 px-3 py-2 text-xs text-slate-300 hover:bg-gray-700 rounded-lg transition-colors text-left"
                >
                  <svg
                    className="w-3.5 h-3.5 text-slate-500"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"
                    />
                  </svg>
                  Profile & Settings
                </button>
                <button
                  onClick={handleLogout}
                  className="w-full flex items-center gap-2.5 px-3 py-2 text-xs text-red-400 hover:bg-red-900/20 rounded-lg transition-colors text-left"
                >
                  <svg
                    className="w-3.5 h-3.5"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"
                    />
                  </svg>
                  Sign out
                </button>
              </div>
            </div>
          )}
        </div>
      </aside>

      {/* ── Main content ── */}
      <main className="flex-1 overflow-auto">
        <PageErrorBoundary>
          <Outlet />
        </PageErrorBoundary>
      </main>
    </div>
  );
}
