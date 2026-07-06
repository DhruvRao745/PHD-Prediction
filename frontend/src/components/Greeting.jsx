function timeOfDay() {
  const hour = new Date().getHours();
  if (hour < 12) return "morning";
  if (hour < 17) return "afternoon";
  return "evening";
}

// Top-of-dashboard banner: "Good afternoon, Dhruv" + a one-line summary
// of whatever needs attention right now. `summary` is left as plain text
// built by the caller from real counts - no invented stats.
export default function Greeting({ name, summary }) {
  return (
    <div className="greeting-banner">
      <h2 style={{ margin: 0 }}>Good {timeOfDay()}, {name}</h2>
      {summary && <p className="hint" style={{ margin: "0.35rem 0 0" }}>{summary}</p>}
    </div>
  );
}
