import { useEffect, useState } from "react";
import { api } from "./api.js";

export function fmtDate(value) {
  if (!value) return "";
  return new Date(value).toLocaleString("en-IN", {
    day: "numeric",
    month: "short",
    hour: "numeric",
    minute: "2-digit",
  });
}

export function fmtAge(hours) {
  if (hours === null || hours === undefined) return "";
  const h = Number(hours);
  if (h < 1) return "under an hour";
  if (h < 48) return `${Math.round(h)} h`;
  return `${Math.round(h / 24)} days`;
}

let lookupCache = null;

export function useLookups() {
  const [data, setData] = useState(lookupCache);
  useEffect(() => {
    if (lookupCache) return;
    api("/lookups").then((r) => {
      lookupCache = r;
      setData(r);
    });
  }, []);
  return data;
}

export function Status({ value }) {
  return (
    <span className={`status status-${value.toLowerCase()}`}>
      <i />
      {value}
    </span>
  );
}

export function Priority({ name, rank }) {
  return <span className={`prio prio-${rank}`}>{name}</span>;
}

export function Pager({ page, pages, onChange }) {
  if (pages <= 1) return null;
  return (
    <div className="pager">
      <button className="btn small" disabled={page <= 1} onClick={() => onChange(page - 1)}>
        Previous
      </button>
      <span>
        Page {page} of {pages}
      </span>
      <button className="btn small" disabled={page >= pages} onClick={() => onChange(page + 1)}>
        Next
      </button>
    </div>
  );
}

export function useAsync(fn, deps) {
  const [state, setState] = useState({ data: null, error: "", loading: true });
  useEffect(() => {
    let alive = true;
    setState((s) => ({ ...s, loading: true, error: "" }));
    fn()
      .then((data) => alive && setState({ data, error: "", loading: false }))
      .catch((e) => alive && setState({ data: null, error: e.message, loading: false }));
    return () => {
      alive = false;
    };
  }, deps);
  return state;
}
