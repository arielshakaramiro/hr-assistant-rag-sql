import { useEffect } from "react";
import { type Sources } from "./api";
import { Icon } from "./Icon";

export function SourcesDrawer({ sources, onClose }: { sources: Sources | null; onClose: () => void }) {
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);

  const open = sources !== null;
  const rows = sources?.rows ?? [];
  const cols = rows[0] ? Object.keys(rows[0]) : [];

  return (
    <>
      <div className={`scrim${open ? " open" : ""}`} onClick={onClose} />
      <aside className={`drawer${open ? " open" : ""}`} aria-label="Answer sources" aria-hidden={!open}>
        <div className="drawer-head">
          <h3>
            <Icon name="check" size={16} /> Sources
          </h3>
          <button className="iconbtn" type="button" aria-label="Close sources" onClick={onClose}>
            <Icon name="close" size={17} />
          </button>
        </div>
        <div className="drawer-body" tabIndex={0}>
          {sources?.sql !== undefined && (
            <>
              <p className="drawer-section">
                <Icon name="db" size={13} />
                {sources.blocked ? " Blocked SQL — not executed" : " Executed query — read-only, scoped to you"}
              </p>
              <pre className="sql" tabIndex={0}>
                {sources.sql}
              </pre>
            </>
          )}
          {rows.length > 0 && (
            <>
              <p className="drawer-section">Result</p>
              <table className="result">
                <thead>
                  <tr>
                    {cols.map((c) => (
                      <th key={c}>{c}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {rows.map((r, i) => (
                    <tr key={i}>
                      {cols.map((c) => (
                        <td key={c}>{String(r[c])}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          )}
          {sources?.citations && sources.citations.length > 0 && (
            <>
              <p className="drawer-section">Policy citations</p>
              {sources.citations.map((c, i) => (
                <div className="cite" key={i}>
                  <span className="where">
                    <Icon name="doc" size={12} /> {c.doc_title} · {c.section}
                  </span>
                  {c.text.split("\n").slice(-1)[0]}
                </div>
              ))}
            </>
          )}
        </div>
      </aside>
    </>
  );
}
