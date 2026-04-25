import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import RequireAuth from "./components/RequireAuth";
import { ToastProvider } from "./components/Toast";
import Alerts from "./pages/Alerts";
import Bookings from "./pages/Bookings";
import CaptainPanel from "./pages/CaptainPanel";
import Dashboard from "./pages/Dashboard";
import EsgReport from "./pages/EsgReport";
import Fleet from "./pages/Fleet";
import JitTool from "./pages/JitTool";
import LiveMap from "./pages/LiveMap";
import Login from "./pages/Login";
import OwnerPanel from "./pages/OwnerPanel";
import Settings from "./pages/Settings";
import Compare from "./pages/Compare";
import VesselDetail from "./pages/VesselDetail";
import RoleHome from "./components/RoleHome";

export default function App() {
  return (
    <ToastProvider>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          element={
            <RequireAuth>
              <Layout />
            </RequireAuth>
          }
        >
          <Route path="/" element={<RoleHome />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/owner" element={<OwnerPanel />} />
          <Route path="/captain" element={<CaptainPanel />} />
          <Route path="/map" element={<LiveMap />} />
          <Route path="/fleet" element={<Fleet />} />
          <Route path="/fleet/:id" element={<VesselDetail />} />
          <Route path="/bookings" element={<Bookings />} />
          <Route path="/alerts" element={<Alerts />} />
          <Route path="/jit-tool" element={<JitTool />} />
          <Route path="/esg" element={<EsgReport />} />
          <Route path="/compare" element={<Compare />} />
          <Route path="/settings" element={<Settings />} />
        </Route>
        <Route path="*" element={<RoleHome />} />
      </Routes>
    </ToastProvider>
  );
}

