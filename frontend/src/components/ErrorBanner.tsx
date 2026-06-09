import { useContext } from "react";
import { AppContext } from "../context/AppContext";

export default function ErrorBanner() {
  const ctx = useContext(AppContext);
  if (!ctx) return null;
  const { error, setError } = ctx;
  if (!error) return null;
  return (
    <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded text-sm text-red-700">
      {error}
      <button
        onClick={() => setError("")}
        className="ml-2 text-red-500 hover:text-red-700"
      >
        ✕
      </button>
    </div>
  );
}
