import { useEffect, useState } from "react";

const STORAGE_KEY = "phd_theme";

function getInitialTheme() {
  const saved = localStorage.getItem(STORAGE_KEY);
  if (saved === "dark" || saved === "light") return saved;
  // No saved preference yet - default to whatever the OS/browser prefers.
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

// Persists across reloads via localStorage and applies instantly by
// setting data-theme on <html> - index.css does the rest since every
// color in the app is already a CSS variable.
export default function ThemeToggle() {
  const [theme, setTheme] = useState(getInitialTheme);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem(STORAGE_KEY, theme);
  }, [theme]);

  return (
    <button
      type="button"
      className="theme-toggle"
      onClick={() => setTheme((t) => (t === "dark" ? "light" : "dark"))}
      aria-label={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
      title={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
    >
      {theme === "dark" ? (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="12" cy="12" r="5" />
          <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42" />
        </svg>
      ) : (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
        </svg>
      )}
    </button>
  );
}
