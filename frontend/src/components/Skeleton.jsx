export default function Skeleton({ className = "" }) {
  return (
    <div
      className={`relative overflow-hidden bg-bg-card rounded ${className}`}
    >
      <div className="absolute inset-0 shimmer animate-shimmer" />
    </div>
  );
}
