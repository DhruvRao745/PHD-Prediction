import { createContext, useCallback, useContext, useState } from "react";

const ToastContext = createContext(null);

let nextId = 1;

// Small dismissible notification stack, top-right, auto-clears after a
// few seconds. Used for transient action feedback ("Assigned", "Deleted")
// so it doesn't sit on the page and get overwritten/confused with the
// next action - unlike the old static <p className="success"> banners.
export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);

  const showToast = useCallback((message, type = "success") => {
    const id = nextId++;
    setToasts((prev) => [...prev, { id, message, type }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 4000);
  }, []);

  function dismiss(id) {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }

  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}
      <div className="toast-stack">
        {toasts.map((t) => (
          <div key={t.id} className={`toast ${t.type}`} onClick={() => dismiss(t.id)}>
            {t.message}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used inside <ToastProvider>");
  return ctx;
}
