/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{js,jsx,ts,tsx}'],
  theme: {
    fontSize: {
      xs: ['var(--text-xs)', '1.4'],
      sm: ['var(--text-sm)', '1.4'],
      base: ['var(--text-base)', '1.5'],
      lg: ['var(--text-lg)', '1.5'],
      xl: ['var(--text-xl)', '1.4'],
      '2xl': ['var(--text-2xl)', '1.3'],
      '3xl': ['var(--text-3xl)', '1.2'],
      '4xl': ['var(--text-4xl)', '1.1'],
    },
    extend: {
      colors: {
        background: '#F2F2F7',
        accent: 'var(--accent-color, #007AFF)',
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
