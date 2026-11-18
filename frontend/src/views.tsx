// Sample dashboard views (labelled sample). The assistant is the real feature; these show
// the same data a user can ask about, for navigation context. The Metrics view is real —
// it reads live operational aggregates from the backend.
import { useEffect, useState } from "react";
import { api, type MetricsData, type TeamOverview } from "./api";
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

export function LeaveView() {
  return (
    <div className="page">
      <h2>My leave</h2>
      <p className="lead">
        Your leave balance and recent requests. <span className="sample-tag">sample demo data</span>
      </p>
      <div className="cards">
        <div className="card">
          <div className="k">
            <Icon name="leave" size={14} /> Remaining (2026)
          </div>
          <div className="v">
            7 <small>days</small>
          </div>
        </div>
        <div className="card">
          <div className="k">Entitlement</div>
          <div className="v">
            12 <small>days</small>
          </div>
        </div>
        <div className="card">
          <div className="k">Used</div>
          <div className="v">
            5 <small>days</small>
          </div>
        </div>
      </div>
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
          <tr>
            <td>Annual</td>
            <td>12–14 Mar 2026</td>
            <td>3</td>
            <td>
              <span className="pill ok">approved</span>
            </td>
          </tr>
          <tr>
            <td>Sick</td>
            <td>2 May 2026</td>
            <td>1</td>
            <td>
              <span className="pill ok">approved</span>
            </td>
          </tr>
          <tr>
            <td>Annual</td>
            <td>20 Jun 2026</td>
            <td>1</td>
            <td>
              <span className="pill warn">pending</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  );
}

export function AttendanceView() {
  return (
    <div className="page">
      <h2>Attendance</h2>
      <p className="lead">
        Your attendance summary. <span className="sample-tag">sample demo data</span>
      </p>
      <div className="cards">
        <div className="card">
          <div className="k">Present</div>
          <div className="v">
            19 <small>days</small>
          </div>
        </div>
        <div className="card">
          <div className="k">Late</div>
          <div className="v">
            2 <small>days</small>
          </div>
        </div>
        <div className="card">
          <div className="k">Absent</div>
          <div className="v">
            0 <small>days</small>
          </div>
        </div>
      </div>
      <table className="data">
        <thead>
          <tr>
            <th>Date</th>
            <th>Status</th>
            <th>Minutes late</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>3 Nov 2026</td>
            <td>
              <span className="pill ok">present</span>
            </td>
            <td>0</td>
          </tr>
          <tr>
            <td>4 Nov 2026</td>
            <td>
              <span className="pill warn">late</span>
            </td>
            <td>12</td>
          </tr>
          <tr>
            <td>5 Nov 2026</td>
            <td>
              <span className="pill ok">present</span>
            </td>
            <td>0</td>
          </tr>
        </tbody>
      </table>
    </div>
  );
}

export function ClaimsView() {
  return (
    <div className="page">
      <h2>My claims</h2>
      <p className="lead">
        Your reimbursement claims. <span className="sample-tag">sample demo data</span>
      </p>
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
          <tr>
            <td>Medical</td>
            <td>Rp 450,000</td>
            <td>10 Oct 2026</td>
            <td>
              <span className="pill ok">paid</span>
            </td>
          </tr>
          <tr>
            <td>Transport</td>
            <td>Rp 120,000</td>
            <td>28 Oct 2026</td>
            <td>
              <span className="pill ok">approved</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  );
}

// "approved"/"paid"/"present" read as positive; everything else (pending/late/absent/…) as a
// warning. Reuses the existing .pill ok|warn chips — no new styling.
const OK_STATUS = new Set(["approved", "paid", "present"]);
const pill = (status: string): string => `pill ${OK_STATUS.has(status) ? "ok" : "warn"}`;

const rupiah = (n: number): string => `Rp ${n.toLocaleString("en-US")}`;

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
