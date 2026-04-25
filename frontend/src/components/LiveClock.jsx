import { useEffect, useState } from "react";

export default function LiveClock() {
  const [now, setNow] = useState(new Date());
  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(t);
  }, []);
  const utc = now.toISOString().slice(11, 19);
  return (
    <span className="font-mono text-text-muted">
      {utc} <span className="text-text-muted/70">UTC</span>
    </span>
  );
}
