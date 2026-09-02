/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          950: "#07111c",
          900: "#0b1c2c",
          800: "#123047",
          700: "#1b425c",
        },
        accent: {
          400: "#2dd4bf",
          500: "#0f9d8a",
          600: "#0b7c6e",
        },
      },
      fontFamily: {
        sans: ["IBM Plex Sans", "ui-sans-serif", "system-ui"],
        mono: ["IBM Plex Mono", "ui-monospace", "monospace"],
      },
    },
  },
  plugins: [],
};
