// Small colored initials circle for a person's name - the color is
// picked deterministically from the name itself (same name always gets
// the same color) so lists feel visually varied without any random
// flicker on re-render.
const PALETTE = ["#2563eb", "#16a34a", "#d97706", "#9333ea", "#0891b2", "#dc2626", "#4f46e5"];

function colorFor(name) {
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash);
  }
  return PALETTE[Math.abs(hash) % PALETTE.length];
}

function initialsFor(name) {
  const parts = String(name || "?").trim().split(/\s+/);
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

export default function Avatar({ name, size = 32 }) {
  return (
    <span
      className="avatar"
      style={{
        width: size,
        height: size,
        fontSize: size * 0.4,
        background: colorFor(name || "?"),
      }}
    >
      {initialsFor(name)}
    </span>
  );
}
