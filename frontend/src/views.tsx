// Dashboard views. The assistant is the primary feature; these read-only views show the
// signed-in employee's own leave/attendance/claims (and, for HR, the team overview and
// operational metrics) directly from the backend.
import { useEffect, useState } from "react";
import {
  api,
  type AttendanceSummary,
  type ClaimsSummary,
  type LeaveSummary,
  type MetricsData,
  type TeamOverview,
} from "./api";
import { Icon } from "./Icon";

export function MetricsView() {
  const [m, setM] = useState<MetricsData | null>(null);
  useEffect(() => {
    api
      .metrics()
      .then((r) => setM(r.data))
      .catch(() => setM(null));
  }, []);
  return (
    <div className="page">
      <h2>Metrics</h2>
      <p className="lead">Live operational metrics for the assistant (metadata only — no stored questions).</p>
      {!m ? (
        <p className="lead">Loading…</p>
      ) : m.count === 0 ? (
        <p className="lead">No queries recorded yet. Ask the assistant something first.</p>
      ) : (
        <>
          <div className="cards">
            <div className="card">
              <div className="k">
                <Icon name="clock" size={14} /> p95 latency
              </div>
              <div className="v">
                {m.p95_latency_ms} <small>ms</small>
              </div>
            </div>
            <div className="card">
              <div className="k">
                <Icon name="clock" size={14} /> p95 time-to-first-token
              </div>
              <div className="v">
                {m.p95_ttft_ms} <small>ms</small>
              </div>
            </div>
            <div className="card">
              <div className="k">Mean cost / query</div>
              <div className="v">${m.mean_cost_usd.toFixed(4)}</div>
            </div>
            <div className="card">
              <div className="k">Failure rate</div>
              <div className="v">{(m.failure_rate * 100).toFixed(1)}%</div>
            </div>
            <div className="card">
              <div className="k">Queries</div>
              <div className="v">{m.count}</div>
            </div>
          </div>
          <table className="data">
            <thead>
              <tr>
                <th>Route</th>
                <th>Count</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(m.by_route).map(([route, n]) => (
                <tr key={route}>
                  <td>{route}</td>
                  <td>{n}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </div>
  );
}

export function StatusView() {
  const [h, setH] = useState<{ status: string; version: string } | null>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    api
      .health()
      .then(setH)
      .catch(() => setFailed(true));
  }, []);

  return (
    <div className="page">
      <h2>Status</h2>
      <p className="lead">Live service status for the demo.</p>
      <div className="cards">
        <div className="card">
          <div className="k">
            <Icon name="shield" size={14} /> API
          </div>
          <div className="v">
            {failed ? (
              <span className="pill warn">offline</span>
            ) : !h ? (
              "…"
            ) : (
              <span className="pill ok">{h.status === "ok" ? "online" : h.status}</span>
            )}
          </div>
        </div>
        <div className="card">
          <div className="k">Version</div>
          <div className="v">{h?.version ?? "…"}</div>
        </div>
      </div>
    </div>
  );
}

export function LeaveView() {
  const [d, setD] = useState<LeaveSummary | null>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    api
      .myLeave()
      .then((r) => setD(r.data))
      .catch(() => setFailed(true));
  }, []);

  if (failed) return <p className="lead">Could not load your leave.</p>;
  if (!d) return <p className="lead">Loading…</p>;

  return (
    <div className="page">
      <h2>My leave</h2>
      <p className="lead">Your leave balance and requests (2026).</p>
      <div className="cards">
        <div className="card">
          <div className="k">
            <Icon name="leave" size={14} /> Remaining
          </div>
          <div className="v">
            {d.remaining_days} <small>days</small>
          </div>
        </div>
        <div className="card">
          <div className="k">Entitlement</div>
          <div className="v">
            {d.entitlement_days} <small>days</small>
          </div>
        </div>
        <div className="card">
          <div className="k">Used</div>
          <div className="v">
            {d.used_days} <small>days</small>
          </div>
        </div>
      </div>
      {d.records.length === 0 ? (
        <p className="lead">No leave requests yet.</p>
      ) : (
        <table className="data">
          <thead>
            <tr>
              <th>Type</th>
              <th>Dates</th>
              <th>Days</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {d.records.map((r, i) => (
              <tr key={i}>
                <td>{r.leave_type}</td>
                <td>{dateRange(r.start_date, r.end_date)}</td>
                <td>{r.days}</td>
                <td>
                  <span className={pill(r.status)}>{r.status}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

export function AttendanceView() {
  const [d, setD] = useState<AttendanceSummary | null>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    api
      .myAttendance()
      .then((r) => setD(r.data))
      .catch(() => setFailed(true));
  }, []);

  if (failed) return <p className="lead">Could not load your attendance.</p>;
  if (!d) return <p className="lead">Loading…</p>;

  return (
    <div className="page">
      <h2>Attendance</h2>
      <p className="lead">Your attendance summary.</p>
      <div className="cards">
        {["present", "late", "absent"].map((s) => (
          <div className="card" key={s}>
            <div className="k">{s[0].toUpperCase() + s.slice(1)}</div>
            <div className="v">
              {d.counts[s] ?? 0} <small>days</small>
            </div>
          </div>
        ))}
      </div>
      {d.records.length === 0 ? (
        <p className="lead">No attendance records yet.</p>
      ) : (
        <table className="data">
          <thead>
            <tr>
              <th>Date</th>
              <th>Status</th>
              <th>Minutes late</th>
            </tr>
          </thead>
          <tbody>
            {d.records.map((r, i) => (
              <tr key={i}>
                <td>{fmtDate(r.work_date)}</td>
                <td>
                  <span className={pill(r.status)}>{r.status}</span>
                </td>
                <td>{r.minutes_late}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

export function ClaimsView() {
  const [d, setD] = useState<ClaimsSummary | null>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    api
      .myClaims()
      .then((r) => setD(r.data))
      .catch(() => setFailed(true));
  }, []);

  if (failed) return <p className="lead">Could not load your claims.</p>;
  if (!d) return <p className="lead">Loading…</p>;

  return (
    <div className="page">
      <h2>My claims</h2>
      <p className="lead">Your reimbursement claims.</p>
      {d.claims.length === 0 ? (
        <p className="lead">No claims yet.</p>
      ) : (
        <table className="data">
          <thead>
            <tr>
              <th>Type</th>
              <th>Amount</th>
              <th>Submitted</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {d.claims.map((c, i) => (
              <tr key={i}>
                <td>{c.claim_type}</td>
                <td>{rupiah(c.amount)}</td>
                <td>{fmtDate(c.submitted)}</td>
                <td>
                  <span className={pill(c.status)}>{c.status}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

// "approved"/"paid"/"present" read as positive; everything else (pending/late/absent/…) as a
// warning. Reuses the existing .pill ok|warn chips — no new styling.
const OK_STATUS = new Set(["approved", "paid", "present"]);
const pill = (status: string): string => `pill ${OK_STATUS.has(status) ? "ok" : "warn"}`;

const rupiah = (n: number): string => `Rp ${n.toLocaleString("en-US")}`;

// ISO date/datetime → "5 Nov 2026". A leave entry spanning days shows a compact range.
const fmtDate = (iso: string): string =>
  new Date(iso).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });
const dateRange = (start: string, end: string): string =>
  start === end ? fmtDate(start) : `${fmtDate(start)} – ${fmtDate(end)}`;

// HR-admin only (role-gated in App.tsx; the backend 403 is the real gate). Whole-company
// aggregates from GET /api/v1/admin/team — no raw per-employee leave/claim rows.
export function TeamView() {
  const [t, setT] = useState<TeamOverview | null>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    api
      .team()
      .then((r) => setT(r.data))
      .catch(() => setFailed(true));
  }, []);

  if (failed) return <p className="lead">Could not load the team dashboard.</p>;
  if (!t) return <p className="lead">Loading…</p>;

  return (
    <div className="page">
      <h2>Team overview</h2>
      <p className="lead">Whole-company aggregates for HR. Read-only — no individual records.</p>

      <div className="cards">
        <div className="card">
          <div className="k">
            <Icon name="leave" size={14} /> Headcount
          </div>
          <div className="v">{t.headcount}</div>
        </div>
        <div className="card">
          <div className="k">Leave remaining (2026)</div>
          <div className="v">
            {t.leave.remaining_days} <small>of {t.leave.entitlement_days} days</small>
          </div>
        </div>
        <div className="card">
          <div className="k">Leave used</div>
          <div className="v">
            {t.leave.used_days} <small>days</small>
          </div>
        </div>
        <div className="card">
          <div className="k">Pending requests</div>
          <div className="v">{t.leave.pending_requests}</div>
        </div>
      </div>

      <h3>By department</h3>
      <table className="data">
        <thead>
          <tr>
            <th>Department</th>
            <th>Headcount</th>
          </tr>
        </thead>
        <tbody>
          {Object.entries(t.by_department).map(([dept, n]) => (
            <tr key={dept}>
              <td>{dept}</td>
              <td>{n}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <h3>Attendance (team)</h3>
      <table className="data">
        <thead>
          <tr>
            <th>Status</th>
            <th>Records</th>
          </tr>
        </thead>
        <tbody>
          {Object.entries(t.attendance).map(([status, n]) => (
            <tr key={status}>
              <td>
                <span className={pill(status)}>{status}</span>
              </td>
              <td>{n}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <h3>Claims by status</h3>
      <table className="data">
        <thead>
          <tr>
            <th>Status</th>
            <th>Count</th>
            <th>Total amount</th>
          </tr>
        </thead>
        <tbody>
          {Object.entries(t.claims_count).map(([status, n]) => (
            <tr key={status}>
              <td>
                <span className={pill(status)}>{status}</span>
              </td>
              <td>{n}</td>
              <td>{rupiah(t.claims_amount[status] ?? 0)}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <h3>Roster</h3>
      <table className="data">
        <thead>
          <tr>
            <th>Name</th>
            <th>Department</th>
            <th>Role</th>
            <th>Leave remaining</th>
          </tr>
        </thead>
        <tbody>
          {t.roster.map((row) => (
            <tr key={row.full_name}>
              <td>{row.full_name}</td>
              <td>{row.department}</td>
              <td>{row.role}</td>
              <td>
                {row.remaining_days} <small>of {row.entitlement_days}</small>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
