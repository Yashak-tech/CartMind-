/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        ink: "#0B0E14",
        panel: "#141A26",
        paper: "#F3F1EA",
        slate: "#566073",
        "signal-gold": "#E8B84F",
        "agent-cyan": "#4FD1C5",
        "alert-coral": "#E8614F",
        "panel-border": "#232C3D",
      },
      fontFamily: {
        sans: ["Inter", "-apple-system", "BlinkMacSystemFont", "sans-serif"],
        display: ["Cabinet Grotesk", "sans-serif"],
        mono: ["IBM Plex Mono", "monospace"],
      },
      keyframes: {
        flashGold: {
          '0%': { backgroundColor: 'rgba(232, 184, 79, 0.25)' },
          '100%': { backgroundColor: 'transparent' },
        },
        flashCoral: {
          '0%': { backgroundColor: 'rgba(232, 97, 79, 0.25)' },
          '100%': { backgroundColor: 'transparent' },
        },
        flashSlate: {
          '0%': { backgroundColor: 'rgba(86, 96, 115, 0.25)' },
          '100%': { backgroundColor: 'transparent' },
        },
        slideDown: {
          '0%': { transform: 'translateY(-10px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        }
      },
      animation: {
        flashGold: 'flashGold 1.2s ease-out',
        flashCoral: 'flashCoral 1.2s ease-out',
        flashSlate: 'flashSlate 1.2s ease-out',
        slideDown: 'slideDown 0.25s ease-out',
      }
    },
  },
  plugins: [],
};
