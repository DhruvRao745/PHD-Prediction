import { Navigate } from "react-router-dom";
import { useAuth } from "./AuthContext.jsx";

// Wrap a route's element with this to require login, and optionally
// restrict it to specific role(s). Pass a single role via `role`, or
// multiple via `roles={["patient", "doctor"]}`. Redirects instead of
// rendering if the check fails.
export default function ProtectedRoute({ role, roles, children }) {
  const { user, loading } = useAuth();

  if (loading) {
    return <div className="page">Loading...</div>;
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  const allowedRoles = roles || (role ? [role] : null);

  if (allowedRoles && !allowedRoles.includes(user.role)) {
    return <Navigate to="/" replace />;
  }

  return children;
}
