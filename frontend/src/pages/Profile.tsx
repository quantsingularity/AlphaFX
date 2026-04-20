import { useState, FormEvent } from "react";
import { useAuth } from "../context/AuthContext";

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="card space-y-5">
      <h2 className="text-sm font-semibold text-slate-200 uppercase tracking-wider border-b border-surface-600 pb-3">
        {title}
      </h2>
      {children}
    </div>
  );
}

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 items-start">
      <label className="text-xs text-slate-500 pt-2.5 uppercase tracking-wide font-medium">
        {label}
      </label>
      <div className="sm:col-span-2">{children}</div>
    </div>
  );
}

const PLAN_COLORS: Record<string, string> = {
  free: "text-slate-400  bg-slate-700/40  border-slate-600/40",
  pro: "text-brand-400  bg-brand-900/30  border-brand-700/40",
  institutional: "text-amber-400  bg-amber-900/20  border-amber-700/40",
};

export default function Profile() {
  const { user, updateProfile, changePassword, logout } = useAuth();

  const [profileForm, setProfileForm] = useState({
    first_name: user?.first_name ?? "",
    last_name: user?.last_name ?? "",
    email: user?.email ?? "",
  });
  const [profileMsg, setProfileMsg] = useState("");
  const [profileErr, setProfileErr] = useState("");
  const [savingProf, setSavingProf] = useState(false);

  const [pwForm, setPwForm] = useState({
    old_password: "",
    new_password: "",
    confirm: "",
  });
  const [pwMsg, setPwMsg] = useState("");
  const [pwErr, setPwErr] = useState("");
  const [savingPw, setSavingPw] = useState(false);
  const [showPw, setShowPw] = useState(false);

  const [confirmLogout, setConfirmLogout] = useState(false);

  const handleProfile = async (e: FormEvent) => {
    e.preventDefault();
    setProfileErr("");
    setProfileMsg("");
    if (!profileForm.email.trim()) {
      setProfileErr("Email is required.");
      return;
    }
    setSavingProf(true);
    try {
      await updateProfile(profileForm);
      setProfileMsg("Profile updated successfully.");
    } catch (err: any) {
      setProfileErr(err?.response?.data?.detail || "Failed to update profile.");
    } finally {
      setSavingProf(false);
    }
  };

  const handlePw = async (e: FormEvent) => {
    e.preventDefault();
    setPwErr("");
    setPwMsg("");
    if (pwForm.new_password.length < 8) {
      setPwErr("New password must be at least 8 characters.");
      return;
    }
    if (pwForm.new_password !== pwForm.confirm) {
      setPwErr("Passwords don't match.");
      return;
    }
    setSavingPw(true);
    try {
      await changePassword(pwForm.old_password, pwForm.new_password);
      setPwMsg("Password changed successfully.");
      setPwForm({ old_password: "", new_password: "", confirm: "" });
    } catch (err: any) {
      setPwErr(err?.response?.data?.detail || "Failed to change password.");
    } finally {
      setSavingPw(false);
    }
  };

  const initials =
    [user?.first_name?.[0], user?.last_name?.[0]]
      .filter(Boolean)
      .join("")
      .toUpperCase() ||
    user?.username?.[0]?.toUpperCase() ||
    "?";
  const joinDate = user?.date_joined
    ? new Date(user.date_joined).toLocaleDateString("en-US", {
        month: "long",
        year: "numeric",
      })
    : "—";

  return (
    <div className="p-6 space-y-6 max-w-3xl">
      {/* Header */}
      <div>
        <h1 className="text-xl font-semibold text-slate-100">
          Profile & Settings
        </h1>
        <p className="text-sm text-slate-500 mt-0.5">
          Manage your account details and preferences
        </p>
      </div>

      {/* Identity card */}
      <div className="card flex items-center gap-5">
        <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-brand-600 to-brand-800 flex items-center justify-center text-2xl font-bold text-white shrink-0 shadow-lg">
          {initials}
        </div>
        <div className="min-w-0">
          <p className="font-semibold text-slate-100 text-lg leading-tight">
            {[user?.first_name, user?.last_name].filter(Boolean).join(" ") ||
              user?.username}
          </p>
          <p className="text-sm text-slate-500 font-mono mt-0.5">
            @{user?.username}
          </p>
          <div className="flex items-center gap-2 mt-2">
            <span
              className={`text-xs font-semibold px-2.5 py-0.5 rounded-full border capitalize ${PLAN_COLORS[user?.plan ?? "free"]}`}
            >
              {user?.plan ?? "free"}
            </span>
            <span className="text-xs text-slate-600">
              Member since {joinDate}
            </span>
          </div>
        </div>
        <div className="ml-auto hidden sm:block">
          <button
            onClick={() => setConfirmLogout(true)}
            className="btn-secondary text-xs text-red-400 hover:text-red-300 border border-red-900/40 hover:border-red-800/60 bg-red-900/10 hover:bg-red-900/20 transition-colors"
          >
            Sign out
          </button>
        </div>
      </div>

      {/* Profile info */}
      <Section title="Personal information">
        <form onSubmit={handleProfile} className="space-y-4">
          <Field label="First name">
            <input
              className="input"
              value={profileForm.first_name}
              onChange={(e) =>
                setProfileForm((f) => ({ ...f, first_name: e.target.value }))
              }
            />
          </Field>
          <Field label="Last name">
            <input
              className="input"
              value={profileForm.last_name}
              onChange={(e) =>
                setProfileForm((f) => ({ ...f, last_name: e.target.value }))
              }
            />
          </Field>
          <Field label="Username">
            <input
              className="input bg-surface-900/50 cursor-not-allowed text-slate-500"
              value={user?.username ?? ""}
              readOnly
            />
            <p className="text-xs text-slate-600 mt-1">
              Username cannot be changed.
            </p>
          </Field>
          <Field label="Email">
            <input
              className="input"
              type="email"
              value={profileForm.email}
              onChange={(e) =>
                setProfileForm((f) => ({ ...f, email: e.target.value }))
              }
            />
          </Field>

          {profileMsg && (
            <p className="text-xs text-brand-400 bg-brand-500/10 border border-brand-500/20 rounded-lg px-3 py-2">
              {profileMsg}
            </p>
          )}
          {profileErr && (
            <p className="text-xs text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2">
              {profileErr}
            </p>
          )}

          <div className="flex justify-end pt-1">
            <button
              type="submit"
              disabled={savingProf}
              className="btn-primary text-sm"
            >
              {savingProf ? "Saving…" : "Save changes"}
            </button>
          </div>
        </form>
      </Section>

      {/* Password */}
      <Section title="Security">
        <form onSubmit={handlePw} className="space-y-4">
          <Field label="Current password">
            <input
              className="input"
              type={showPw ? "text" : "password"}
              placeholder="••••••••"
              value={pwForm.old_password}
              onChange={(e) =>
                setPwForm((f) => ({ ...f, old_password: e.target.value }))
              }
            />
          </Field>
          <Field label="New password">
            <input
              className="input"
              type={showPw ? "text" : "password"}
              placeholder="Min. 8 characters"
              value={pwForm.new_password}
              onChange={(e) =>
                setPwForm((f) => ({ ...f, new_password: e.target.value }))
              }
            />
          </Field>
          <Field label="Confirm">
            <input
              className="input"
              type={showPw ? "text" : "password"}
              placeholder="Repeat new password"
              value={pwForm.confirm}
              onChange={(e) =>
                setPwForm((f) => ({ ...f, confirm: e.target.value }))
              }
            />
          </Field>

          <div className="flex items-center gap-2 pl-0 sm:pl-[calc(100%/3)]">
            <input
              id="showpw"
              type="checkbox"
              checked={showPw}
              onChange={() => setShowPw(!showPw)}
              className="w-3.5 h-3.5 rounded accent-brand-500 cursor-pointer"
            />
            <label
              htmlFor="showpw"
              className="text-xs text-slate-500 cursor-pointer"
            >
              Show passwords
            </label>
          </div>

          {pwMsg && (
            <p className="text-xs text-brand-400 bg-brand-500/10 border border-brand-500/20 rounded-lg px-3 py-2">
              {pwMsg}
            </p>
          )}
          {pwErr && (
            <p className="text-xs text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2">
              {pwErr}
            </p>
          )}

          <div className="flex justify-end pt-1">
            <button
              type="submit"
              disabled={savingPw}
              className="btn-primary text-sm"
            >
              {savingPw ? "Changing…" : "Change password"}
            </button>
          </div>
        </form>
      </Section>

      {/* Plan */}
      <Section title="Subscription plan">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-slate-300 font-medium capitalize">
              {user?.plan ?? "Free"} plan
            </p>
            <p className="text-xs text-slate-500 mt-0.5">
              {user?.plan === "free"
                ? "Basic access — 5 pairs, 1 portfolio, basic charts."
                : user?.plan === "pro"
                  ? "Full analytics — 40+ pairs, 10 portfolios, alerts, carry tools."
                  : user?.plan === "institutional"
                    ? "Unlimited — API access, options pricing, priority support."
                    : ""}
            </p>
          </div>
          <button className="btn-secondary text-xs px-3 py-1.5">
            Upgrade plan
          </button>
        </div>
      </Section>

      {/* Danger zone */}
      <Section title="Danger zone">
        <div className="flex items-center justify-between rounded-lg border border-red-900/30 bg-red-900/10 px-4 py-3">
          <div>
            <p className="text-sm text-red-400 font-medium">Delete account</p>
            <p className="text-xs text-slate-500 mt-0.5">
              Permanently remove your account and all data. This cannot be
              undone.
            </p>
          </div>
          <button className="text-xs font-medium text-red-400 border border-red-800/40 hover:border-red-600/60 hover:bg-red-900/20 px-3 py-1.5 rounded-lg transition-colors">
            Delete
          </button>
        </div>
      </Section>

      {/* Logout confirmation modal */}
      {confirmLogout && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="bg-surface-800 border border-surface-600 rounded-2xl p-6 w-[340px] space-y-4 shadow-2xl">
            <h3 className="text-slate-100 font-semibold">Sign out?</h3>
            <p className="text-sm text-slate-400">
              You'll need to sign in again to access your dashboard.
            </p>
            <div className="flex gap-2 pt-1">
              <button
                onClick={() => setConfirmLogout(false)}
                className="btn-secondary flex-1 text-sm"
              >
                Cancel
              </button>
              <button
                onClick={logout}
                className="flex-1 text-sm bg-red-900/30 hover:bg-red-900/50 border border-red-800/40 text-red-400 font-medium px-4 py-2 rounded-lg transition-colors"
              >
                Sign out
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
