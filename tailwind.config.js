/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: "class",
  // Scan every app's templates. Tailwind reads these as plain text, so classes
  // referenced inside inline <script> blocks in these templates (e.g. the nav
  // dropdown toggling 'opacity-0'/'pointer-events-none') are picked up too.
  content: [
    "./missions/templates/**/*.html",
    "./appointments/templates/**/*.html",
    "./queue_management/templates/**/*.html",
    "./assistant/templates/**/*.html",
    "./notifications/templates/**/*.html",
  ],
  // Belt-and-braces safelist for classes only ever added/removed by JS at
  // runtime, so a future template refactor can't accidentally purge them.
  safelist: [
    "hidden",
    "opacity-0", "opacity-100",
    "-translate-y-2", "translate-y-0",
    "pointer-events-none", "pointer-events-auto",
  ],
  theme: {
    extend: {
      colors: {
        // Darkened from the original brand hues (#00adef / #d4af37 / #ef4444) to
        // meet WCAG AA 4.5:1 text contrast on white - the originals measured
        // 2.55:1, 2.10:1, and 3.76:1 and failed for body/link text.
        primary: "#0077a3",     // Somali sky blue, AA text contrast 5.0:1 on white
        secondary: "#183059",   // Deep trust navy
        accent: "#8a6d1f",      // Gold accent, AA text contrast 4.9:1 on white
        background: "#f4f7f6",
        card: "#ffffff",
        border: "#e2e8f0",
        textPrimary: "#0f172a",
        textSecondary: "#475569",
        danger: "#dc2626",      // AA text contrast 4.8:1 on white
      },
      fontFamily: {
        sans: ["Plus Jakarta Sans", "sans-serif"],
      },
    },
  },
  plugins: [
    require("@tailwindcss/forms"),
    require("@tailwindcss/container-queries"),
  ],
};
