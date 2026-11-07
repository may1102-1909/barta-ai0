import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        navy: {
          50: "#f1f5f9",
          100: "#e2e8f0",
          200: "#cbd5e1",
          300: "#94a3b8",
          400: "#64748b",
          500: "#475569",
          600: "#334155",
          700: "#1e293b",
          800: "#172554",
          900: "#0f172a",
          950: "#0a192f",
        },
      },
      fontFamily: {
        sans: [
          '"Roboto Slab"',
          '"Noto Serif Devanagari"',
          "Rockwell",
          "Georgia",
          "serif",
        ],
        serif: [
          '"Roboto Slab"',
          '"Noto Serif Devanagari"',
          "Rockwell",
          "Georgia",
          "serif",
        ],
        slab: [
          '"Roboto Slab"',
          '"Noto Serif Devanagari"',
          "Rockwell",
          "Georgia",
          "serif",
        ],
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "Consolas", "monospace"],
      },
      boxShadow: {
        subtle: "0 1px 2px 0 rgba(15, 23, 42, 0.06)",
        card: "0 1px 3px 0 rgba(15, 23, 42, 0.06), 0 1px 2px -1px rgba(15, 23, 42, 0.04)",
        crisp: "0 10px 30px -12px rgba(15, 23, 42, 0.25)",
        glow: "0 0 0 3px rgba(16, 185, 129, 0.25)",
      },
      keyframes: {
        glow: {
          "0%, 100%": { boxShadow: "0 0 0 0 rgba(16, 185, 129, 0.45)" },
          "50%": { boxShadow: "0 0 0 4px rgba(16, 185, 129, 0)" },
        },
        "fade-in": {
          from: { opacity: "0", transform: "translateY(2px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        glow: "glow 1.8s ease-in-out infinite",
        "fade-in": "fade-in 180ms ease-out",
      },
    },
  },
  plugins: [],
};
export default config;
