import { useEffect, useState } from "react";
import "./app.css";
import { api, type Me, type Sources } from "./api";
import { Chat } from "./Chat";
import { Icon } from "./Icon";
import { SignIn } from "./SignIn";
import { SourcesDrawer } from "./SourcesDrawer";
import { AttendanceView, ClaimsView, LeaveView, MetricsView } from "./views";

type ViewId = "ask" | "leave" | "attend" | "claims" | "metrics";

const TITLES: Record<ViewId, [string, string]> = {
  ask: ["Ask assistant", "Policy & your own records · answered with sources"],
  leave: ["My leave", "Your leave balance and recent requests"],
  attend: ["Attendance", "Your attendance summary"],
  claims: ["My claims", "Your reimbursement claims"],
  metrics: ["Metrics", "How the assistant is performing"],
};

const NAV: { id: ViewId; icon: Parameters<typeof Icon>[0]["name"]; label: string }[] = [
  { id: "ask", icon: "ask", label: "Ask assistant" },
  { id: "leave", icon: "leave", label: "My leave" },
  { id: "attend", icon: "clock", label: "Attendance" },
  { id: "claims", icon: "claim", label: "My claims" },
  { id: "metrics", icon: "chart", label: "Metrics" },
];

export default function App() {
  const [me, setMe] = useState<Me | null>(null);
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState<ViewId>("ask");
  const [sources, setSources] = useState<Sources | null>(null);
  const [navOpen, setNavOpen] = useState(false);
  const [theme, setTheme] = useState<"dark" | "light">("dark");

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
  }, [theme]);

  useEffect(() => {
    api
      .me()
      .then((r) => setMe(r.data))
      .catch(() => setMe(null))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return null;
  if (!me) return <SignIn onSignedIn={() => api.me().then((r) => setMe(r.data))} />;

  const [title, sub] = TITLES[view];
  const initials = me.full_name
    .split(" ")
    .map((p) => p[0])
    .slice(0, 2)
    .join("");

  async function signOut() {
    await api.logout();
    setMe(null);
  }

  function go(v: ViewId) {
    setView(v);
    setNavOpen(false);
  }

  return (
    <div className="shell">
      <aside className={`sidebar${navOpen ? " open" : ""}`} aria-label="Sidebar">
        <div className="brand">
          <span className="mark">
            <Icon name="logo" size={28} />
          </span>
          HR Assistant <span className="tag">sample</span>
        </div>
        <div className="nav-label" id="nav-ws">
          Workspace
        </div>
        <nav className="nav" aria-labelledby="nav-ws">
          {NAV.map((n) => (
            <button
              key={n.id}
              type="button"
              className={view === n.id ? "active" : ""}
              onClick={() => go(n.id)}
            >
              <Icon name={n.icon} size={17} /> {n.label}
            </button>
          ))}
        </nav>
        <div className="spacer" />
        <div className="usercard">
          <span className="avatar">{initials}</span>
          <span className="meta">
            <span className="nm">{me.full_name}</span>
            <span className="dp">
              {me.department} · {me.role}
            </span>
          </span>
        </div>
      </aside>

      <div className="main">
        <header className="topbar">
          <div className="row">
            <button
              className="iconbtn menu-toggle"
              type="button"
              aria-label="Open navigation"
              onClick={() => setNavOpen((o) => !o)}
            >
              <Icon name="menu" size={17} />
            </button>
            <div>
              <h1>{title}</h1>
              <div className="sub">{sub}</div>
            </div>
          </div>
          <div className="row">
            <button
              className="iconbtn"
              type="button"
              aria-label="Toggle dark mode"
              onClick={() => setTheme((t) => (t === "dark" ? "light" : "dark"))}
            >
              <Icon name="moon" size={17} />
            </button>
            <button className="iconbtn" type="button" aria-label="Sign out" onClick={signOut}>
              <Icon name="signout" size={17} />
            </button>
          </div>
        </header>

        {view === "ask" ? (
          <Chat onOpenSources={setSources} />
        ) : (
          <main className="scroll">
            <section className="view">
              {view === "leave" && <LeaveView />}
              {view === "attend" && <AttendanceView />}
              {view === "claims" && <ClaimsView />}
              {view === "metrics" && <MetricsView />}
            </section>
          </main>
        )}
      </div>

      <SourcesDrawer sources={sources} onClose={() => setSources(null)} />
    </div>
  );
}
