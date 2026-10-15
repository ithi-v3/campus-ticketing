import { useState } from "react";
import { api } from "../api.js";
import { useAuth } from "../auth.jsx";
import { useAsync, useLookups } from "../util.jsx";

const blank = { full_name: "", email: "", password: "", role: "Technician", phone: "", specialty_category_id: "", assigned_block: "" };

export default function Users() {
  const { user: me } = useAuth();
  const lookups = useLookups();
  const [version, setVersion] = useState(0);
  const [role, setRole] = useState("");
  const { data, error } = useAsync(() => api("/users", { params: { role } }), [version, role]);
  const [form, setForm] = useState(blank);
  const [formError, setFormError] = useState("");
  const [showForm, setShowForm] = useState(false);

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });
  const blocks = [...new Set(lookups?.locations.map((l) => l.block_name) || [])];

  async function create(e) {
    e.preventDefault();
    setFormError("");
    try {
      await api("/users", { method: "POST", body: form });
      setForm(blank);
      setShowForm(false);
      setVersion((v) => v + 1);
    } catch (err) {
      setFormError(err.message);
    }
  }

  async function toggle(u) {
    try {
      await api(`/users/${u.user_id}`, { method: "PATCH", body: { is_active: !u.is_active } });
      setVersion((v) => v + 1);
    } catch (err) {
      alert(err.message);
    }
  }

  async function changeRole(u, newRole) {
    try {
      await api(`/users/${u.user_id}`, { method: "PATCH", body: { role: newRole } });
    } catch (err) {
      alert(err.message);
    }
    setVersion((v) => v + 1);
  }

  return (
    <>
      <div className="page-head">
        <h1>Users</h1>
        <div className="row-btns">
          <select value={role} onChange={(e) => setRole(e.target.value)} aria-label="Filter by role">
            <option value="">Everyone</option>
            <option>Student</option>
            <option>Technician</option>
            <option>Admin</option>
          </select>
          <button className="btn primary" onClick={() => setShowForm(!showForm)}>
            {showForm ? "Cancel" : "Add a user"}
          </button>
        </div>
      </div>

      {showForm && (
        <form className="panel stack" onSubmit={create}>
          {formError && <p className="error">{formError}</p>}
          <div className="row">
            <label>Full name<input value={form.full_name} onChange={set("full_name")} required /></label>
            <label>Email<input type="email" value={form.email} onChange={set("email")} required /></label>
          </div>
          <div className="row">
            <label>Temporary password<input type="password" value={form.password} onChange={set("password")} required minLength={8} /></label>
            <label>
              Role
              <select value={form.role} onChange={set("role")}>
                <option>Technician</option>
                <option>Admin</option>
                <option>Student</option>
              </select>
            </label>
          </div>
          {form.role === "Technician" && (
            <div className="row">
              <label>
                Trade
                <select value={form.specialty_category_id} onChange={set("specialty_category_id")}>
                  <option value="">General</option>
                  {lookups?.categories.map((c) => (
                    <option key={c.category_id} value={c.category_id}>{c.category_name}</option>
                  ))}
                </select>
              </label>
              <label>
                Usual block
                <select value={form.assigned_block} onChange={set("assigned_block")}>
                  <option value="">Anywhere</option>
                  {blocks.map((b) => <option key={b}>{b}</option>)}
                </select>
              </label>
            </div>
          )}
          <div><button className="btn primary">Create user</button></div>
        </form>
      )}

      {error && <p className="error">{error}</p>}

      <table className="grid">
        <thead>
          <tr><th>Name</th><th>Email</th><th>Role</th><th>Trade / block</th><th>Account</th></tr>
        </thead>
        <tbody>
          {data?.items.map((u) => (
            <tr key={u.user_id} className={u.is_active ? "" : "inactive"}>
              <td>{u.full_name}</td>
              <td>{u.email}</td>
              <td>
                <select value={u.role} disabled={u.user_id === me.user_id} onChange={(e) => changeRole(u, e.target.value)} aria-label={`Role for ${u.full_name}`}>
                  <option>Student</option>
                  <option>Technician</option>
                  <option>Admin</option>
                </select>
              </td>
              <td>{u.role === "Technician" ? [u.specialty, u.assigned_block].filter(Boolean).join(" · ") || "General" : ""}</td>
              <td>
                {u.user_id === me.user_id ? (
                  <span className="muted">you</span>
                ) : (
                  <button className="linklike" onClick={() => toggle(u)}>
                    {u.is_active ? "Deactivate" : "Reactivate"}
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  );
}
