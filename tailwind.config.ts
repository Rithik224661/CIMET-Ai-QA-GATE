import type { Config } from "tailwindcss";

/**
 * Design tokens from design_handoff/README.md — the single source of
 * palette, type and shape values. Do not add colors outside this file;
 * components must reference these tokens, never raw hex values.
 */
const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#000000",
        surface: "#0a0a0a",
        "surface-2": "#121212",
        "chip-bg": "#1f1f1f",
        ring: "rgba(255,255,255,0.145)",
        hairline: "rgba(255,255,255,0.08)",
        track: "rgba(255,255,255,0.08)",
        "bar-muted": "rgba(255,255,255,0.18)",
        "bar-muted-2": "rgba(255,255,255,0.35)",
        text: "#ffffff",
        "text-2": "#ededed",
        "text-muted": "#999999",
        "text-dim": "#666666",
        "cta-ink": "#121212",
        pass: "#62c073",
        fail: "#f2685c",
        review: "#e0a341",
        accent: "#52a8ff",
      },
      fontFamily: {
        sans: ["var(--font-inter)", "system-ui", "sans-serif"],
        mono: ["var(--font-geist-mono)", "ui-monospace", "monospace"],
      },
      letterSpacing: {
        decision: "-2.6px",
        kpi: "-2.2px",
        cal: "-2px",
      },
      screens: {
        rail: "1040px",
      },
      keyframes: {
        qaspin: { to: { transform: "rotate(360deg)" } },
        qapulse: { "0%,100%": { opacity: "0.35" }, "50%": { opacity: "1" } },
        qaslide: {
          from: { transform: "translateX(16px)", opacity: "0" },
          to: { transform: "translateX(0)", opacity: "1" },
        },
      },
      animation: {
        qaspin: "qaspin 900ms linear infinite",
        qapulse: "qapulse 1s ease-in-out infinite",
        qaslide: "qaslide 180ms ease-out",
      },
    },
  },
};

export default config;
