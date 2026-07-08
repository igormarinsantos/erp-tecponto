import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        tec: {
          bg: "rgb(var(--tp-bg) / <alpha-value>)",
          "bg-elevated": "rgb(var(--tp-bg-elevated) / <alpha-value>)",
          panel: "rgb(var(--tp-panel) / <alpha-value>)",
          "panel-strong": "rgb(var(--tp-panel-strong) / <alpha-value>)",
          field: "rgb(var(--tp-field) / <alpha-value>)",
          sidebar: "rgb(var(--tp-sidebar) / <alpha-value>)",
          border: "rgb(var(--tp-border) / <alpha-value>)",
          orange: "rgb(var(--tp-orange) / <alpha-value>)",
          "digital-orange": "rgb(var(--tp-digital-orange) / <alpha-value>)",
          graphite: "rgb(var(--tp-graphite) / <alpha-value>)",
          ink: "rgb(var(--tp-ink) / <alpha-value>)",
          mist: "rgb(var(--tp-mist) / <alpha-value>)",
          white: "rgb(var(--tp-white) / <alpha-value>)",
          success: "rgb(var(--tp-success) / <alpha-value>)",
          green: "rgb(var(--tp-green) / <alpha-value>)",
          whatsapp: "rgb(var(--tp-whatsapp) / <alpha-value>)",
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
        card: "var(--tp-card-radius)",
        control: "var(--tp-control-radius)",
        nav: "var(--tp-nav-radius)",
      },
      fontFamily: {
        display: [
          "var(--tp-font-display)",
        ],
        table: [
          "var(--tp-font-table)",
        ],
        sans: [
          "var(--tp-font-body)",
        ],
      },
      boxShadow: {
        panel: "0 18px 42px rgba(0, 0, 0, 0.32)",
        glow: "0 0 0 1px rgba(254, 80, 0, 0.26), 0 14px 28px rgba(254, 80, 0, 0.16)",
      },
    },
  },
  plugins: [],
} satisfies Config;
