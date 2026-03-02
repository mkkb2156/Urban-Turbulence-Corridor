/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        risk: {
          green: '#2ecc71',
          yellow: '#f1c40f',
          red: '#e74c3c',
          black: '#2c3e50',
        },
        sidebar: {
          DEFAULT: '#1e293b',
          hover: '#334155',
          active: '#0f172a',
        },
      },
      width: {
        sidebar: '240px',
        'sidebar-collapsed': '60px',
      },
    },
  },
  plugins: [],
};
