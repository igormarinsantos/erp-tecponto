import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        tec: {
          bg: "rgb(var(--tp-bg) / <alpha-value>)",
          panel: "rgb(var(--tp-panel) / <alpha-value>)",
          "panel-strong": "rgb(var(--tp-panel-strong) / <alpha-value>)",
          border: "rgb(var(--tp-border) / <alpha-value>)",
          orange: "rgb(var(--tp-orange) / <alpha-value>)",
          green: "rgb(var(--tp-green) / <alpha-value>)",
          blue: "rgb(var(--tp-blue) / <alpha-value>)",
          purple: "rgb(var(--tp-purple) / <alpha-value>)",
          amber: "rgb(var(--tp-amber) / <alpha-value>)",
          red: "rgb(var(--tp-red) / <alpha-value>)",
          text: "rgb(var(--tp-text) / <alpha-value>)",
          muted: "rgb(var(--tp-muted) / <alpha-value>)",
          subtle: "rgb(var(--tp-subtle) / <alpha-value>)",
        },
      },
      borderRadius: {
        card: "8px",
        control: "8px",
      },
      fontFamily: {
        sans: [
          "Inter",
          "ui-sans-serif",
          "system-ui",
          "-apple-system",
          "BlinkMacSystemFont",
          "Segoe UI",
          "sans-serif",
        ],
      },
      boxShadow: {
        panel: "0 18px 42px rgba(0, 0, 0, 0.32)",
        glow: "0 0 0 1px rgba(255, 91, 18, 0.22), 0 14px 28px rgba(255, 91, 18, 0.12)",
      },
    },
  },
  plugins: [],
} satisfies Config;
