/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        app: '#030608',
        surface: '#080C10',
        'surface-2': '#0C1116',
        elevated: '#10161C',
        line: {
          DEFAULT: '#29313A',
          strong: '#46515C',
        },
        ink: {
          primary: '#F2F4F5',
          secondary: '#9BA5AE',
          muted: '#626C75',
        },
        accent: {
          blue: '#3EA6FF',
          green: '#8BE34F',
          purple: '#9B6CFF',
          gold: '#FFD23F',
        },
        silver: '#B8C0C7',
      },
      fontFamily: {
        mono: ['"IBM Plex Mono"', 'ui-monospace', 'monospace'],
        sans: ['Inter', 'ui-sans-serif', 'sans-serif'],
      },
      borderRadius: {
        sm: '4px',
        DEFAULT: '6px',
        lg: '8px',
      },
    },
  },
  plugins: [],
}
