import type { Config } from "tailwindcss"

const config: Config = {
  content: ["./src/**/*.{ts,tsx}", "./*.tsx", "./contents/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        argus: {
          ink: "#111827",
          panel: "#F7F8FA",
          line: "#D7DCE2",
          accent: "#0F766E",
          signal: "#D97706",
          danger: "#B91C1C"
        }
      },
      boxShadow: {
        argus: "0 18px 50px rgba(17, 24, 39, 0.18)"
      }
    }
  },
  plugins: []
}

export default config
