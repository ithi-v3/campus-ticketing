import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api.js";
import { useLookups } from "../util.jsx";

export default function NewTicket() {
  const lookups = useLookups();
  const navigate = useNavigate();
  const [form, setForm] = useState({
    title: "",
    category_id: "",
    location_id: "",
    priority_id: "",
    description: "",
  });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  if (!lookups) return <p>Loading…</p>;

  // group rooms under their block
  const blocks = {};
  lookups.locations.forEach((l) => (blocks[l.block_name] = [...(blocks[l.block_name] || []), l]));
  const choices = lookups.priorities.filter((p) => p.priority_name !== "Critical");
  const medium = choices.find((p) => p.priority_name === "Medium");

  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const body = { ...form, priority_id: form.priority_id || medium?.priority_id };
      const r = await api("/tickets", { method: "POST", body });
      navigate(`/tickets/${r.ticket.ticket_id}`);
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  }

  return (
    <>
      <div className="page-head">
        <h1>Report a problem</h1>
      </div>
      <form className="stack narrow" onSubmit={submit}>
        {error && <p className="error">{error}</p>}
        <label>
          What's wrong?
          <input value={form.title} onChange={set("title")} maxLength={150} required placeholder="e.g. Ceiling fan makes a grinding noise" />
        </label>
        <div className="row">
          <label>
            Type of problem
            <select value={form.category_id} onChange={set("category_id")} required>
              <option value="">Choose…</option>
              {lookups.categories.map((c) => (
                <option key={c.category_id} value={c.category_id}>
                  {c.category_name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Where is it?
            <select value={form.location_id} onChange={set("location_id")} required>
              <option value="">Choose…</option>
              {Object.entries(blocks).map(([block, rooms]) => (
                <optgroup key={block} label={block}>
                  {rooms.map((l) => (
                    <option key={l.location_id} value={l.location_id}>
                      {l.room}
                    </option>
                  ))}
                </optgroup>
              ))}
            </select>
          </label>
        </div>
        <label>
          How urgent is it?
          <select value={form.priority_id || medium?.priority_id || ""} onChange={set("priority_id")}>
            {choices.map((p) => (
              <option key={p.priority_id} value={p.priority_id}>
                {p.priority_name}
              </option>
            ))}
          </select>
          <small>
            Unassigned tickets are bumped up automatically if nobody picks them up in time. Use High
            only for things that are unsafe or stop you from working.
          </small>
        </label>
        <label>
          Details
          <textarea rows={5} value={form.description} onChange={set("description")} maxLength={2000} required placeholder="What happened, since when, anything the technician should know" />
        </label>
        <div>
          <button className="btn primary" disabled={busy}>
            {busy ? "Submitting…" : "Submit ticket"}
          </button>
        </div>
      </form>
    </>
  );
}
