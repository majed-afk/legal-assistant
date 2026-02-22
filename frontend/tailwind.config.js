/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './app/**/*.{js,ts,jsx,tsx}',
    './components/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Tajawal', 'Noto Naskh Arabic', 'sans-serif'],
        heading: ['Noto Naskh Arabic', 'Traditional Arabic', 'serif'],
        legal: ['Noto Naskh Arabic', 'Traditional Arabic', 'serif'],
      },
      colors: {
        primary: {
          50: '#f0f7ff',
          100: '#e0efff',
          200: '#b9dfff',
          300: '#7cc4ff',
          400: '#36a5ff',
          500: '#0c87f2',
          600: '#006acf',
          700: '#0054a7',
          800: '#044889',
          900: '#0a3d71',
        },
        gold: {
          400: '#d4a843',
          500: '#c49a38',
          600: '#a37e2c',
        },
      },
    },
  },
  plugins: [],
};
