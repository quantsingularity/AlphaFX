import { Outlet, NavLink } from "react-router-dom";
import { useState } from "react";

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

export default function Layout() {
  const [open, setOpen] = useState(true);

  return (
    <div className="flex h-screen bg-gray-950 text-gray-100">
      {/* Sidebar */}
      <aside
        className={`${open ? "w-56" : "w-14"} transition-all duration-200 bg-gray-900 border-r border-gray-800 flex flex-col`}
      >
        <div className="flex items-center justify-between px-4 py-4 border-b border-gray-800">
          {open && (
            <span className="font-bold text-cyan-400 text-lg">AlphaFX</span>
          )}
          <button
            onClick={() => setOpen(!open)}
            className="text-gray-400 hover:text-white"
          >
            {open ? "◀" : "▶"}
          </button>
        </div>
        <nav className="flex-1 py-4 space-y-1">
          {NAV.map(({ to, label, icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `flex items-center gap-3 px-4 py-2.5 text-sm transition-colors rounded-l-none rounded-r-lg mx-2 ` +
                (isActive
                  ? "bg-cyan-900/50 text-cyan-400 border-l-2 border-cyan-400"
                  : "text-gray-400 hover:text-gray-100 hover:bg-gray-800")
              }
            >
              <span className="text-base">{icon}</span>
              {open && <span>{label}</span>}
            </NavLink>
          ))}
        </nav>
        {open && (
          <div className="px-4 py-3 border-t border-gray-800 text-xs text-gray-600">
            AlphaFX v2.0 • Django
          </div>
        )}
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  );
}
