import { useRef, useState } from "react";
import { api, ApiError, type ChatData, type Sources, type Turn as HistoryTurn } from "./api";
import { Icon } from "./Icon";

interface Turn {
  id: number;
  question: string;
  data?: ChatData;
  error?: boolean;
  pending?: boolean;
}

const CHIPS = [
  { icon: "leave", text: "How many annual leave days do I have left?" },
  { icon: "clock", text: "What is the overtime policy?" },
  { icon: "claim", text: "What is the status of my latest claim?" },
  { icon: "clock", text: "Was I late last month?" },
] as const;

export function Chat({ onOpenSources }: { onOpenSources: (s: Sources) => void }) {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const nextId = useRef(1);

  async function ask(question: string) {
    const q = question.trim();
    if (!q || busy) return;
    const id = nextId.current++;
    // Send the last few completed turns as context so a follow-up ("what about last year?")
    // resolves. Backend caps this again; nothing is persisted server-side.
    const history: HistoryTurn[] = turns
      .filter((t): t is Turn & { data: ChatData } => Boolean(t.data))
      .slice(-3)
      .map((t) => ({ question: t.question, answer: t.data.answer }));
    setInput("");
    setBusy(true);
    setTurns((t) => [...t, { id, question: q, pending: true }]);
    try {
      const res = await api.ask(q, history);
      setTurns((t) => t.map((x) => (x.id === id ? { ...x, data: res.data, pending: false } : x)));
    } catch (ex) {
      const rate = ex instanceof ApiError && ex.status === 429;
      setTurns((t) =>
        t.map((x) => (x.id === id ? { ...x, error: true, pending: false, rate } : x)),
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <main className="view scroll" aria-label="Ask assistant">
        <div className="thread">
        <div className="hero-head">
          <h2>Ask about policy or your own records</h2>
          <p>
            Leave, attendance, claims, and company policy — answered with sources. You only ever
            see your own data. <span className="sample-tag">sample demo data</span>
          </p>
          <div className="chips" role="group" aria-label="Suggested questions">
            {CHIPS.map((c) => (
              <button className="chip" type="button" key={c.text} onClick={() => ask(c.text)}>
                <Icon name={c.icon} size={14} /> {c.text}
              </button>
            ))}
          </div>
        </div>

          {turns.map((t) => (
            <Message key={t.id} turn={t} onOpenSources={onOpenSources} />
          ))}
        </div>
      </main>

      <footer className="composer" aria-label="Ask a question">
        <div className="composer-inner">
          <label htmlFor="q" className="sr-only">
            Ask a question
          </label>
          <textarea
            id="q"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                ask(input);
              }
            }}
            placeholder="Ask about your leave, attendance, claims, or company policy…"
          />
          <button className="send" type="button" onClick={() => ask(input)} disabled={busy}>
            Send <Icon name="send" size={16} />
          </button>
        </div>
        <p className="consent">
          <Icon name="claim" size={13} /> Rating an answer stores that question and answer in the
          app to improve the assistant. Questions are otherwise not saved.
        </p>
      </footer>
    </>
  );
}

function Message({
  turn,
  onOpenSources,
}: {
  turn: Turn & { rate?: boolean };
  onOpenSources: (s: Sources) => void;
}) {
  const [rating, setRating] = useState<"up" | "down" | null>(null);
  const d = turn.data;

  function rate(r: "up" | "down") {
    if (!d) return;
    setRating(r);
    // Storing Q/A text happens only on this explicit rating (consent shown in the composer note).
    void api.feedback(turn.question, d.answer, d.route, r).catch(() => {});
  }
  return (
    <div className="msg">
      <div className="bubble user">{turn.question}</div>
      <div className="bubble assistant">
        {turn.pending && (
          <span className="typing" role="status" aria-label="Assistant is thinking">
            <i />
            <i />
            <i />
          </span>
        )}
        {turn.error && (
          <div className="notice error">
            <Icon name="warn" size={18} />
            <span>
              {turn.rate
                ? "You're asking a lot quickly — give it a moment and try again."
                : "Couldn't reach the model just now. Please try again."}
            </span>
          </div>
        )}
        {d && <Answer d={d} onOpenSources={onOpenSources} rating={rating} setRating={rate} />}
      </div>
    </div>
  );
}

function Answer({
  d,
  onOpenSources,
  rating,
  setRating,
}: {
  d: ChatData;
  onOpenSources: (s: Sources) => void;
  rating: "up" | "down" | null;
  setRating: (r: "up" | "down") => void;
}) {
  const blocked = d.sources.blocked;
  const abstained = d.outcome === "abstained" && d.route !== "DATA";
  const hasSources =
    (d.sources.citations && d.sources.citations.length > 0) || d.sources.sql !== undefined;
  return (
    <>
      <div className="meta-row">
        <span className="badge">
          <Icon name={d.route === "POLICY" ? "doc" : "db"} size={13} /> {d.route}
          <span className="reason">· {d.route_reason}</span>
        </span>
        <span className={`confidence${d.confidence === "low" ? " low" : ""}`}>
          <span className="dot" /> {d.confidence} confidence
        </span>
      </div>

      {blocked ? (
        <div className="notice blocked">
          <Icon name="shield" size={18} />
          <span>
            <strong>Query blocked</strong> ({blocked.code}): {blocked.message}
          </span>
        </div>
      ) : abstained ? (
        <div className="notice abstain">
          <Icon name="warn" size={18} />
          <span>{d.answer}</span>
        </div>
      ) : (
        <p className="answer">{d.answer}</p>
      )}

      {hasSources && (
        <button className="srcbtn" type="button" onClick={() => onOpenSources(d.sources)}>
          <Icon name="check" size={14} />
          {d.sources.sql !== undefined ? " View SQL & result" : ` View ${d.sources.citations?.length} citations`}
        </button>
      )}

      {!blocked && !abstained && (
        <div className="feedback">
          <span>Was this helpful?</span>
          <button
            className="fbtn"
            type="button"
            aria-label="Helpful"
            aria-pressed={rating === "up"}
            onClick={() => setRating("up")}
          >
            <Icon name="up" size={15} />
          </button>
          <button
            className="fbtn"
            type="button"
            aria-label="Not helpful"
            aria-pressed={rating === "down"}
            onClick={() => setRating("down")}
          >
            <Icon name="down" size={15} />
          </button>
        </div>
      )}
    </>
  );
}
