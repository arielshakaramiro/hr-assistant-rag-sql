// Inline SVG icons (no emoji in chrome). One component, name-keyed, stroke = currentColor.
type Name =
  | "logo" | "ask" | "leave" | "clock" | "claim" | "chart" | "menu" | "moon"
  | "signout" | "db" | "doc" | "shield" | "warn" | "send" | "up" | "down" | "close" | "check";

const P: Record<Name, string> = {
  logo: "M6 7h20a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H13l-5 4v-4H6a2 2 0 0 1-2-2V9a2 2 0 0 1 2-2zM16 10.5l3 1.3v2.4c0 2-1.3 3.2-3 3.8-1.7-.6-3-1.8-3-3.8v-2.4l3-1.3z",
  ask: "M8 10h8M8 14h5M21 12a9 9 0 1 1-3.6-7.2L21 3v6h-6",
  leave: "M8 7V3m8 4V3M4 11h16M5 5h14a1 1 0 0 1 1 1v13a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1z",
  clock: "M12 6v6l4 2M12 22a10 10 0 1 1 0-20 10 10 0 0 1 0 20z",
  claim: "M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8zM14 2v6h6M9 13h6M9 17h4",
  chart: "M3 3v18h18M7 15l4-4 3 3 5-6",
  menu: "M4 6h16M4 12h16M4 18h16",
  moon: "M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z",
  signout: "M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9",
  db: "M4 7c0-1.7 3.6-3 8-3s8 1.3 8 3-3.6 3-8 3-8-1.3-8-3zM4 7v10c0 1.7 3.6 3 8 3s8-1.3 8-3V7",
  doc: "M4 4h12l4 4v12H4zM14 4v4h4",
  shield: "M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10zM9 12l2 2 4-4",
  warn: "M12 9v4m0 4h.01M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z",
  send: "M22 2 11 13M22 2l-7 20-4-9-9-4z",
  up: "M7 10v11M14 4l-2 6h7a2 2 0 0 1 2 2.3l-1.2 7A2 2 0 0 1 17.8 21H7V10l4-7a2 2 0 0 1 3 1z",
  down: "M17 14V3M10 20l2-6H5a2 2 0 0 1-2-2.3l1.2-7A2 2 0 0 1 6.2 3H17v11l-4 7a2 2 0 0 1-3-1z",
  close: "M18 6 6 18M6 6l12 12",
  check: "M9 11l3 3L22 4M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11",
};

export function Icon({ name, size = 18 }: { name: Name; size?: number }) {
  const vb = name === "logo" ? "0 0 32 32" : "0 0 24 24";
  return (
    <svg
      viewBox={vb}
      width={size}
      height={size}
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d={P[name]} />
    </svg>
  );
}
