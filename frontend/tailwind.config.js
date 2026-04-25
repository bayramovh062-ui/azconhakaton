/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx,ts,tsx}"],
  theme: {
    extend: {
      colors: {
        "bg-primary": "#0a0e1a",
        "bg-secondary": "#0f1629",
        "bg-card": "#141d35",
        border: "#1e2d4a",
        "accent-cyan": "#00d4ff",
        "accent-green": "#00ff88",
        "accent-red": "#ff3d3d",
        "accent-yellow": "#ffd700",
        "text-primary": "#e8f0fe",
        "text-muted": "#6b7fa3",
      },
      fontFamily: {
        display: ['Orbitron', 'sans-serif'],
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'ui-monospace', 'monospace'],
      },
      boxShadow: {
        glow: '0 0 18px rgba(0, 212, 255, 0.35)',
        'glow-green': '0 0 18px rgba(0, 255, 136, 0.35)',
        'glow-red': '0 0 18px rgba(255, 61, 61, 0.4)',
      },
      keyframes: {
        pulseRing: {
          '0%':   { transform: 'scale(0.8)', opacity: 0.8 },
          '100%': { transform: 'scale(2.2)', opacity: 0 },
        },
        gridShift: {
          '0%':   { backgroundPosition: '0 0' },
          '100%': { backgroundPosition: '60px 60px' },
        },
        countUp: {
          from: { opacity: 0, transform: 'translateY(8px)' },
          to:   { opacity: 1, transform: 'translateY(0)' },
        },
        shimmer: {
          '0%':   { backgroundPosition: '-400px 0' },
          '100%': { backgroundPosition: '400px 0' },
        },
      },
      animation: {
        pulseRing: 'pulseRing 1.6s ease-out infinite',
        gridShift: 'gridShift 20s linear infinite',
        countUp:   'countUp 0.5s ease-out',
        shimmer:   'shimmer 1.6s linear infinite',
      },
    },
  },
  plugins: [],
};
