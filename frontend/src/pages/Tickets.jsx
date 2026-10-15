import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api.js";
import { useAuth } from "../auth.jsx";
import { Pager, Priority, Status, fmtAge, useAsync, useLookups } from "../util.jsx";

const STATUSES = ["Open", "Assigned", "Escalated", "Resolved", "Closed"];

const CONFIG = {
  Student: { path: "/tickets/mine", title: "My tickets", empty: "You haven't reported anything yet." },
  Technician: { path: "/tickets/assigned", title: "Assigned to me", empty: "Nothing is assigned to you right now." },
  Admin: { path: "/tickets", title: "All tickets", empty: "No tickets match." },
};

export default function Tickets() {
  const { user } = useAuth();
  const cfg = CONFIG[user.role];
  const lookups = useLookups();
  const navigate = useNavigate();

  const [filters, setFilters] = useState({ q: "", status: "", category_id: "", priority_id: "", sort: "created_at" });
  const [applied, setApplied] = useState(filters);
  const [page, setPage] = useState(1);

  const { data, error, loading } = useAsync(
    () => api(cfg.path, { params: { ...applied, page, per_page: 10 } }),
    [applied, page, cfg.path]
  );

  const set = (k) => (e) => setFilters({ ...filters, [k]: e.target.value });

  function search(e) {
    e.preventDefault();
    setPage(1);
    setApplied(filters);
  }

  function reset() {
    const blank = { q: "", status: "", category_id: "", priority_id: "", sort: "created_at" };
    setFilters(blank);
    setApplied(blank);
    setPage(1);
  }

  const showTech = user.role !== "Technician";
  const showReporter = user.role !== "Student";

  return (
    <>
      <div className="page-head">
        <h1>{cfg.title}</h1>
        {user.role === "Student" && (
          <Link to="/new" className="btn primary">
            Report a problem
          </Link>
        )}
      </div>

      <form className="filters" onSubmit={search}>
        <input
          type="search"
          placeholder="Search title, description, room or ticket number"
          value={filters.q}
          onChange={set("q")}
        />
        <select value={filters.status} onChange={set("status")} aria-label="Status">
          <option value="">Any status</option>
          {STATUSES.map((s) => (
            <option key={s}>{s}</option>
          ))}
        </select>
        <select value={filters.category_id} onChange={set("category_id")} aria-label="Category">
          <option value="">Any category</option>
          {lookups?.categories.map((c) => (
            <option key={c.category_id} value={c.category_id}>
              {c.category_name}
            </option>
          ))}
        </select>
        <select value={filters.priority_id} onChange={set("priority_id")} aria-label="Priority">
          <option value="">Any priority</option>
          {lookups?.priorities.map((p) => (
            <option key={p.priority_id} value={p.priority_id}>
              {p.priority_name}
            </option>
          ))}
        </select>
        <select value={filters.sort} onChange={set("sort")} aria-label="Sort by">
          <option value="created_at">Newest first</option>
          <option value="priority">Highest priority first</option>
          <option value="updated_at">Recently updated</option>
        </select>
        <button className="btn">Apply</button>
        <button type="button" className="linklike" onClick={reset}>
          Clear
        </button>
      </form>

      {error && <p className="error">{error}</p>}

      <table className="grid">
        <thead>
          <tr>
            <th>#</th>
            <th>Problem</th>
            <th>Where</th>
            <th>Priority</th>
            <th>Status</th>
            {showReporter && <th>Reported by</th>}
            {showTech && <th>Technician</th>}
            <th>Age</th>
          </tr>
        </thead>
        <tbody>
          {data?.items.map((t) => (
            <tr key={t.ticket_id} className="clickable" onClick={() => navigate(`/tickets/${t.ticket_id}`)}>
              <td className="mono">{t.ticket_id}</td>
              <td>
                <Link to={`/tickets/${t.ticket_id}`} onClick={(e) => e.stopPropagation()}>
                  {t.title}
                </Link>
                <div className="sub">{t.category_name}</div>
              </td>
              <td>{t.location_label}</td>
              <td>
                <Priority name={t.priority_name} rank={t.priority_rank} />
              </td>
              <td>
                <Status value={t.status} />
              </td>
              {showReporter && <td>{t.reporter_name}</td>}
              {showTech && <td>{t.technician_name || <span className="muted">not assigned</span>}</td>}
              <td>{fmtAge(t.age_hours)}</td>
            </tr>
          ))}
          {data && data.items.length === 0 && (
            <tr>
              <td colSpan={8} className="empty">
                {cfg.empty}
              </td>
            </tr>
          )}
          {loading && !data && (
            <tr>
              <td colSpan={8} className="empty">
                Loading…
              </td>
            </tr>
          )}
        </tbody>
      </table>

      {data && (
        <div className="table-foot">
          <span>
            {data.total} ticket{data.total === 1 ? "" : "s"}
          </span>
          <Pager page={data.page} pages={data.pages} onChange={setPage} />
        </div>
      )}
    </>
  );
}
