import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth.jsx";
import Layout from "./components/Layout.jsx";
import Login from "./pages/Login.jsx";
import Signup from "./pages/Signup.jsx";
import Tickets from "./pages/Tickets.jsx";
import NewTicket from "./pages/NewTicket.jsx";
import TicketDetail from "./pages/TicketDetail.jsx";
import Analytics from "./pages/Analytics.jsx";
import Users from "./pages/Users.jsx";
import Notifications from "./pages/Notifications.jsx";

function Guard({ roles, children }) {
  const { user } = useAuth();
  if (roles && !roles.includes(user.role)) return <Navigate to="/" replace />;
  return children;
}

export default function App() {
  const { user, loading } = useAuth();

  if (loading) return <p className="boot">Loading…</p>;

  if (!user) {
    return (
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/signup" element={<Signup />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    );
  }

  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Tickets />} />
        <Route
          path="/new"
          element={
            <Guard roles={["Student"]}>
              <NewTicket />
            </Guard>
          }
        />
        <Route path="/tickets/:id" element={<TicketDetail />} />
        <Route
          path="/analytics"
          element={
            <Guard roles={["Admin", "Technician"]}>
              <Analytics />
            </Guard>
          }
        />
        <Route
          path="/users"
          element={
            <Guard roles={["Admin"]}>
              <Users />
            </Guard>
          }
        />
        <Route path="/notifications" element={<Notifications />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Layout>
  );
}
