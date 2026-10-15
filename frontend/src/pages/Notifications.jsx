import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api.js";
import { fmtDate, useAsync } from "../util.jsx";

export default function Notifications() {
  const navigate = useNavigate();
  const [version, setVersion] = useState(0);
  const { data, error } = useAsync(() => api("/notifications"), [version]);

  async function open(n) {
    if (!n.is_read) await api(`/notifications/${n.notification_id}/read`, { method: "POST" }).catch(() => {});
    if (n.ticket_id) navigate(`/tickets/${n.ticket_id}`);
    else setVersion((v) => v + 1);
  }

  async function readAll() {
    await api("/notifications/read-all", { method: "POST" });
    setVersion((v) => v + 1);
  }

  return (
    <>
      <div className="page-head">
        <h1>Notifications</h1>
        {data?.unread > 0 && (
          <button className="btn" onClick={readAll}>
            Mark all as read
          </button>
        )}
      </div>
      {error && <p className="error">{error}</p>}
      <ul className="notes">
        {data?.items.map((n) => (
          <li key={n.notification_id} className={n.is_read ? "" : "unread"}>
            <button onClick={() => open(n)}>
              <span>{n.message}</span>
              <span className="muted">{fmtDate(n.created_at)}</span>
            </button>
          </li>
        ))}
        {data && data.items.length === 0 && <li className="empty">Nothing yet.</li>}
      </ul>
    </>
  );
}
