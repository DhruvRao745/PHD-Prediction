// A friendlier stand-in for a flat "No X yet." sentence - names the
// empty space, explains it in one line, and optionally offers a next
// step (a real link/button, not just "click here").
export default function EmptyState({ title, hint, action }) {
  return (
    <div className="empty-state">
      <p>{title}</p>
      {hint && <p className="hint" style={{ margin: 0 }}>{hint}</p>}
      {action && <div style={{ marginTop: "0.75rem" }}>{action}</div>}
    </div>
  );
}
