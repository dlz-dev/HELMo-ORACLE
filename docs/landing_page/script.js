tailwind.config = {
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        'gold': '#C9A84C',
        'gold-light': '#E2C06A',
        'gold-glow': 'rgba(201, 168, 76, 0.4)',
        'glass-bg': 'rgba(255, 255, 255, 0.05)',
        'glass-border': 'rgba(255, 255, 255, 0.1)',
      },
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', 'sans-serif'],
        heading: ['Outfit', 'sans-serif'],
      },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
        'hero-glow': 'radial-gradient(circle at 50% 50%, rgba(201, 168, 76, 0.12) 0%, rgba(0, 0, 0, 0) 50%)',
      }
    }
  }
}