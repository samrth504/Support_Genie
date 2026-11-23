import { Navigate, useLocation } from "react-router-dom";

import { homeFor, useAuth } from "../context/AuthContext";
import { Spinner } from "./ui";

/** Only logged-in users with the right role see the page. (The backend checks again on every call.) */
export default function ProtectedRoute({ role, children }) {
  const { user, checking } = useAuth();
  const location = useLocation();

  if (checking) return <Spinner label="Checking your session…" />;
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  if (role && user.role !== role) return <Navigate to={homeFor(user)} replace />;
  return children;
}
