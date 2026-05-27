/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#090a0f",
        card: "#0f111a",
        border: "#1e293b",
        glow: "#10b981",
        emerald: {
          500: "#10b981",
        },
        rose: {
          500: "#f43f5e",
        },
        amber: {
          500: "#f59e0b",
        }
      }
    },
  },
  plugins: [],
}
