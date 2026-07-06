// Compares the two most recent predictions (chronological, ascending)
// and shows whether risk moved up or down since last time - a single
// number in isolation doesn't tell a doctor whether a patient is
// improving or getting worse, the direction does.
export default function RiskTrend({ predictions }) {
  if (!predictions || predictions.length < 2) return null;

  const latest = predictions[predictions.length - 1];
  const previous = predictions[predictions.length - 2];
  const diff = latest.confidence - previous.confidence;

  if (Math.abs(diff) < 0.01) {
    return <span className="trend flat">→ steady</span>;
  }

  if (diff > 0) {
    return <span className="trend up">↑ risk up {Math.round(diff * 100)}%</span>;
  }

  return <span className="trend down">↓ risk down {Math.round(Math.abs(diff) * 100)}%</span>;
}
