import { Navigate, useLocation } from "react-router-dom";
import { getToken } from "../api";

export default function RequireAuth({ children }) {
  const loc = useLocation();
  if (!getToken()) {
    return <Navigate to="/login" replace state={{ from: loc.pathname }} />;
  }
  return children;
}
