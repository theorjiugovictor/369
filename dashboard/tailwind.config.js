/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        earth: {
          50:  '#f6f3ee',
          100: '#ece6d9',
          200: '#d5c9b1',
          300: '#bba882',
          400: '#a68a5b',
          500: '#8c6f42',
          600: '#735836',
          700: '#5a432b',
          800: '#3d2d1c',
          900: '#1e160d',
        },
        moss: {
          400: '#6aad5e',
          500: '#4e9443',
          600: '#3d7534',
        },
        sky: {
          400: '#5aade0',
          500: '#3d93cc',
        },
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
    },
  },
  plugins: [],
}
