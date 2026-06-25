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
          navy:   '#051C2C',
          black:  '#222222',
          copper: '#DEA36D',
          green:  '#19322F',
          beige:  '#D0D0AA',
          bg:     '#F8F7F4',
        },
      },
    },
  },
  plugins: [],
}
