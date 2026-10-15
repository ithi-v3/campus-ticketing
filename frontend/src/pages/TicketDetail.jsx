import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../api.js";
import { useAuth } from "../auth.jsx";
import { Priority, Status, fmtDate, fmtAge, useAsync, useLookups } from "../util.jsx";

export default function TicketDetail() {
  const { id } = useParams();
  const { user } = useAuth();
  const [version, setVersion] = useState(0);
  const { data, error, loading } = useAsync(() => api(`/tickets/${id}`), [id, version]);
  const reload = () => setVersion((v) => v + 1);

  if (loading && !data) return <p>Loading…</p>;
  if (error) return <p className="error">{error}</p>;

  const { ticket: t, history, assignments, feedback } = data;
  const isReporter = t.reporter_id === user.user_id;
  const isMyJob = user.role === "Technician" && t.technician_id === user.user_id;

  return (
    <>
      <div className="page-head">
        <h1>
          <span className="mono muted">#{t.ticket_id}</span> {t.title}
        </h1>
      </div>

      <div className="detail">
        <section>
          <dl className="facts">
            <div>
              <dt>Status</dt>
              <dd>
                <Status value={t.status} />
              </dd>
            </div>
            <div>
              <dt>Priority</dt>
              <dd>
                <Priority name={t.priority_name} rank={t.priority_rank} />
              </dd>
            </div>
            <div>
              <dt>Type</dt>
              <dd>{t.category_name}</dd>
            </div>
            <div>
              <dt>Location</dt>
              <dd>{t.location_label}</dd>
            </div>
            <div>
              <dt>Reported by</dt>
              <dd>{t.reporter_name}</dd>
            </div>
            <div>
              <dt>Technician</dt>
              <dd>{t.technician_name || <span className="muted">not assigned yet</span>}</dd>
            </div>
            <div>
              <dt>Raised</dt>
              <dd>{fmtDate(t.created_at)}</dd>
            </div>
            <div>
              <dt>{t.resolved_at ? "Took" : "Open for"}</dt>
              <dd>{fmtAge(t.age_hours)}</dd>
            </div>
          </dl>

          <h3>Details</h3>
          <p className="prose">{t.description}</p>

          {feedback && (
            <>
              <h3>Feedback</h3>
              <p>
                <strong>{feedback.rating} / 5</strong>
                {feedback.comments && <> — “{feedback.comments}”</>}
              </p>
            </>
          )}

          <h3>History</h3>
          <ol className="timeline">
            {history.map((h) => (
              <li key={h.history_id}>
                <span className="when">{fmtDate(h.changed_at)}</span>
                <span>
                  {h.old_status ? `${h.old_status} → ${h.new_status}` : h.new_status}
                  <span className="muted"> · {h.changed_by_name}</span>
                  {h.remarks && <span className="muted"> · {h.remarks}</span>}
                </span>
              </li>
            ))}
          </ol>

          {assignments.length > 1 && (
            <>
              <h3>Assignments</h3>
              <ul className="plain">
                {assignments.map((a) => (
                  <li key={a.assignment_id}>
                    {a.technician_name}
                    <span className="muted">
                      {" "}
                      · {fmtDate(a.assigned_at)}
                      {a.assigned_by_name && ` by ${a.assigned_by_name}`}
                      {a.is_current && " · current"}
                    </span>
                  </li>
                ))}
              </ul>
            </>
          )}
        </section>

        <aside>
          {isMyJob && t.status === "Assigned" && <ResolvePanel id={id} onDone={reload} />}
          {user.role === "Admin" && <AdminPanel ticket={t} onDone={reload} />}
          {isReporter && user.role === "Student" && t.status === "Resolved" && (
            <FeedbackPanel id={id} onDone={reload} />
          )}
          {isReporter && user.role === "Student" && ["Open", "Escalated"].includes(t.status) && (
            <EditPanel ticket={t} onDone={reload} />
          )}
        </aside>
      </div>
    </>
  );
}

function useAction() {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function run(fn) {
    setBusy(true);
    setError("");
    try {
      await fn();
      return true;
    } catch (e) {
      setError(e.message);
      return false;
    } finally {
      setBusy(false);
    }
  }
  return { busy, error, run };
}

function ResolvePanel({ id, onDone }) {
  const { busy, error, run } = useAction();
  return (
    <div className="panel">
      <h3>Finished the job?</h3>
      <p className="muted">The reporter is asked for feedback once you mark it resolved.</p>
      {error && <p className="error">{error}</p>}
      <button
        className="btn primary"
        disabled={busy}
        onClick={async () => {
          if (await run(() => api(`/tickets/${id}`, { method: "PATCH", body: { status: "Resolved" } }))) onDone();
        }}
      >
        Mark as resolved
      </button>
    </div>
  );
}

function FeedbackPanel({ id, onDone }) {
  const { busy, error, run } = useAction();
  const [rating, setRating] = useState("5");
  const [comments, setComments] = useState("");

  async function submit(e) {
    e.preventDefault();
    if (await run(() => api(`/tickets/${id}/feedback`, { method: "POST", body: { rating, comments } }))) onDone();
  }

  return (
    <form className="panel stack" onSubmit={submit}>
      <h3>Was it fixed properly?</h3>
      {error && <p className="error">{error}</p>}
      <label>
        Rating
        <select value={rating} onChange={(e) => setRating(e.target.value)}>
          <option value="5">5 – fixed, no complaints</option>
          <option value="4">4 – fine</option>
          <option value="3">3 – okay, took a while</option>
          <option value="2">2 – only partly fixed</option>
          <option value="1">1 – not fixed</option>
        </select>
      </label>
      <label>
        Comments <small>(optional)</small>
        <textarea rows={3} maxLength={500} value={comments} onChange={(e) => setComments(e.target.value)} />
      </label>
      <div>
        <button className="btn primary" disabled={busy}>
          Submit and close ticket
        </button>
      </div>
    </form>
  );
}

function EditPanel({ ticket, onDone }) {
  const lookups = useLookups();
  const { busy, error, run } = useAction();
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({
    title: ticket.title,
    description: ticket.description,
    category_id: ticket.category_id,
    location_id: ticket.location_id,
  });
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  if (!open)
    return (
      <div className="panel">
        <h3>Got something wrong?</h3>
        <button className="btn" onClick={() => setOpen(true)}>
          Edit this ticket
        </button>
      </div>
    );

  async function submit(e) {
    e.preventDefault();
    if (await run(() => api(`/tickets/${ticket.ticket_id}`, { method: "PATCH", body: form }))) {
      setOpen(false);
      onDone();
    }
  }

  return (
    <form className="panel stack" onSubmit={submit}>
      <h3>Edit ticket</h3>
      {error && <p className="error">{error}</p>}
      <label>
        Title
        <input value={form.title} onChange={set("title")} maxLength={150} required />
      </label>
      <label>
        Type
        <select value={form.category_id} onChange={set("category_id")}>
          {lookups?.categories.map((c) => (
            <option key={c.category_id} value={c.category_id}>
              {c.category_name}
            </option>
          ))}
        </select>
      </label>
      <label>
        Location
        <select value={form.location_id} onChange={set("location_id")}>
          {lookups?.locations.map((l) => (
            <option key={l.location_id} value={l.location_id}>
              {l.label}
            </option>
          ))}
        </select>
      </label>
      <label>
        Details
        <textarea rows={4} value={form.description} onChange={set("description")} maxLength={2000} required />
      </label>
      <div className="row-btns">
        <button className="btn primary" disabled={busy}>
          Save
        </button>
        <button type="button" className="linklike" onClick={() => setOpen(false)}>
          Cancel
        </button>
      </div>
    </form>
  );
}

function AdminPanel({ ticket, onDone }) {
  const navigate = useNavigate();
  const lookups = useLookups();
  const { busy, error, run } = useAction();
  const [techId, setTechId] = useState("");
  const techs = useAsync(() => api("/technicians", { params: { ticket_id: ticket.ticket_id } }), [ticket.ticket_id, ticket.technician_id]);
  const finished = ["Resolved", "Closed"].includes(ticket.status);

  async function assign(e) {
    e.preventDefault();
    if (await run(() => api(`/tickets/${ticket.ticket_id}/assign`, { method: "POST", body: { technician_id: techId } }))) {
      setTechId("");
      onDone();
    }
  }

  async function setPriority(e) {
    await run(() => api(`/tickets/${ticket.ticket_id}`, { method: "PATCH", body: { priority_id: e.target.value } }));
    onDone();
  }

  return (
    <div className="panel stack">
      <h3>Admin</h3>
      {error && <p className="error">{error}</p>}

      {!finished && (
        <form className="stack" onSubmit={assign}>
          <label>
            {ticket.technician_id ? "Reassign to" : "Assign to"}
            <select value={techId} onChange={(e) => setTechId(e.target.value)} required>
              <option value="">Choose a technician…</option>
              {techs.data?.items.map((t) => (
                <option key={t.user_id} value={t.user_id}>
                  {t.full_name} — {t.specialty || "general"}
                  {t.assigned_block ? `, ${t.assigned_block}` : ""} ({t.open_load} open)
                  {t.matches_category && t.matches_block ? "  ★ best fit" : t.matches_category ? "  · same trade" : ""}
                </option>
              ))}
            </select>
            <small>Ordered by trade and block match, then by how busy they are.</small>
          </label>
          <div>
            <button className="btn primary" disabled={busy || !techId}>
              Assign
            </button>
          </div>
        </form>
      )}

      {ticket.status !== "Closed" && (
        <label>
          Priority
          <select value={ticket.priority_id} onChange={setPriority} disabled={busy}>
            {lookups?.priorities.map((p) => (
              <option key={p.priority_id} value={p.priority_id}>
                {p.priority_name}
              </option>
            ))}
          </select>
        </label>
      )}

      {ticket.status !== "Closed" && (
        <div>
          <button
            className="btn danger"
            disabled={busy}
            onClick={async () => {
              if (!window.confirm("Close this ticket? It stays in the records but leaves the queue.")) return;
              if (await run(() => api(`/tickets/${ticket.ticket_id}`, { method: "DELETE" }))) {
                onDone();
                navigate("/");
              }
            }}
          >
            Close ticket
          </button>
        </div>
      )}
    </div>
  );
}
