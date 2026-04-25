import { Navigate } from "react-router-dom";
import { getStoredUser } from "../api";

const HOME_BY_ROLE = {
  admin:    "/dashboard",
  operator: "/dashboard",
  analyst:  "/dashboard",
  viewer:   "/dashboard",
  owner:    "/owner",
  captain:  "/captain",
};

export default function RoleHome() {
  const user = getStoredUser();
  const target = HOME_BY_ROLE[user?.role] || "/dashboard";
  return <Navigate to={target} replace />;
}
