/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx,ts,tsx}'],
  theme: {
    extend: {
      colors: {
        background: '#F2F2F7',
        accent: '#007AFF',
        dark: '#1C1C1E',
      },
      boxShadow: {
        soft: '0 10px 40px rgba(0, 0, 0, 0.12)',
      },
      borderRadius: {
        card: '16px',
      },
      transitionDuration: {
        smooth: '180ms',
      },
    },
  },
  plugins: [],
};
