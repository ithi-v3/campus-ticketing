import { useState } from "react";
import { api } from "../api.js";
import { useAuth } from "../auth.jsx";
import { useAsync } from "../util.jsx";

const num = (v, suffix = "") => (v === null || v === undefined ? "–" : `${v}${suffix}`);

export default function Analytics() {
  const { user } = useAuth();
  return user.role === "Admin" ? <AdminReports /> : <MyNumbers />;
}

function MyNumbers() {
  const { data, error } = useAsync(() => api("/reports/me"), []);
  const r = data?.report;
  return (
    <>
      <div className="page-head">
        <h1>My numbers</h1>
      </div>
      {error && <p className="error">{error}</p>}
      {r && (
        <dl className="stats">
          <div><dt>Tickets assigned to you</dt><dd>{r.tickets_assigned}</dd></div>
          <div><dt>Resolved</dt><dd>{r.tickets_resolved}</dd></div>
          <div><dt>Still open</dt><dd>{r.open_load}</dd></div>
          <div><dt>Average time to resolve</dt><dd>{num(r.avg_resolution_hours, " h")}</dd></div>
          <div><dt>Average rating</dt><dd>{num(r.avg_rating, " / 5")}</dd></div>
        </dl>
      )}
    </>
  );
}

function Bars({ rows, labelKey }) {
  const max = Math.max(1, ...rows.map((r) => r.count));
  return (
    <table className="bars">
      <tbody>
        {rows.map((r) => (
          <tr key={r[labelKey]}>
            <td>{r[labelKey]}</td>
            <td className="track">
              <span style={{ width: `${(r.count / max) * 100}%` }} />
            </td>
            <td className="mono">{r.count}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function AdminReports() {
  const [version, setVersion] = useState(0);
  const [note, setNote] = useState("");
  const summary = useAsync(() => api("/reports/summary"), [version]);
  const techs = useAsync(() => api("/reports/technicians"), [version]);

  async function runSweep() {
    setNote("");
    try {
      const r = await api("/reports/escalate", { method: "POST" });
      setNote(r.escalated ? `${r.escalated} overdue ticket(s) escalated.` : "Nothing is overdue right now.");
      setVersion((v) => v + 1);
    } catch (e) {
      setNote(e.message);
    }
  }

  const o = summary.data?.overall;

  return (
    <>
      <div className="page-head">
        <h1>Reports</h1>
        <div className="row-btns">
          {note && <span className="muted">{note}</span>}
          <button className="btn" onClick={runSweep}>
            Check for overdue tickets
          </button>
        </div>
      </div>

      {(summary.error || techs.error) && <p className="error">{summary.error || techs.error}</p>}

      {o && (
        <dl className="stats">
          <div><dt>Tickets in total</dt><dd>{o.total}</dd></div>
          <div><dt>Waiting for a technician</dt><dd>{o.awaiting_assignment}</dd></div>
          <div><dt>Average time to resolve</dt><dd>{num(o.avg_resolution_hours, " h")}</dd></div>
          <div><dt>Average rating</dt><dd>{num(o.avg_rating, " / 5")}</dd></div>
        </dl>
      )}

      <div className="two-col">
        <section>
          <h3>By status</h3>
          {summary.data && <Bars rows={summary.data.by_status} labelKey="status" />}
        </section>
        <section>
          <h3>By type of problem</h3>
          {summary.data && <Bars rows={summary.data.by_category} labelKey="category_name" />}
        </section>
      </div>

      <h3>Technicians</h3>
      <table className="grid">
        <thead>
          <tr>
            <th>Name</th>
            <th>Assigned</th>
            <th>Resolved</th>
            <th>Open now</th>
            <th>Avg. hours to resolve</th>
            <th>Avg. rating</th>
          </tr>
        </thead>
        <tbody>
          {techs.data?.items.map((t) => (
            <tr key={t.technician_id}>
              <td>{t.technician_name}</td>
              <td>{t.tickets_assigned}</td>
              <td>{t.tickets_resolved}</td>
              <td>{t.open_load}</td>
              <td>{num(t.avg_resolution_hours)}</td>
              <td>{num(t.avg_rating)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  );
}
