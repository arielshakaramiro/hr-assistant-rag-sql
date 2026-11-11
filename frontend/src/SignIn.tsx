import { useState } from "react";
import { api, ApiError } from "./api";
import { Icon } from "./Icon";

export function SignIn({ onSignedIn }: { onSignedIn: () => void }) {
  const [email, setEmail] = useState("maya@example.com");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setErr("");
    setBusy(true);
    try {
      await api.login(email, password);
      onSignedIn();
    } catch (ex) {
      if (ex instanceof ApiError && ex.status === 401) setErr("Email or password is incorrect.");
      else setErr("Couldn't sign in. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="signin-wrap">
      <form className="signin" onSubmit={submit}>
        <h1 className="brand">
          <span className="mark">
            <Icon name="logo" size={28} />
          </span>
          HR Assistant <span className="tag">sample</span>
        </h1>
        <p className="sub">Sign in to ask about policy and your own records</p>
        {err && (
          <p className="err" role="alert">
            {err}
          </p>
        )}
        <div className="field">
          <label htmlFor="email">Email</label>
          <input
            id="email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="username"
            required
          />
        </div>
        <div className="field">
          <label htmlFor="pw">Password</label>
          <input
            id="pw"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            required
          />
        </div>
        <button className="send" type="submit" disabled={busy}>
          {busy ? "Signing in…" : "Sign in"}
        </button>
        <p className="demo-note">
          Demo accounts are listed in the project README (sample data).
        </p>
      </form>
    </main>
  );
}
