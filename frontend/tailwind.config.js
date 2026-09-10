/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        paper: { 50: '#FFFCF6', 100: '#FFF8EC', 200: '#F6EAD4' },
        ink: { DEFAULT: '#2B2620', soft: '#57504A', mute: '#8A8178' },
        accent: { DEFAULT: '#B45309', soft: '#D97706' },
      },
      fontFamily: {
        ui: ['"Noto Sans SC"', 'system-ui', '-apple-system', 'PingFang SC',
          'Microsoft YaHei', 'sans-serif'],
        serif: ['"Noto Serif SC"', 'Songti SC', 'STSong', 'SimSun', 'serif'],
      },
      boxShadow: {
        card: '0 1px 2px rgba(60,45,20,.06), 0 8px 24px rgba(60,45,20,.08)',
        sheet: '0 -8px 32px rgba(40,32,20,.18)',
      },
      borderRadius: { xl2: '14px' },
    },
  },
  plugins: [],
}
