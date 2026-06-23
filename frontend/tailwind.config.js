/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      colors: {
        brand: {
          50:  '#eef3fb',
          100: '#d0dfF3',
          200: '#a1bfe7',
          300: '#729fdb',
          400: '#437fcf',
          500: '#1a5fc3',
          600: '#144d9e',
          700: '#0f3b7a',
          800: '#0a2855',
          900: '#051631',
        },
      },
    },
  },
  plugins: [],
}
