import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../auth.jsx";

export default function Login() {
  const { signIn } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await signIn(email, password);
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
          Report a broken fan, a leaking tap or a dead Wi-Fi point, and see who is fixing it. Log
          in with your campus account to continue.
        </p>
      </div>
      <form className="auth-form" onSubmit={submit}>
        <h2>Log in</h2>
        {error && <p className="error">{error}</p>}
        <label>
          Email
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoFocus />
        </label>
        <label>
          Password
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
        </label>
        <button className="btn primary" disabled={busy}>
          {busy ? "Logging in…" : "Log in"}
        </button>
        <p className="alt">
          New here? <Link to="/signup">Create a student account</Link>
        </p>
      </form>
    </div>
  );
}
