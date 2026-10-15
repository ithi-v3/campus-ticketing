import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../auth.jsx";

export default function Signup() {
  const { signUp } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ full_name: "", email: "", phone: "", password: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await signUp(form);
      navigate("/");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-wrap">
      <div className="auth-intro">
        <h1>Campus Maintenance Desk</h1>
        <p>
          Accounts created here are student accounts. Technicians and admins are added by the
          maintenance office.
        </p>
      </div>
      <form className="auth-form" onSubmit={submit}>
        <h2>Create an account</h2>
        {error && <p className="error">{error}</p>}
        <label>
          Full name
          <input value={form.full_name} onChange={set("full_name")} required maxLength={100} />
        </label>
        <label>
          Email
          <input type="email" value={form.email} onChange={set("email")} required />
        </label>
        <label>
          Phone <small>(optional)</small>
          <input value={form.phone} onChange={set("phone")} maxLength={20} />
        </label>
        <label>
          Password
          <input type="password" value={form.password} onChange={set("password")} required minLength={8} maxLength={64} />
          <small>8 to 64 characters, with at least one number or symbol.</small>
        </label>
        <button className="btn primary" disabled={busy}>
          {busy ? "Creating…" : "Create account"}
        </button>
        <p className="alt">
          Already registered? <Link to="/login">Log in</Link>
        </p>
      </form>
    </div>
  );
}
