import { useEffect, useState } from "react";
import { Outlet } from "react-router-dom";
import CommandPalette from "./CommandPalette";
import Sidebar, { MobileTabBar } from "./Sidebar";
import TopHeader from "./TopHeader";

export default function Layout() {
  const [collapsed, setCollapsed] = useState(false);
  const [palette, setPalette] = useState(false);

  useEffect(() => {
    function onKey(e) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setPalette(true);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  return (
    <div className="flex h-screen w-screen bg-bg-primary text-text-primary overflow-hidden">
      <Sidebar collapsed={collapsed} onToggle={() => setCollapsed((c) => !c)} />
      <div className="flex-1 flex flex-col overflow-hidden">
        <TopHeader onOpenPalette={() => setPalette(true)} />
        <main className="flex-1 overflow-auto pb-16 md:pb-0">
          <Outlet />
        </main>
      </div>
      <MobileTabBar />
      <CommandPalette open={palette} onClose={() => setPalette(false)} />
    </div>
  );
}
