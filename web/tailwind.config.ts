import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      fontFamily: {
        cinzel: ["var(--font-cinzel)", "serif"],
        sans:   ["var(--font-geist-sans)", "sans-serif"],
        mono:   ["var(--font-geist-mono)", "monospace"],
      },
      colors: {
        gold: {
          DEFAULT: "#C9A84C",
          light:   "#E2C06A",
          dark:    "#A07830",
        },
      },
      keyframes: {
        "fade-up": {
          "0%":   { opacity: "0", transform: "translateY(12px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "fade-in": {
          "0%":   { opacity: "0" },
          "100%": { opacity: "1" },
        },
        "glow-pulse": {
          "0%, 100%": { opacity: "0.6" },
          "50%":      { opacity: "1" },
        },
        shimmer: {
          "0%":   { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
      },
      animation: {
        "fade-up":    "fade-up 0.4s ease both",
        "fade-in":    "fade-in 0.3s ease both",
        "glow-pulse": "glow-pulse 3s ease-in-out infinite",
        shimmer:      "shimmer 2.5s linear infinite",
      },
    },
  },
  plugins: [],
};

export default config;