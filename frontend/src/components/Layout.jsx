import { useEffect, useState } from "react";
import { NavLink, useLocation, useNavigate } from "react-router-dom";
import { api } from "../api.js";
import { useAuth } from "../auth.jsx";

const HOME_LABEL = {
  Student: "My tickets",
  Technician: "Assigned to me",
  Admin: "All tickets",
};

export default function Layout({ children }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [unread, setUnread] = useState(0);

  useEffect(() => {
    let alive = true;
    const load = () =>
      api("/notifications")
        .then((r) => alive && setUnread(r.unread))
        .catch(() => {});
    load();
    const timer = setInterval(load, 60000);
    return () => {
      alive = false;
      clearInterval(timer);
    };
  }, [location.pathname]);

  async function handleLogout() {
    await logout();
    navigate("/login");
  }

  return (
    <>
      <header className="topbar">
        <div className="topbar-inner">
          <NavLink to="/" className="brand">
            Campus Maintenance Desk
          </NavLink>
          <nav>
            <NavLink to="/" end>
              {HOME_LABEL[user.role]}
            </NavLink>
            {user.role === "Student" && <NavLink to="/new">Report a problem</NavLink>}
            {user.role !== "Student" && (
              <NavLink to="/analytics">{user.role === "Admin" ? "Reports" : "My numbers"}</NavLink>
            )}
            {user.role === "Admin" && <NavLink to="/users">Users</NavLink>}
            <NavLink to="/notifications">
              Notifications{unread > 0 && <span className="count">{unread}</span>}
            </NavLink>
          </nav>
          <div className="who">
            <span>
              {user.full_name} <small>({user.role})</small>
            </span>
            <button className="linklike" onClick={handleLogout}>
              Log out
            </button>
          </div>
        </div>
      </header>
      <main className="page">{children}</main>
    </>
  );
}
